"""Modulo 4 + 5: Orquestracao, agendamento, trava de concorrencia, dedup e logs
(ver secao 5 e risco #8 do estudo de viabilidade).

Uso:
  - Ciclo unico:      python -m src.orchestrator --once
  - Loop continuo:    python -m src.orchestrator
    (dispara um ciclo a cada INTERVALO_HORAS; para producao, prefira agendar
    "python -m src.orchestrator --once" via Windows Task Scheduler em vez de
    manter este processo rodando, conforme secao 4 do estudo)
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config import settings
from src.logging_setup import get_logger

logger = get_logger("orchestrator")

HISTORICO_CPF = settings.DATA_FINAL_DIR / "cpf_historico.csv"


def _lock_path() -> Path:
    from config.settings import BASE_DIR

    return BASE_DIR / "orchestrator.lock"


def _adquirir_lock() -> bool:
    lock = _lock_path()
    if lock.exists():
        idade = time.time() - lock.stat().st_mtime
        if idade < 2 * 3600:
            logger.warning("Ciclo anterior ainda em execucao (lock com %.0f min). Pulando ciclo.", idade / 60)
            return False
        logger.warning("Lock antigo (%.0f min) considerado travado (stale). Removendo.", idade / 60)
        lock.unlink()

    lock.write_text(f"pid={os.getpid()} inicio={datetime.now().isoformat()}", encoding="utf-8")
    return True


def _liberar_lock() -> None:
    lock = _lock_path()
    if lock.exists():
        lock.unlink()


def _deduplicar_contra_historico(csv_tratado: Path) -> Path:
    df = pd.read_csv(csv_tratado, dtype={"CPF": str})

    agora = datetime.now()
    janela = agora - timedelta(hours=24)

    if HISTORICO_CPF.exists():
        historico = pd.read_csv(HISTORICO_CPF, dtype={"CPF": str}, parse_dates=["data_hora"])
        historico = historico[historico["data_hora"] >= janela]
    else:
        historico = pd.DataFrame(columns=["CPF", "data_hora"])

    cpfs_recentes = set(historico["CPF"])
    total_antes = len(df)
    df_dedup = df[~df["CPF"].isin(cpfs_recentes)].copy()
    logger.info(
        "Deduplicacao (janela 24h): %d linhas -> %d novas (%d ja processadas recentemente)",
        total_antes,
        len(df_dedup),
        total_antes - len(df_dedup),
    )

    novo_historico = pd.concat(
        [historico, pd.DataFrame({"CPF": df_dedup["CPF"], "data_hora": agora})],
        ignore_index=True,
    )
    novo_historico.to_csv(HISTORICO_CPF, index=False)

    destino = settings.DATA_FINAL_DIR / f"{csv_tratado.stem}_dedup.csv"
    df_dedup.to_csv(destino, index=False, encoding="utf-8-sig")
    return destino


def run_ciclo(permitir_consulta_real: bool = False, permitir_novavida_job_real: bool = False) -> None:
    if not _adquirir_lock():
        return

    inicio = time.time()
    try:
        logger.info("=== Iniciando ciclo ===")

        from src import astor_extraction, data_treatment

        bruto = astor_extraction.extrair(permitir_consulta_real=permitir_consulta_real)
        tratado = data_treatment.tratar(bruto)
        final_sem_higienizar = _deduplicar_contra_historico(tratado)

        logger.info(
            "Base pronta para envio ao Nova Vida: %s (integracao Nova Vida ainda "
            "nao implementada - ver src/novavida_integration.py)",
            final_sem_higienizar,
        )

        try:
            from src import novavida_integration

            novavida_integration.upload_e_higienizar(
                final_sem_higienizar, permitir_job_real=permitir_novavida_job_real
            )
        except (NotImplementedError, RuntimeError) as e:
            logger.warning("Etapa Nova Vida pendente: %s", e)

        logger.info("=== Ciclo concluido em %.1fs ===", time.time() - inicio)
    except Exception:
        logger.exception("Ciclo falhou com erro")
    finally:
        _liberar_lock()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Executa um unico ciclo e sai")
    parser.add_argument(
        "--permitir-consulta-real",
        action="store_true",
        help="Autoriza consultas reais (com possivel custo) no Astor Tech",
    )
    parser.add_argument(
        "--permitir-novavida-job-real",
        action="store_true",
        help="Autoriza disparar um job real (com possivel custo) no Nova Vida",
    )
    args = parser.parse_args()

    if args.once:
        run_ciclo(
            permitir_consulta_real=args.permitir_consulta_real,
            permitir_novavida_job_real=args.permitir_novavida_job_real,
        )
        return

    intervalo_seg = settings.INTERVALO_HORAS * 3600
    logger.info("Loop continuo iniciado (intervalo=%.0fs)", intervalo_seg)
    while True:
        run_ciclo(
            permitir_consulta_real=args.permitir_consulta_real,
            permitir_novavida_job_real=args.permitir_novavida_job_real,
        )
        time.sleep(intervalo_seg)


if __name__ == "__main__":
    main()
