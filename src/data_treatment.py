"""Modulo 2: Tratamento de dados (ver secao 5 do estudo de viabilidade).

Le o arquivo bruto exportado do Astor Tech, mantem apenas as colunas
I (CPF), R (Nome), N (Valor Liberado), aplica a regra de negocio
Valor Liberado > R$4.000,00 e gera o CSV separado por virgula para envio
ao Nova Vida.

CONFIRMADO com arquivo real em 17/07/2026 (export "UY3_1707_CLT", 4985
linhas, teste de ponta a ponta - ver docstring de src/astor_extraction.py):
  - O arquivo bruto entregue pelo Astor Tech e um .zip contendo um unico
    CSV separado por ";". _ler_arquivo_bruto() ja funciona sem alteracao:
    pandas.read_csv(sep=None, engine="python") detecta automaticamente a
    compressao (pelo sufixo .zip) e o separador.
  - O layout de colunas I/R/N do processo bateu exatamente com o arquivo
    real, contando letras de coluna estilo Excel (A=1, B=2, ...): indice 8
    ("I") = "registration_number" (CPF), indice 13 ("N") = "liquid_value"
    (Valor Liberado, ja em reais), indice 17 ("R") = "employee_name"
    (Nome). Resultado do teste: 4985 linhas brutas -> 0 CPFs invalidos ->
    4985 linhas finais (todas ja vinham com Valor Liberado dentro da faixa
    filtrada na origem).
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


def _parse_valor_liberado(coluna: pd.Series) -> pd.Series:
    """O export do Astor Tech entrega esta coluna ja como numero decimal
    (ex. 5001.59), nao como string de moeda formatada (ex. "R$ 5.001,59").
    Se ja vier numerica, usa direto - aplicar a limpeza de string (que
    remove "." como separador de milhar) nesse caso apagaria o ponto
    decimal e infla o valor em 100x (bug confirmado em 20/07/2026 com
    arquivo real: 5001.59 virava 500159).
    """
    if pd.api.types.is_numeric_dtype(coluna):
        return pd.to_numeric(coluna, errors="coerce")
    return pd.to_numeric(
        coluna.astype(str).str.replace(r"[R$\s.]", "", regex=True).str.replace(",", "."),
        errors="coerce",
    )


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
            "Valor Liberado": _parse_valor_liberado(df.iloc[:, idx_valor]),
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
