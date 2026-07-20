"""Modulo 3: Integracao Nova Vida (ver secao 5 do estudo de viabilidade).

STATUS: Fluxo completo mapeado com selectors reais, confirmados pelo usuario
em 20/07/2026 (inspecao ao vivo do modal "Novo enriquecimento" e do botao de
download). Disparo de job real e download automatico do resultado ainda
dependem de teste de ponta a ponta autorizado (ver traves abaixo) para
validar a etapa de download, que e a unica ainda nao exercitada ao vivo.

Confirmado ao vivo em 17/07/2026 (URL fornecida pelo usuario):
  - URL: https://ipe.novavidati.com.br/IndicadoresGerais (redireciona para
    login automaticamente quando nao autenticado). Login funciona com os
    campos #sUsuario (name=sUsuario), #sSenha, name=sCliente.

Confirmado ao vivo em 20/07/2026 (inspecao do HTML real do menu/modal +
teste em modo seguro, permitir_job_real=False, sem disparar job):
  - Menu lateral: link com <span class="main-nav__link-text">Enriquecimentos
    </span>.
  - Botao "Adicionar" (onclick="exibirModalAdicionarEnriquecimento(this)")
    abre o modal "Novo enriquecimento" (#enriquecimentoModal, Bootstrap).
    Selecoes necessarias:
      - select#campanhaselect - usar a opcao "CLT_UY3_1207" (value 6028).
      - select#processo - usar a opcao "NVBOOK CEL OBG - BESTTIMETOCALL"
        (value 1581).
    Esses valores ficam em config/settings.py (NOVAVIDA_CAMPANHA,
    NOVAVIDA_PROCESSO), lidos do .env.
  - O modal TAMBEM tem select#layoutEntrada e select#layoutSaida (a
    suposicao original baseada na documentacao estava certa nisso), mas NAO
    precisam ser selecionados manualmente: o proprio JS do site filtra e
    auto-preenche esses dois campos assim que o Processo e escolhido (unica
    opcao disponivel para o processo 1581 fica selecionada sozinha:
    layoutEntrada=2, layoutSaida=3955). Confirmado lendo o valor dos selects
    apos escolher o Processo.
  - Upload: a dropzone (.upload-file__dropzone) NAO tem um <input
    type="file"> dentro do modal - o input real do Dropzone.js
    (.dz-hidden-input, visibility:hidden) fica anexado fora do modal, direto
    na pagina. _fazer_upload() por isso busca em `page`, nao em `modal`.
  - Botao #iniciarJob dispara o job (efeito real / possivel custo).
  - Apos concluido, o download do resultado e feito clicando no icone
    <span class="material-icons">download</span> associado ao job na lista
    de Enriquecimentos. O arquivo baixado vem zipado (mesmo padrao do Astor
    Tech - ver src/astor_extraction.py), entao _baixar_resultado() salva
    com a extensao sugerida pelo navegador (normalmente .zip) e o pipeline
    de tratamento ja sabe ler .zip.

NAO CONFIRMADO AO VIVO (proxima etapa de validacao):
  - Quanto tempo o job leva para ficar pronto para download e como o status
    e exibido na lista (nome da coluna, texto do estado "concluido" etc.).
    _baixar_resultado() faz polling reabrindo a lista e tentando localizar o
    icone de download na linha mais recente que bater com a Campanha usada;
    se a lista expuser um identificador mais especifico (ID do job, coluna
    de status), ajustar o matching abaixo apos o primeiro teste real.

upload_e_higienizar() faz login, abre o modal "Novo enriquecimento", valida
que a configuracao de negocio foi preenchida, seleciona os campos e anexa o
arquivo. So clica em "Iniciar job" (efeito real / possivel custo) se
permitir_job_real=True E toda a configuracao estiver preenchida; caso
contrario cancela o modal sem disparar nada, so para validar que o
preenchimento funcionaria.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from config import settings
from src.logging_setup import get_logger

logger = get_logger("novavida_integration")

CONFIG_JOB_OBRIGATORIA = {
    "NOVAVIDA_CAMPANHA": settings.NOVAVIDA_CAMPANHA,
    "NOVAVIDA_PROCESSO": settings.NOVAVIDA_PROCESSO,
}


def _login(page) -> None:
    page.goto(settings.NOVAVIDA_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(800)
    page.locator("#sUsuario").fill(settings.NOVAVIDA_USER)
    page.locator("#sSenha").fill(settings.NOVAVIDA_PASS)
    page.locator("#sCliente").fill(settings.NOVAVIDA_EMPRESA)
    page.get_by_role("button", name="Entrar").click()
    page.wait_for_timeout(4000)
    if "Login" in page.url:
        raise RuntimeError(
            "Login no Nova Vida falhou ou nao pode ser confirmado (permaneceu/retornou "
            "para tela de Login). Confirmar URL e credenciais com o usuario antes de seguir."
        )
    logger.info("Login no Nova Vida OK. URL: %s", page.url)


def _ir_para_enriquecimentos(page) -> None:
    page.get_by_text("Enriquecimentos", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(2000)
    logger.info("Tela de Enriquecimentos carregada. URL: %s", page.url)


def _abrir_modal_novo_enriquecimento(page):
    page.get_by_role("button", name="Adicionar").click(timeout=5000)
    page.wait_for_timeout(1000)
    modal = page.locator(".modal, [role='dialog']").filter(has_text="Novo enriquecimento").first
    modal.wait_for(timeout=5000)
    return modal


def _validar_configuracao_job() -> None:
    faltando = [nome for nome, valor in CONFIG_JOB_OBRIGATORIA.items() if not valor]
    if faltando:
        raise RuntimeError(
            "Configuracao de negocio do Nova Vida incompleta - faltam: "
            f"{', '.join(faltando)}. Defina essas variaveis no .env antes de disparar "
            "um job real."
        )


def _selecionar_campos(modal) -> None:
    modal.locator("#campanhaselect").select_option(label=settings.NOVAVIDA_CAMPANHA)
    modal.locator("#processo").select_option(label=settings.NOVAVIDA_PROCESSO)
    logger.info(
        "Campos selecionados no modal: Campanha=%s, Processo=%s",
        settings.NOVAVIDA_CAMPANHA,
        settings.NOVAVIDA_PROCESSO,
    )


def _fazer_upload(page, caminho_csv: Path) -> None:
    """O upload usa uma dropzone (Dropzone.js) cujo <input type="file"> real
    fica fora do DOM do modal (visibility:hidden, anexado globalmente na
    pagina) - confirmado ao vivo em 20/07/2026. Por isso a busca e feita em
    `page`, nao em `modal`.
    """
    page.locator("input[type='file']").first.set_input_files(str(caminho_csv))
    page.wait_for_timeout(1000)
    logger.info("Arquivo anexado ao modal 'Novo enriquecimento': %s", caminho_csv.name)


def _baixar_resultado(page, download_dir: Path, tentativas: int = 15, espera_seg: float = 20.0) -> Path:
    """Aguarda o job aparecer pronto na lista de Enriquecimentos e baixa o
    resultado clicando no icone de download (<span class="material-icons">
    download</span>) da linha correspondente.

    NAO CONFIRMADO AO VIVO ainda (ver docstring do modulo): a linha
    considerada e a que contem o texto da Campanha usada (settings.
    NOVAVIDA_CAMPANHA) e tem o icone de download visivel/clicavel. Se a
    lista tiver colunas de status/ID mais especificas, ajustar o matching
    abaixo apos o primeiro teste real com permitir_job_real=True.
    """
    for tentativa in range(tentativas):
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)

        linha = page.locator(f"tr:has-text('{settings.NOVAVIDA_CAMPANHA}')").first
        if linha.count() > 0:
            botao_download = linha.locator(".material-icons", has_text="download").first
            if botao_download.count() > 0 and botao_download.is_visible():
                with page.expect_download(timeout=60000) as download_info:
                    botao_download.click(timeout=5000)
                download = download_info.value
                extensao = Path(download.suggested_filename).suffix or ".zip"
                destino = download_dir / f"novavida_{settings.NOVAVIDA_CAMPANHA}{extensao}"
                download.save_as(str(destino))
                logger.info("Resultado do Nova Vida baixado em: %s", destino)
                return destino

        logger.info(
            "Resultado do Nova Vida ainda nao disponivel para download (tentativa %d/%d). "
            "Aguardando %.0fs...",
            tentativa + 1,
            tentativas,
            espera_seg,
        )
        page.wait_for_timeout(espera_seg * 1000)

    raise RuntimeError(
        f"Job do Nova Vida (Campanha '{settings.NOVAVIDA_CAMPANHA}') nao ficou disponivel "
        f"para download apos {tentativas} tentativas."
    )


def upload_e_higienizar(caminho_csv: Path, permitir_job_real: bool = False) -> Path | None:
    _validar_configuracao_job()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        try:
            _login(page)
            _ir_para_enriquecimentos(page)
            modal = _abrir_modal_novo_enriquecimento(page)
            _selecionar_campos(modal)
            _fazer_upload(page, caminho_csv)

            if not permitir_job_real:
                modal.get_by_role("button", name="Cancelar").click()
                logger.warning(
                    "permitir_job_real=False: modal preenchido e validado, mas job NAO "
                    "foi disparado (sem custo). Chame com permitir_job_real=True para "
                    "efetivamente iniciar o enriquecimento."
                )
                return None

            page.locator("#iniciarJob").click(timeout=5000)
            page.wait_for_timeout(2000)
            logger.info("Job de enriquecimento iniciado no Nova Vida para %s", caminho_csv.name)

            return _baixar_resultado(page, settings.DATA_NOVAVIDA_DIR)
        finally:
            browser.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        try:
            _login(page)
        finally:
            browser.close()
