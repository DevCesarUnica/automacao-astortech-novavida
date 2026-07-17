"""Modulo 2: Tratamento de dados (ver secao 5 do estudo de viabilidade).

Le o arquivo bruto exportado do Astor Tech, mantem apenas as colunas
I (CPF), R (Nome), N (Valor Liberado), aplica a regra de negocio
Valor Liberado > R$4.000,00 e gera o CSV separado por virgula para envio
ao Nova Vida.
"""
from __future__ import annotations

from pathlib import Path
from string import ascii_uppercase

import pandas as pd

from config import settings
from src.cpf_utils import cpf_valido, limpar_cpf
from src.logging_setup import get_logger

logger = get_logger("data_treatment")


def col_letter_to_index(letter: str) -> int:
    """Converte letra de coluna estilo Excel ('A', 'I', 'AA', ...) para indice 0-based."""
    letter = letter.strip().upper()
    idx = 0
    for ch in letter:
        idx = idx * 26 + (ascii_uppercase.index(ch) + 1)
    return idx - 1


def _ler_arquivo_bruto(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(caminho, header=0)
    return pd.read_csv(caminho, header=0, sep=None, engine="python")


def tratar(caminho_bruto: Path) -> Path:
    df = _ler_arquivo_bruto(caminho_bruto)

    idx_cpf = col_letter_to_index(settings.COLUNA_CPF)
    idx_nome = col_letter_to_index(settings.COLUNA_NOME)
    idx_valor = col_letter_to_index(settings.COLUNA_VALOR_LIBERADO)
    max_idx = max(idx_cpf, idx_nome, idx_valor)
    if max_idx >= len(df.columns):
        raise ValueError(
            f"Arquivo bruto tem {len(df.columns)} colunas, mas a coluna "
            f"'{settings.COLUNA_VALOR_LIBERADO}' (indice {idx_valor}) foi esperada. "
            "Confirmar layout real do export do Astor Tech."
        )

    saida = pd.DataFrame(
        {
            "CPF": df.iloc[:, idx_cpf],
            "Nome": df.iloc[:, idx_nome],
            "Valor Liberado": pd.to_numeric(
                df.iloc[:, idx_valor].astype(str).str.replace(r"[R$\s.]", "", regex=True).str.replace(",", "."),
                errors="coerce",
            ),
        }
    )
    total_bruto = len(saida)

    saida["CPF"] = saida["CPF"].apply(limpar_cpf)
    saida = saida[saida["CPF"].apply(cpf_valido)]
    descartados_cpf_invalido = total_bruto - len(saida)

    saida = saida[saida["Valor Liberado"] > settings.VALOR_MINIMO_REGRA_NEGOCIO]

    saida = saida.drop_duplicates(subset="CPF", keep="first")

    logger.info(
        "Tratamento concluido: %d linhas brutas -> %d CPFs invalidos descartados -> %d linhas finais",
        total_bruto,
        descartados_cpf_invalido,
        len(saida),
    )

    destino = settings.DATA_TREATED_DIR / f"{caminho_bruto.stem}_tratado.csv"
    saida.to_csv(destino, index=False, sep=",", encoding="utf-8-sig")
    logger.info("CSV tratado salvo em: %s", destino)
    return destino


if __name__ == "__main__":
    import sys

    tratar(Path(sys.argv[1]))
