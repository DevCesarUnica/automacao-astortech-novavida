import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random

import pandas as pd

from src.data_treatment import tratar
from config import settings


def gerar_cpf_valido():
    def dv(digs, pesos):
        s = sum(d * p for d, p in zip(digs, pesos))
        r = (s * 10) % 11
        return 0 if r == 10 else r

    base = [random.randint(0, 9) for _ in range(9)]
    d1 = dv(base, range(10, 1, -1))
    d2 = dv(base + [d1], range(11, 1, -1))
    return "".join(map(str, base + [d1, d2]))


random.seed(42)
n = 20
cols = {chr(65 + i): [f"col{chr(65+i)}_{j}" for j in range(n)] for i in range(26)}

cpfs = [gerar_cpf_valido() for _ in range(n)]
nomes = [f"Fulano de Tal {j}" for j in range(n)]
valores = [round(random.uniform(2000, 10000), 2) for j in range(n)]

cols["I"] = cpfs
cols["R"] = nomes
cols["N"] = [f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") for v in valores]

# duplicar um CPF e um invalido para testar dedup/validacao
cpfs_dup_idx = 0
cols["I"][1] = cols["I"][0]  # duplicado
cols["I"][2] = "12345678900"  # invalido

df = pd.DataFrame(cols)
raw_path = settings.DATA_RAW_DIR / "UY3_1707_TESTE.xlsx"
df.to_excel(raw_path, index=False)
print("Arquivo de teste gerado:", raw_path)
print("Valores originais (amostra):", valores[:5])

destino = tratar(raw_path)
print("Saida:", destino)
print(pd.read_csv(destino).to_string())
