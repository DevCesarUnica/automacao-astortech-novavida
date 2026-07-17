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
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import settings
from src.browser_utils import click_control_below_label, close_overlays
from src.logging_setup import get_logger

logger = get_logger("astor_extraction")

FILTRO_VALOR_LIBERADO_TEXTO = "R$4001,00 à R$8000,99"
FILTRO_PERIODO_TEXTO = "<= 24 HORAS"


def _login(page) -> None:
    page.goto(settings.ASTOR_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(800)
    page.get_by_label("Endereço de e-mail").fill(settings.ASTOR_USER)
    page.get_by_label("Senha").fill(settings.ASTOR_PASS)
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_timeout(3000)
    if "entrar" in page.url:
        raise RuntimeError("Login no Astor Tech falhou (permaneceu na tela de login).")
    close_overlays(page)
    logger.info("Login no Astor Tech OK. URL: %s", page.url)


def _navegar_ate_painel_controle(page) -> None:
    page.get_by_text("Análise", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(800)
    page.get_by_text("Painel de Controle", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(2000)
    close_overlays(page)
    logger.info("Painel de Controle carregado. URL: %s", page.url)


def _selecionar_tipo_consulta(page) -> None:
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
    """Seleciona as linhas da tabela de filtros rapidos (Valor Liberado /
    Limite por Periodo) que aparece no fim da pagina apos consultar.

    CONFIRMADO ao vivo em 17/07/2026: clicar no texto da celula (<td>) NAO
    seleciona o filtro (a tela mostra o toast "Nenhum filtro selecionado!").
    Cada linha tem um radio button (circulo) em uma celula separada, a
    esquerda da coluna de texto - e nele que o clique precisa acontecer.
    """
    page.keyboard.press("End")
    page.wait_for_timeout(1200)

    for texto in (FILTRO_VALOR_LIBERADO_TEXTO, FILTRO_PERIODO_TEXTO):
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
    logger.info("Filtros atualizados (Valor Liberado + Limite por Periodo).")


def _exportar(page, nome_arquivo: str) -> None:
    page.get_by_role("button", name="Exportar").click(timeout=5000)
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

    close_overlays(page)
    page.wait_for_timeout(300)
    linha.locator("button").last.click(timeout=5000)
    page.wait_for_timeout(500)

    with page.expect_download(timeout=60000) as download_info:
        page.get_by_text("Download", exact=True).click(timeout=5000)
    download = download_info.value

    extensao = Path(download.suggested_filename).suffix or ".xlsx"
    destino = download_dir / f"{nome_arquivo}{extensao}"
    download.save_as(str(destino))
    logger.info("Arquivo bruto salvo em: %s", destino)
    return destino


def extrair(permitir_consulta_real: bool = False) -> Path:
    """Executa o ciclo completo de extracao no Astor Tech.

    `permitir_consulta_real` e um trava de seguranca proposital: consultas no
    Astor Tech podem ter custo por CPF retornado (bureau de dados). So passe
    True apos confirmar com o negocio/financeiro que o custo por consulta e
    aceitavel para rodar em producao.
    """
    if not permitir_consulta_real:
        raise RuntimeError(
            "Extracao real bloqueada por seguranca: chame extrair(permitir_consulta_real=True) "
            "apenas apos confirmar o custo por consulta no Astor Tech."
        )

    nome_arquivo = f"UY3_{datetime.now():%d%m}_{settings.PERFIL_BASE}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
        finally:
            browser.close()


if __name__ == "__main__":
    extrair(permitir_consulta_real=False)
