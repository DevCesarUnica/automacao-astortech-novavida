"""Modulo 1: Extracao Astor Tech (ver secao 5 do estudo de viabilidade).

Fluxo completo confirmado pelo usuario em 17/07/2026 (inspecao ao vivo do DOM
real, incluindo o fluxo assincrono de exportacao que antes nao estava
mapeado):

  1. Login.
  2. Menu lateral: Analise -> Painel de Controle.
  3. Campo "Tipo da Consulta" (ng-select) -> selecionar "Banco UY3 CLT".
  4. Clicar em "Consultar" (dispara a consulta - efeito real / possivel
     custo por CPF retornado).
  5. Rolar ate o final da pagina: uma tabela de filtros rapidos aparece com
     os resultados da consulta, listando faixas/linhas selecionaveis (ex.:
     "R$4001,00 a R$8000,99" na faixa de Valor Liberado, "<= 24 HORAS" na
     faixa de tempo). Selecionar as duas linhas correspondentes aos filtros
     obrigatorios do processo (secao 5 do estudo).
  6. Clicar em "Atualizar Filtros" (botao real, distinto do "Consultar" do
     topo - a suposicao anterior de que "Atualizar Filtros" era so um nome
     antigo de "Consultar" estava ERRADA; e um botao separado que reaplica
     a consulta com os filtros rapidos selecionados).
  7. Clicar em "Exportar" (topo). Isso NAO baixa o arquivo diretamente - abre
     um dialogo pedindo o nome da planilha.
  8. Preencher o nome seguindo o padrao "UY3_DDMM_PERFILBASE" (ex.:
     UY3_1707_CLT) e clicar em "Baixar Base". Isso enfileira a geracao do
     export (processo assincrono do lado do Astor Tech).
  9. Ir em "Exportacoes" (menu lateral, /analise/exportacoes), localizar a
     linha com o nome usado no passo 8, abrir o menu de 3 pontos e clicar em
     "Download" para baixar o arquivo de fato.

TESTE REAL DE PONTA A PONTA executado com sucesso em 17/07/2026 (autorizado
explicitamente pelo usuario, que confirmou nao haver custo real nesse
ambiente/plano). Exportacao "UY3_1707_CLT" com 4985 registros, baixada e
tratada com sucesso (0 CPFs invalidos descartados). Achados que corrigiram
suposicoes anteriores:

  - Passo 5 (selecionar filtros rapidos): clicar no TEXTO da celula (<td>)
    NAO seleciona o filtro - a tela mostra o toast "Nenhum filtro
    selecionado!". Cada linha tem um radio button em uma celula separada;
    _selecionar_filtros_rapidos() agora localiza a <tr> ancestral do texto
    e clica no radio dentro dela (fallback: primeira <td> da linha).
  - Passo 8 (Exportar): o dialogo abre e o input de nome e preenchido pelo
    primeiro <input matInput> do overlay, como assumido - funcionou sem
    ajuste.
  - Passo 9 (Exportacoes/Download): o export fica listado com STATUS
    "EM PROCESSAMENTO" (laranja) por um tempo antes de "CONCLUIDO" (verde).
    Clicar em Download enquanto ainda esta "EM PROCESSAMENTO" baixa um JSON
    de erro ({"error":"Arquivo nao encontrado"}) em vez do arquivo real -
    _baixar_de_exportacoes() agora faz polling do TEXTO do status da linha
    (nao so da existencia dela) ate conter "CONCLU". Tambem foi preciso
    fechar overlays residuais (close_overlays) antes de clicar no menu de 3
    pontos, e garantir que o submenu "Analise" esteja expandido antes de
    procurar o link "Exportacoes" (necessario ao reentrar direto nessa
    tela em uma sessao nova).
  - O arquivo entregue pelo "Download" e um .ZIP contendo um unico CSV
    separado por ";" (nao .xlsx como se assumia antes). pandas.read_csv
    consegue ler direto do .zip (compressao/separador auto-detectados por
    _ler_arquivo_bruto() em data_treatment.py) sem precisar descompactar
    manualmente.
  - Colunas do CSV real (24 no total, cabecalho em ingles) CONFIRMAM a
    suposicao original de "Coluna I/R/N" do processo, contando letras de
    coluna estilo Excel (A=1, B=2, ...): indice 8 (Excel "I") =
    "registration_number" (CPF), indice 13 (Excel "N") = "liquid_value"
    (Valor Liberado, ja em reais, ex. 6398.45), indice 17 (Excel "R") =
    "employee_name" (Nome). config/settings.py (COLUNA_CPF="I",
    COLUNA_NOME="R", COLUNA_VALOR_LIBERADO="N") e data_treatment.py ja
    estavam corretos, nao precisaram de ajuste.
  - Confirmado tambem (sem custo, so visitando a tela existente): a tabela
    de Exportacoes tem colunas ID, Data Criacao, Data Finalizacao, Usuario,
    Nome do Arquivo, Qtd. Solicitada, Qtd. Entregue, Status, Acao; a coluna
    "Acao" tem 1 botao (3 pontos) que abre um menu com "Download" e
    "Excluir".

CONFIRMADO (verificacao anterior, ainda valida): os filtros "Limite por
Periodo = 24 Horas" e "Valor Liberado" NAO existem como campo generico no
bloco de Filtros dinamico (Campo/Condicao/Valor) do Painel de Controle -
eles vem da tabela de filtros rapidos pos-consulta (passo 5 acima), no fim
da pagina, so visivel apos rodar uma consulta real.

ATUALIZADO conforme PDF "Automacao Astor Tech -> Nova Vida" (v2):
  - A extracao passou a selecionar SO o filtro rapido de periodo (<=24
    HORAS). O filtro de faixa de Valor Liberado deixou de ser aplicado
    aqui - a regra de negocio (Valor Liberado > R$4.000) ja e' aplicada
    depois, no tratamento (data_treatment.py), entao selecionar a faixa
    aqui tambem era redundante.
  - Nome do arquivo de export mudou de UY3_DDMM_PERFILBASE para
    UY3_DDMM_HHMM (ex.: UY3_0308_1130), conforme os exemplos reais do PDF
    (o texto do PDF menciona "UY3_DDMM_AAAA_HHMM" com ano, mas os prints
    mostram o padrao sem ano - seguimos os prints).
  - O PDF mostra um modal de exportacao ("Enviar para Campanha") com
    campos extras "Finalidade" e "Limite Quantidade de Cliente" que nao
    foram vistos na validacao ao vivo anterior (que so preenchia o nome).
    Ambos aparecem pre-preenchidos nos prints (Finalidade="Baixar Base",
    Limite=valor default do sistema) e o projeto ja controla volume via
    --limite-leads no orchestrator, entao _exportar() NAO foi alterada
    para preenche-los. Se uma sessao live mostrar que vem vazios/
    obrigatorios, usar click_control_below_label() (browser_utils.py) por
    label, mesmo padrao ja usado para "Tipo da Consulta".

CONFIRMADO ao vivo em 04/08/2026: o botao "Exportar" (id real "enviar-
campanha") ficou desabilitado por mais de 6.5s apos "Atualizar Filtros",
estourando o timeout fixo de clique e derrubando o ciclo com
TimeoutError/"element is not enabled". O tempo de recalculo da tabela varia
com o volume de resultados da consulta - _exportar() agora faz polling do
estado do botao (ate 20s) antes de clicar, em vez de um sleep fixo de 3s.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import settings
from src.browser_utils import click_control_below_label, close_overlays
from src.logging_setup import get_logger

logger = get_logger("astor_extraction")

FILTRO_PERIODO_TEXTO = "<= 24 HORAS"


def _login(page) -> None:
    # CONFIRMADO ao vivo em 12/08/2026 (3 de 4 ciclos do dia falharam aqui):
    # um dialogo promocional novo ("Turbine sua prospeccao com o SMS
    # Inteligente", overlay CDK padrao do Angular Material) passou a aparecer
    # logo apos o login e ficava bloqueando a pagina - como close_overlays()
    # so era chamada DEPOIS da checagem de URL, o robo achava que o login
    # tinha falhado (URL ainda parecia estar em "entrar") quando na verdade
    # so estava atras do dialogo. Agora fecha overlays ANTES de checar a URL.
    # CONFIRMADO ao vivo em 12/08/2026 (11h e 12h do mesmo dia): o Astor
    # Tech as vezes fica bem mais lento que o normal pra carregar a tela de
    # login (30s+ contra ~12s do normal, confirmado comparando execucoes
    # reais) - nao e' falha permanente, e' lentidao intermitente do lado
    # deles. Por isso tenta recarregar a pagina ate 3 vezes antes de
    # desistir, em vez de derrubar o ciclo inteiro na primeira lentidao.
    #
    # CONFIRMADO ao vivo em 13/08/2026: a mesma lentidao tambem pode fazer o
    # PROPRIO page.goto() estourar o timeout de 30s (a pagina nem chega a
    # carregar, nao e' so o campo demorando) - isso acontecia FORA do
    # try/except acima (que so cobria a espera pelo campo), entao o ciclo
    # inteiro caia sem tentar de novo. Agora o goto() tambem esta dentro do
    # try, entao qualquer uma das duas lentidoes aciona o mesmo retry.
    for tentativa in range(1, 4):
        try:
            page.goto(settings.ASTOR_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(800)
            page.get_by_label("Endereço de e-mail").wait_for(state="visible", timeout=20000)
            break
        except Exception:
            if tentativa == 3:
                raise
            logger.warning(
                "Astor Tech lento (tentativa %d/3) - pagina ou campo de login nao "
                "carregaram a tempo, tentando de novo.",
                tentativa,
            )

    page.get_by_label("Endereço de e-mail").fill(settings.ASTOR_USER)
    page.get_by_label("Senha").fill(settings.ASTOR_PASS)
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_timeout(3000)
    close_overlays(page)
    if "entrar" in page.url:
        raise RuntimeError("Login no Astor Tech falhou (permaneceu na tela de login).")
    logger.info("Login no Astor Tech OK. URL: %s", page.url)


def _navegar_ate_painel_controle(page) -> None:
    """Confirmado ao vivo em 04/08/2026: o clique em "Painel de Controle"
    pode nao navegar (pagina permanece em /home) quando o submenu "Analise"
    ainda nao terminou de renderizar nos 800ms fixos de espera anteriores -
    o clique acerta um texto igual que ainda nao e o link real. Por isso
    agora o codigo confere a URL apos o clique e tenta de novo (ate 5x) em
    vez de assumir que um unico clique bastou.
    """
    page.get_by_text("Análise", exact=True).first.click(timeout=5000)
    page.get_by_text("Painel de Controle", exact=True).first.wait_for(state="visible", timeout=5000)
    for _ in range(5):
        page.get_by_text("Painel de Controle", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(1000)
        if "painel-controle" in page.url:
            break
    else:
        raise RuntimeError(
            "Clique em 'Painel de Controle' nao navegou para a URL esperada "
            f"(permaneceu em {page.url}) apos varias tentativas."
        )
    close_overlays(page)
    logger.info("Painel de Controle carregado. URL: %s", page.url)


def _selecionar_tipo_consulta(page) -> None:
    # 06/08/2026: o tour Shepherd.js ("step-consulta") e' especifico deste
    # campo e pode aparecer so agora, mesmo depois do close_overlays() ja
    # chamado em _navegar_ate_painel_controle - por isso fecha de novo aqui
    # antes de tentar clicar no combobox (ver close_overlays em browser_utils.py).
    close_overlays(page)
    combobox = page.locator("div[role='combobox'].ng-input").first
    if combobox.count() == 0:
        ok = click_control_below_label(page, "Tipo da Consulta")
        if not ok:
            raise RuntimeError("Nao foi possivel localizar o campo 'Tipo da Consulta'.")
    else:
        combobox.click(timeout=5000)
    page.wait_for_timeout(600)
    page.get_by_text(settings.ASTOR_TIPO_CONSULTA, exact=True).click(timeout=5000)
    page.wait_for_timeout(1000)
    logger.info("Tipo da Consulta selecionado: %s", settings.ASTOR_TIPO_CONSULTA)


def _consultar(page) -> None:
    page.get_by_role("button", name="Consultar").click(timeout=5000)
    page.wait_for_timeout(5000)
    logger.info("Consulta disparada (efeito real / possivel custo por CPF retornado).")


def _selecionar_filtros_rapidos(page) -> None:
    """Seleciona a linha da tabela de filtros rapidos (Limite por Periodo)
    que aparece no fim da pagina apos consultar.

    CONFIRMADO ao vivo em 17/07/2026: clicar no texto da celula (<td>) NAO
    seleciona o filtro (a tela mostra o toast "Nenhum filtro selecionado!").
    Cada linha tem um radio button (circulo) em uma celula separada, a
    esquerda da coluna de texto - e nele que o clique precisa acontecer.

    ATUALIZADO conforme PDF v2: nao seleciona mais o filtro de faixa de
    Valor Liberado aqui (ver docstring do modulo) - so o de periodo.
    """
    page.keyboard.press("End")
    page.wait_for_timeout(1200)

    for texto in (FILTRO_PERIODO_TEXTO,):
        celula = page.get_by_text(texto, exact=True).first
        celula.wait_for(timeout=10000)
        linha = celula.locator("xpath=ancestor::tr[1]")
        radio = linha.locator(
            "input[type='radio'], mat-radio-button, .mdc-radio, [role='radio']"
        ).first
        if radio.count() == 0:
            # Fallback: clicar na primeira celula da linha (coluna do radio),
            # ao inves do texto do valor.
            radio = linha.locator("td").first
        radio.click(timeout=5000)
        page.wait_for_timeout(500)
        logger.info("Filtro rapido selecionado: %s", texto)


def _atualizar_filtros(page) -> None:
    page.get_by_role("button", name="Atualizar Filtros").click(timeout=5000)
    page.wait_for_timeout(3000)
    logger.info("Filtros atualizados (Limite por Periodo).")


def _exportar(page, nome_arquivo: str) -> None:
    """O botao "Exportar" fica desabilitado ate a tabela recalcular os
    resultados apos "Atualizar Filtros" - confirmado ao vivo em 04/08/2026
    (TimeoutError "element is not enabled" mesmo apos os 3s fixos de espera
    em _atualizar_filtros). O tempo de recalculo varia com o volume de
    resultados, entao aqui o codigo faz polling do estado do botao em vez de
    assumir que ja esta pronto.

    CONFIRMADO ao vivo em 13/08/2026: os 20s antigos as vezes nao bastam na
    mesma lentidao intermitente do Astor Tech ja vista no login (ver
    _login) - checagem manual logo apos uma falha real mostrou o botao
    habilitado normalmente, so tinha demorado mais que 20s. Ampliado para
    45s antes de desistir.
    """
    botao_exportar = page.get_by_role("button", name="Exportar").first
    for _ in range(45):
        if botao_exportar.is_enabled():
            break
        page.wait_for_timeout(1000)
    else:
        raise RuntimeError(
            "Botao 'Exportar' permaneceu desabilitado apos 45s esperando os filtros "
            "recalcularem. Pode indicar que a consulta com os filtros aplicados nao "
            "retornou nenhum resultado - verificar manualmente antes de tentar novamente."
        )

    botao_exportar.click(timeout=5000)
    page.wait_for_timeout(1000)

    overlay = page.locator(".cdk-overlay-pane").last
    overlay.locator("input[matinput]").first.fill(nome_arquivo)
    page.get_by_role("button", name="Baixar Base").click(timeout=5000)
    page.wait_for_timeout(2000)
    logger.info("Exportacao '%s' solicitada (geracao assincrona no Astor Tech).", nome_arquivo)


def _baixar_de_exportacoes(
    page, nome_arquivo: str, download_dir: Path, tentativas: int = 15, espera_seg: float = 8.0
) -> Path:
    """Aguarda o export ficar com STATUS "CONCLUIDO" na tela de Exportacoes
    antes de baixar.

    CONFIRMADO ao vivo em 17/07/2026: o export fica listado com status
    "EM PROCESSAMENTO" (laranja) por um tempo antes de virar "CONCLUIDO"
    (verde). Clicar em Download enquanto ainda esta "EM PROCESSAMENTO"
    baixa um JSON de erro ({"error":"Arquivo nao encontrado"}) em vez do
    arquivo real - por isso o polling abaixo verifica o texto do status na
    linha, nao so a existencia da linha.
    """
    link_exportacoes = page.get_by_role("link", name="Exportações")
    if link_exportacoes.count() == 0 or not link_exportacoes.first.is_visible():
        page.get_by_text("Análise", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(800)
    page.get_by_role("link", name="Exportações").click(timeout=5000)
    page.wait_for_timeout(2000)

    linha = page.locator(f"tr:has-text('{nome_arquivo}')").first
    for tentativa in range(tentativas):
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)
        linha = page.locator(f"tr:has-text('{nome_arquivo}')").first
        if linha.count() > 0:
            status = linha.inner_text()
            if "CONCLU" in status.upper():
                break
            logger.info(
                "Export '%s' ainda EM PROCESSAMENTO (tentativa %d/%d). Aguardando %.0fs...",
                nome_arquivo,
                tentativa + 1,
                tentativas,
                espera_seg,
            )
        else:
            logger.info(
                "Export '%s' ainda nao aparece em Exportacoes (tentativa %d/%d). Aguardando...",
                nome_arquivo,
                tentativa + 1,
                tentativas,
            )
        page.wait_for_timeout(espera_seg * 1000)
    else:
        raise RuntimeError(
            f"Export '{nome_arquivo}' nao ficou CONCLUIDO na tela de Exportacoes "
            f"apos {tentativas} tentativas."
        )

    botao_menu = linha.locator("button").last
    for tentativa_clique in range(4):
        close_overlays(page)
        page.wait_for_timeout(300)
        try:
            botao_menu.click(timeout=5000)
            break
        except PlaywrightTimeoutError:
            logger.warning(
                "Clique no menu de acoes da linha '%s' bloqueado por overlay residual "
                "(tentativa %d/4) - chamando close_overlays() de novo.",
                nome_arquivo,
                tentativa_clique + 1,
            )
    else:
        raise RuntimeError(
            f"Nao foi possivel clicar no menu de acoes da linha '{nome_arquivo}' - "
            "overlay/backdrop residual continuou bloqueando o clique mesmo apos varias "
            "tentativas de close_overlays()."
        )
    page.wait_for_timeout(500)

    with page.expect_download(timeout=60000) as download_info:
        page.get_by_text("Download", exact=True).click(timeout=5000)
    download = download_info.value

    extensao = Path(download.suggested_filename).suffix or ".xlsx"
    destino = download_dir / f"{nome_arquivo}{extensao}"
    download.save_as(str(destino))
    logger.info("Arquivo bruto salvo em: %s", destino)
    return destino


def _salvar_evidencia_erro(page, etapa: str) -> None:
    """Salva screenshot + HTML da pagina no momento de uma falha, em
    logs/screenshots/. Nunca deve derrubar o ciclo por conta propria - se a
    pagina/browser ja estiver em estado ruim (ex.: crash), so loga o aviso.
    """
    pasta = settings.LOGS_DIR / "screenshots"
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = pasta / f"{carimbo}_{etapa}"
    try:
        page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
        base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
        logger.info("Evidencia de erro salva em %s.png / .html", base)
    except Exception as e:
        logger.warning("Nao foi possivel salvar evidencia de erro: %s", e)


def extrair(permitir_consulta_real: bool = False, headless: bool = True) -> Path:
    """Executa o ciclo completo de extracao no Astor Tech.

    `permitir_consulta_real` e um trava de seguranca proposital: consultas no
    Astor Tech podem ter custo por CPF retornado (bureau de dados). So passe
    True apos confirmar com o negocio/financeiro que o custo por consulta e
    aceitavel para rodar em producao.
    `headless=False` abre o navegador visivel, util para acompanhar o robo
    em execucao durante testes.
    """
    if not permitir_consulta_real:
        raise RuntimeError(
            "Extracao real bloqueada por seguranca: chame extrair(permitir_consulta_real=True) "
            "apenas apos confirmar o custo por consulta no Astor Tech."
        )

    nome_arquivo = f"UY3_{datetime.now():%d%m_%H%M}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(accept_downloads=True)
        try:
            _login(page)
            _navegar_ate_painel_controle(page)
            _selecionar_tipo_consulta(page)
            _consultar(page)
            _selecionar_filtros_rapidos(page)
            _atualizar_filtros(page)
            _exportar(page, nome_arquivo)
            destino = _baixar_de_exportacoes(page, nome_arquivo, settings.DATA_RAW_DIR)
            return destino
        except Exception:
            # 06/08/2026: em modo headed o navegador fecha (finally abaixo)
            # antes de alguem conseguir olhar a tela apos uma falha, entao um
            # erro ao vivo ficava sem nenhuma pista alem da stack trace. Salva
            # screenshot + HTML da pagina no momento do erro para diagnostico
            # posterior, sem depender de acompanhar a execucao em tempo real.
            _salvar_evidencia_erro(page, "extrair")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    extrair(permitir_consulta_real=False)
