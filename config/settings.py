import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ASTOR_URL = os.environ["ASTOR_URL"]
ASTOR_USER = os.environ["ASTOR_USER"]
ASTOR_PASS = os.environ["ASTOR_PASS"]

NOVAVIDA_USER = os.environ["NOVAVIDA_USER"]
NOVAVIDA_PASS = os.environ["NOVAVIDA_PASS"]
NOVAVIDA_EMPRESA = os.environ["NOVAVIDA_EMPRESA"]
NOVAVIDA_URL = os.environ["NOVAVIDA_URL"]

# Selecoes do modal "Novo enriquecimento" (tela Enriquecimentos do Nova
# Vida). NAO DEFINIDAS ainda - decisao de negocio pendente (qual Campanha/
# Processo/Layouts usar). Ficam vazias de proposito ate o usuario confirmar;
# ver guard em src/novavida_integration.py.
NOVAVIDA_CAMPANHA = os.environ.get("NOVAVIDA_CAMPANHA", "")
NOVAVIDA_SUBCAMPANHA = os.environ.get("NOVAVIDA_SUBCAMPANHA", "")
NOVAVIDA_PROCESSO = os.environ.get("NOVAVIDA_PROCESSO", "")
NOVAVIDA_LAYOUT_ENTRADA = os.environ.get("NOVAVIDA_LAYOUT_ENTRADA", "")
NOVAVIDA_LAYOUT_SAIDA = os.environ.get("NOVAVIDA_LAYOUT_SAIDA", "")

VALOR_MIN = float(os.environ.get("VALOR_MIN", "4001.00"))
VALOR_MAX = float(os.environ.get("VALOR_MAX", "8000.99"))
VALOR_MINIMO_REGRA_NEGOCIO = 4000.00  # regra: Valor Liberado > R$4.000,00 (estudo, secao 2.1 item 8)
PERFIL_BASE = os.environ.get("PERFIL_BASE", "CLT")
INTERVALO_HORAS = float(os.environ.get("INTERVALO_HORAS", "1"))

# Tipo de consulta no Astor Tech confirmado ao vivo em 17/07/2026 (Painel de
# Controle > Tipo da Consulta): unica opcao disponivel era "Banco UY3 CLT".
ASTOR_TIPO_CONSULTA = "Banco UY3 CLT"

# Colunas do arquivo bruto exportado pelo Astor Tech, conforme especificacao
# do processo (letras de coluna estilo Excel). CONFIRMADO contra um arquivo
# real em 17/07/2026 (export "UY3_1707_CLT", 4985 linhas): indice 8 (I) =
# registration_number/CPF, indice 13 (N) = liquid_value/Valor Liberado,
# indice 17 (R) = employee_name/Nome. Ver docstring de src/data_treatment.py.
COLUNA_CPF = "I"
COLUNA_NOME = "R"
COLUNA_VALOR_LIBERADO = "N"

DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_TREATED_DIR = BASE_DIR / "data" / "treated"
DATA_FINAL_DIR = BASE_DIR / "data" / "final"
LOGS_DIR = BASE_DIR / "logs"

for _dir in (DATA_RAW_DIR, DATA_TREATED_DIR, DATA_FINAL_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
