# Automação Astor Tech → Nova Vida

Robô em Python + Playwright que automatiza a extração de leads no **Astor Tech**, aplica as regras de negócio de elegibilidade e envia a base para higienização/enriquecimento no **Nova Vida (Plataforma Ipê)**.

Elimina o processo manual de extrair a base, filtrar colunas, aplicar a regra de valor liberado e subir o arquivo para higienização — reduzindo o tempo entre a geração do lead e sua disponibilização para a operação.

## Sumário

- [Visão geral do fluxo](#visão-geral-do-fluxo)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Guardas de segurança](#guardas-de-segurança)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Status do projeto](#status-do-projeto)
- [Documentação adicional](#documentação-adicional)
- [Créditos](#créditos)
- [Licença](#licença)

## Visão geral do fluxo

```
Astor Tech                      Tratamento local                Nova Vida
┌─────────────────┐            ┌──────────────────┐            ┌─────────────────────┐
│ Login            │            │ Seleciona colunas │            │ Login                │
│ Painel de        │  export    │ CPF / Nome /       │  upload    │ Enriquecimentos      │
│ Controle →        │ ─────────▶│ Valor Liberado     │ ─────────▶│ (Novo enriquecimento)│
│ Banco UY3 CLT     │  (bruto)  │ Valida CPF (dv)    │  (CSV)    │ Campanha/Processo/    │
│ Consultar/Exportar│            │ Filtra > R$4.000   │            │ Layouts               │
└─────────────────┘            │ Dedup (24h)        │            └─────────────────────┘
                                └──────────────────┘
```

O orquestrador (`src/orchestrator.py`) executa esse ciclo sob demanda ou em intervalos programados, com trava de concorrência e deduplicação contra um histórico de CPFs já processados nas últimas 24h.

## Estrutura do projeto

```
.
├── config/
│   └── settings.py            # Configuração central, lida de variáveis de ambiente
├── src/
│   ├── astor_extraction.py    # Login + navegação + extração no Astor Tech
│   ├── data_treatment.py      # Seleção de colunas, validação de CPF, regra de valor
│   ├── novavida_integration.py# Login + upload no Nova Vida (Plataforma Ipê)
│   ├── orchestrator.py        # Orquestração, lock, deduplicação, agendamento
│   ├── cpf_utils.py           # Validação/normalização de CPF
│   ├── browser_utils.py       # Utilitários de navegação (fechar overlays, etc.)
│   └── logging_setup.py       # Logging estruturado com rotação de arquivo
├── explore/                    # Scripts usados para mapear ao vivo a UI dos sistemas
├── docs/                       # Estudo de viabilidade e orientações do processo
├── data/{raw,treated,final}/   # Saída de cada etapa do pipeline (git-ignorado)
├── logs/                       # Logs de execução (git-ignorado)
├── .env.example                 # Modelo de variáveis de ambiente
└── requirements.txt
```

## Guardas de segurança

Ambos os sistemas de origem/destino têm efeitos com custo real (bureau de dados) ou que
disparam processamento de dados de clientes. Por isso o código nunca executa essas ações
por acidente:

| Trava | Onde | Comportamento padrão |
|---|---|---|
| `permitir_consulta_real` | `astor_extraction.extrair()` | `False` — recusa consultar/exportar no Astor Tech (possível custo por CPF retornado) até ser chamado explicitamente com `True` |
| `permitir_job_real` | `novavida_integration.upload_e_higienizar()` | `False` — preenche e valida o formulário de upload no Nova Vida, mas cancela antes de clicar em "Iniciar job" |
| Validação de configuração | `novavida_integration._validar_configuracao_job()` | Bloqueia com erro claro se Campanha/Processo/Layouts de saída não estiverem definidos no `.env` (decisão de negócio pendente) |

O orquestrador expõe as mesmas travas via CLI: `--permitir-consulta-real` e `--permitir-novavida-job-real`.

## Requisitos

- Python 3.11+
- Google Chrome/Chromium (instalado automaticamente pelo Playwright)

## Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

## Configuração

Copie `.env.example` para `.env` e preencha com as credenciais reais (o arquivo `.env`
nunca deve ser versionado — já está no `.gitignore`):

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `ASTOR_URL`, `ASTOR_USER`, `ASTOR_PASS` | Credenciais de acesso ao Astor Tech |
| `NOVAVIDA_URL`, `NOVAVIDA_USER`, `NOVAVIDA_PASS`, `NOVAVIDA_EMPRESA` | Credenciais de acesso ao Nova Vida (Plataforma Ipê) |
| `NOVAVIDA_CAMPANHA`, `NOVAVIDA_SUBCAMPANHA`, `NOVAVIDA_PROCESSO`, `NOVAVIDA_LAYOUT_ENTRADA`, `NOVAVIDA_LAYOUT_SAIDA` | Seleções do modal "Novo enriquecimento" no Nova Vida — **pendentes de decisão de negócio**, ver `docs/Orientacoes_Automacao_AstorTech_NovaVida.txt` seção 13 para as opções disponíveis |
| `VALOR_MIN`, `VALOR_MAX` | Faixa de referência do "Valor Liberado" (o filtro efetivo aplicado é `> VALOR_MINIMO_REGRA_NEGOCIO`, hoje R$ 4.000,00) |
| `PERFIL_BASE` | Sufixo usado no nome do arquivo exportado (ex.: `CLT`) |
| `INTERVALO_HORAS` | Intervalo entre ciclos no modo loop contínuo |

## Uso

```bash
# Ciclo único (recomendado para agendar via Windows Task Scheduler / cron)
python -m src.orchestrator --once

# Loop contínuo (dispara um ciclo a cada INTERVALO_HORAS)
python -m src.orchestrator

# Autorizando explicitamente etapas com custo/efeito real
python -m src.orchestrator --once --permitir-consulta-real --permitir-novavida-job-real
```

## Status do projeto

Mapeamento feito com testes ao vivo contra os ambientes reais (login, navegação e
preenchimento de formulários), sem disparar ações com custo. Pendências conhecidas:

- Os filtros "Limite por Período: 24h" e "Valor Liberado" descritos no processo original
  **não existem** na tela do Astor Tech testada — a regra de valor é garantida no
  pós-processamento (`data_treatment.py`) independentemente disso.
- Falta decidir Campanha/Processo/Layouts do Nova Vida (variáveis vazias por padrão).
- Download automático do resultado higienizado no Nova Vida ainda não foi mapeado.

Detalhes completos em `docs/Orientacoes_Automacao_AstorTech_NovaVida.txt`.

## Documentação adicional

- [`docs/Estudo_de_Viabilidade_Automacao_AstorTech_NovaVida.txt`](docs/Estudo_de_Viabilidade_Automacao_AstorTech_NovaVida.txt) — estudo de viabilidade, riscos e cronograma.
- [`docs/Orientacoes_Automacao_AstorTech_NovaVida.txt`](docs/Orientacoes_Automacao_AstorTech_NovaVida.txt) — especificação do processo e confirmações de campo mapeadas ao vivo.

## Créditos

Desenvolvido para a **Unica Promotora**.

Créditos: [**cesaraaugustoo**](https://github.com/cesaraaugustoo)

## Licença

Distribuído sob a licença MIT — veja [LICENSE](LICENSE).
