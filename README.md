# Automação Astor Tech → Nova Vida

Robô em Python + Playwright que automatiza a extração de leads no **Astor Tech**, aplica as regras de negócio de elegibilidade, envia a base para higienização/enriquecimento no **Nova Vida (Plataforma Ipê)**, consolida o resultado numa base final e a distribui por e-mail para a operação.

Elimina o processo manual de extrair a base, filtrar colunas, aplicar a regra de valor liberado, subir o arquivo para higienização, baixar e cruzar o resultado com telefone/e-mail — reduzindo o tempo entre a geração do lead e sua disponibilização para a operação.

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
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│        Astor Tech       │  │     Tratamento local    │  │        Nova Vida        │  │    Consolidação final   │
│Login                    │  │Seleciona colunas        │  │Login                    │  │Cruza base tratada       │
│Painel de Controle →     │  │(CPF/Nome/Valor/         │  │Enriquecimentos          │  │+ telefone/e-mail        │
│Banco UY3 CLT            │  │Parcelas/Datas/Margem)   │  │(Novo enriquecimento)    │  │do Nova Vida             │
│Consultar/Exportar       │  │Valida CPF (dv)          │  │Campanha/Processo/       │  │.xlsx formatado          │
│                         │  │Filtra > R$4.000         │  │Layouts                  │  │E-mail p/ operação       │
│                         │  │Filtra janela de horas   │  │                         │  │(Outlook Web)            │
│                         │  │Dedup (24h)              │  │                         │  │                         │
└─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘

  extrai (bruto)  ──────▶   trata + filtra + dedup   ──────▶   upload + higieniza (CSV)   ──────▶   consolida + envia por e-mail
```

O orquestrador (`src/orchestrator.py`) executa esse ciclo sob demanda ou em intervalos programados, com trava de concorrência, deduplicação contra um histórico de CPFs já processados nas últimas 24h e um resumo legível por ciclo (`logs/resumo_ciclos.txt`).

## Estrutura do projeto

```
.
├── config/
│   └── settings.py            # Configuração central, lida de variáveis de ambiente
├── src/
│   ├── astor_extraction.py    # Login + navegação + extração no Astor Tech
│   ├── data_treatment.py      # Seleção de colunas, validação de CPF, regras de elegibilidade
│   ├── novavida_integration.py# Login + upload/higienização no Nova Vida (Plataforma Ipê)
│   ├── consolidacao.py        # Cruza base tratada com resultado do Nova Vida, gera .xlsx formatado
│   ├── notificacao.py         # Envio da base final por e-mail via Outlook Web
│   ├── relatorio.py           # Resumo legível por humano de cada ciclo (logs/resumo_ciclos.txt)
│   ├── orchestrator.py        # Orquestração, lock, deduplicação, agendamento
│   ├── cpf_utils.py           # Validação/normalização de CPF
│   ├── browser_utils.py       # Utilitários de navegação (fechar overlays, etc.)
│   └── logging_setup.py       # Logging estruturado com rotação de arquivo
├── explore/                            # Scripts usados para mapear ao vivo a UI dos sistemas
├── docs/                               # Estudo de viabilidade e orientações do processo
├── data/{astor_bruto,treated,final,novavida,entregas}/  # Saída de cada etapa do pipeline (git-ignorado)
├── logs/                               # Logs de execução e resumo por ciclo (git-ignorado)
├── .env.example                        # Modelo de variáveis de ambiente
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
| `permitir_criar_campanha` | `novavida_integration.upload_e_higienizar()` | `False` — reaproveita a campanha fixa em `NOVAVIDA_CAMPANHA` (fluxo validado ao vivo); criar campanha nova a cada ciclo via botão "+" nunca foi validado ao vivo, só usar em sessão supervisionada |
| Validação de configuração | `novavida_integration._validar_configuracao_job()` | Bloqueia com erro claro se Processo/Campanha (quando aplicável) não estiverem definidos no `.env` |
| Falha no envio de e-mail | `orchestrator.run_ciclo()` | Não derruba o ciclo — a base final já foi gerada e salva antes do e-mail; a falha fica registrada no log e no resumo do ciclo |

O orquestrador expõe as mesmas travas via CLI: `--permitir-consulta-real`, `--permitir-novavida-job-real` e `--permitir-criar-campanha`.

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
| `NOVAVIDA_CAMPANHA`, `NOVAVIDA_SUBCAMPANHA`, `NOVAVIDA_PROCESSO`, `NOVAVIDA_LAYOUT_ENTRADA`, `NOVAVIDA_LAYOUT_SAIDA` | Seleções do modal "Novo enriquecimento" no Nova Vida. `NOVAVIDA_CAMPANHA` é usada como fallback quando o robô roda com `--permitir-criar-campanha` desligado (padrão) — ver `docs/Orientacoes_Automacao_AstorTech_NovaVida.txt` |
| `VALOR_MIN`, `VALOR_MAX` | Faixa de referência do "Valor Liberado" (o filtro efetivo aplicado é `> VALOR_MINIMO_REGRA_NEGOCIO`, hoje R$ 4.000,00) |
| `FILTRO_HORAS_CONSULTA` | Mantém apenas leads com "Data da Consulta" dentro dessa janela de horas (padrão `12`) |
| `INTERVALO_HORAS` | Intervalo entre ciclos no modo loop contínuo |
| `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` | Não usados no envio (ver nota abaixo) — mantidos como referência/config futura |
| `EMAIL_REMETENTE`, `EMAIL_SENHA` | Conta usada para logar no Outlook Web e enviar a base final. Se a conta tiver MFA ativo, o login automático falha — ver docstring de `src/notificacao.py` |
| `EMAIL_DESTINATARIO` | Destinatário da base final higienizada a cada ciclo |

> **Nota sobre e-mail:** o envio é feito via automação do Outlook Web (Playwright), não via SMTP — o tenant Microsoft 365 da Unica Promotora tem autenticação SMTP desativada. Detalhes em `src/notificacao.py`.

## Uso

```bash
# Ciclo único (recomendado para agendar via Windows Task Scheduler / cron)
python -m src.orchestrator --once

# Loop contínuo (dispara um ciclo a cada INTERVALO_HORAS)
python -m src.orchestrator

# Autorizando explicitamente etapas com custo/efeito real
python -m src.orchestrator --once --permitir-consulta-real --permitir-novavida-job-real

# Truncando a base final para as N primeiras linhas antes do envio ao Nova Vida
python -m src.orchestrator --once --permitir-consulta-real --permitir-novavida-job-real --limite-leads 50

# Navegador visível (não-headless), útil para acompanhar o robô em testes
python -m src.orchestrator --once --headed

# Autorizando criar uma Campanha nova a cada ciclo no Nova Vida (não validado ao
# vivo — só usar em sessão supervisionada, ver Guardas de segurança)
python -m src.orchestrator --once --permitir-novavida-job-real --permitir-criar-campanha
```

Cada ciclo grava um resumo legível em `logs/resumo_ciclos.txt` (uma etapa por linha, `OK`/`FALHOU`/`PULADO`) além do log técnico completo em `logs/automacao.log`.

## Status do projeto

Fluxo completo validado ao vivo ponta a ponta contra os ambientes reais — extração no
Astor Tech, tratamento, upload e higienização no Nova Vida, consolidação da base final
e envio por e-mail — incluindo ciclos reais em produção. Pendências conhecidas:

- Criação de Campanha nova a cada ciclo no Nova Vida (botão "+") ainda não foi validada
  ao vivo — controlada pela flag `--permitir-criar-campanha` (desligada por padrão, ver
  Guardas de segurança).
- O filtro "Valor Liberado" descrito no processo original não existe como filtro rápido
  na tela do Astor Tech — a regra de valor é garantida no pós-processamento
  (`data_treatment.py`) independentemente disso.
- Envio de e-mail depende de a conta remetente não ter MFA ativado (ver
  `src/notificacao.py` para o contorno caso isso mude).

Detalhes completos em `docs/Orientacoes_Automacao_AstorTech_NovaVida.txt`.

## Documentação adicional

- [`docs/Estudo_de_Viabilidade_Automacao_AstorTech_NovaVida.txt`](docs/Estudo_de_Viabilidade_Automacao_AstorTech_NovaVida.txt) — estudo de viabilidade, riscos e cronograma.
- [`docs/Orientacoes_Automacao_AstorTech_NovaVida.txt`](docs/Orientacoes_Automacao_AstorTech_NovaVida.txt) — especificação do processo e confirmações de campo mapeadas ao vivo.
- [`docs/Orientacoes_Automacao_AstorTech_NovaVida_fonte_v2.txt`](docs/Orientacoes_Automacao_AstorTech_NovaVida_fonte_v2.txt) — transcrição da orientação de processo v2 (material fonte).
- [`docs/PDF_Automacao_AstorTech_NovaVida.txt`](docs/PDF_Automacao_AstorTech_NovaVida.txt) — transcrição integral do PDF de especificação do processo.

## Créditos

Desenvolvido para a **Unica Promotora**.

Créditos: [**cesaraaugustoo**](https://github.com/cesaraaugustoo)

## Licença

Distribuído sob a licença MIT — veja [LICENSE](LICENSE).
