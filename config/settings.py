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
# Vida). Confirmado pelo usuario em 20/07/2026 via inspecao ao vivo do modal
# real: so existem os campos Campanha (#campanhaselect) e Processo
# (#processo) - ver guard em src/novavida_integration.py.
NOVAVIDA_CAMPANHA = os.environ.get("NOVAVIDA_CAMPANHA", "")
NOVAVIDA_PROCESSO = os.environ.get("NOVAVIDA_PROCESSO", "")

VALOR_MIN = float(os.environ.get("VALOR_MIN", "4001.00"))
VALOR_MAX = float(os.environ.get("VALOR_MAX", "8000.99"))
VALOR_MINIMO_REGRA_NEGOCIO = 4000.00  # regra: Valor Liberado > R$4.000,00 (estudo, secao 2.1 item 8)
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

# Colunas adicionadas conforme PDF "Automacao Astor Tech -> Nova Vida" (v2).
# O, Q e S confirmados contra arquivo real (data/astor_bruto/UY3_2107_CLT.zip):
# O=number_of_payments, Q=request_date, S=birth_date - batem com o PDF.
# T no PDF e' chamada de "Valor da Parcela", mas no arquivo real T e'
# available_margin (Margem Disponivel) - nao existe campo de valor de
# parcela mensal no export do Astor Tech. Mantida mesmo assim, rotulada
# pelo conteudo real (ver src/consolidacao.py), ate o negocio confirmar.
COLUNA_NUM_PARCELAS = "O"
COLUNA_DATA_CONSULTA = "Q"
COLUNA_DATA_NASCIMENTO = "S"
COLUNA_MARGEM_DISPONIVEL = "T"

# Filtro pos-tratamento: manter so leads consultados nas ultimas N horas
# (secao "Aplicacao dos Filtros" do PDF, exemplo dado: 6 horas). Elevado o
# fallback de 6 para 12 em 06/08/2026: ciclo real as 11h08 zerou leads porque
# o "Data da Consulta" mais recente no export do Astor Tech estava 8h37min
# atrasado em relacao ao horario do ciclo - ver .env.
FILTRO_HORAS_CONSULTA = float(os.environ.get("FILTRO_HORAS_CONSULTA", "12"))

# Envio por e-mail da base final (pedido explicito do usuario em
# 05/08/2026) - ver src/notificacao.py. EMAIL_REMETENTE/EMAIL_SENHA ficam
# vazios por padrao de proposito: enviar_base_por_email() valida e levanta
# erro claro se nao estiverem preenchidos no .env, em vez de falhar calado.
# Para Gmail/Google Workspace, EMAIL_SENHA precisa ser uma "senha de app"
# (nao a senha normal da conta, se houver verificacao em duas etapas).
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE", "")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA", "")
EMAIL_DESTINATARIO = os.environ.get("EMAIL_DESTINATARIO", "cs@unicapromotora.com.br")

DATA_RAW_DIR = BASE_DIR / "data" / "astor_bruto"  # export direto do Astor Tech, sem tratamento
DATA_TREATED_DIR = BASE_DIR / "data" / "treated"
DATA_FINAL_DIR = BASE_DIR / "data" / "final"
DATA_NOVAVIDA_DIR = BASE_DIR / "data" / "novavida"
DATA_ENTREGAS_DIR = BASE_DIR / "data" / "entregas"
LOGS_DIR = BASE_DIR / "logs"

for _dir in (DATA_RAW_DIR, DATA_TREATED_DIR, DATA_FINAL_DIR, DATA_NOVAVIDA_DIR, DATA_ENTREGAS_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
