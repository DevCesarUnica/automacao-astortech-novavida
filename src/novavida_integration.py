"""Modulo 3: Integracao Nova Vida (ver secao 5 do estudo de viabilidade).

STATUS: LOGIN E TELA DE UPLOAD MAPEADOS. Disparo de job (upload real) AINDA
NAO IMPLEMENTADO - pendente de decisao de negocio (ver abaixo).

Confirmado ao vivo em 17/07/2026 (URL fornecida pelo usuario):
  - URL: https://ipe.novavidati.com.br/IndicadoresGerais (redireciona para
    login automaticamente quando nao autenticado). Login funciona com os
    campos #sUsuario (name=sUsuario), #sSenha, name=sCliente.
  - Apos login, tela "Enriquecimentos" (menu lateral, URL /Enriquecimento)
    e onde ocorre o upload/higienizacao. Botao "Adicionar" abre o modal
    "Novo enriquecimento" com os campos (ver detalhes e opcoes vistas em
    docs/Orientacoes_Automacao_AstorTech_NovaVida.txt, secao 13):
      select#campanhaselect, select#subcampanha, select#processo,
      select#layoutEntrada, select#layoutSaida, area de upload
      (drag-and-drop / input[type=file]), botao "Iniciar job".

NAO CONFIRMADO (por isso o disparo real do job fica atras de uma trava,
"permitir_job_real", igual ao padrao usado em src/astor_extraction.py):
  - Qual Campanha/Subcampanha, Processo e par de Layouts (entrada/saida)
    a automacao deve selecionar para bater com o layout final esperado
    (secao 10 do documento de orientacoes: CPF, NOME, VALOR LIBERADO,
    TELEFONE, EMAIL). Escolher o processo errado pode gerar custo e/ou
    devolver dados fora do padrao esperado pela operacao. Esses valores
    ficam em config/settings.py (NOVAVIDA_CAMPANHA, NOVAVIDA_PROCESSO,
    NOVAVIDA_LAYOUT_ENTRADA, NOVAVIDA_LAYOUT_SAIDA) e sao lidos do .env -
    hoje estao vazios de proposito.
  - Como acompanhar o status ate concluir e baixar o resultado (o botao
    "Download Alternativo" no historico nao foi testado, para evitar
    baixar dados reais de clientes sem autorizacao). Por isso
    _baixar_resultado() abaixo ainda e um stub.

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
    "NOVAVIDA_LAYOUT_ENTRADA": settings.NOVAVIDA_LAYOUT_ENTRADA,
    "NOVAVIDA_LAYOUT_SAIDA": settings.NOVAVIDA_LAYOUT_SAIDA,
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


def _abrir_modal_novo_enriquecimento(page):
    page.get_by_role("link", name="list Enriquecimentos").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Adicionar").click()
    page.wait_for_timeout(1000)
    modal = page.locator(".modal, [role='dialog']").filter(has_text="Novo enriquecimento").first
    modal.wait_for(timeout=5000)
    return modal


def _validar_configuracao_job() -> None:
    faltando = [nome for nome, valor in CONFIG_JOB_OBRIGATORIA.items() if not valor]
    if faltando:
        raise RuntimeError(
            "Configuracao de negocio do Nova Vida incompleta - faltam: "
            f"{', '.join(faltando)}. Defina essas variaveis no .env (ver "
            "docs/Orientacoes_Automacao_AstorTech_NovaVida.txt secao 13 para as opcoes "
            "disponiveis) antes de disparar um job real."
        )


def _selecionar_campos(modal) -> None:
    modal.locator("#campanhaselect").select_option(label=settings.NOVAVIDA_CAMPANHA)
    if settings.NOVAVIDA_SUBCAMPANHA:
        modal.locator("#subcampanha").select_option(label=settings.NOVAVIDA_SUBCAMPANHA)
    modal.locator("#processo").select_option(label=settings.NOVAVIDA_PROCESSO)
    modal.locator("#layoutEntrada").select_option(label=settings.NOVAVIDA_LAYOUT_ENTRADA)
    modal.locator("#layoutSaida").select_option(label=settings.NOVAVIDA_LAYOUT_SAIDA)


def _fazer_upload(modal, caminho_csv: Path) -> None:
    modal.locator("input[type='file']").set_input_files(str(caminho_csv))
    logger.info("Arquivo anexado ao modal 'Novo enriquecimento': %s", caminho_csv.name)


def _baixar_resultado(page, id_enriquecimento: str) -> Path:
    raise NotImplementedError(
        "Download do resultado (botao 'Download Alternativo' no historico de "
        "Enriquecimentos) ainda nao foi testado - evitar baixar dados reais de "
        "clientes sem autorizacao explicita. Mapear esta etapa antes de usar."
    )


def upload_e_higienizar(caminho_csv: Path, permitir_job_real: bool = False) -> Path | None:
    _validar_configuracao_job()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        try:
            _login(page)
            modal = _abrir_modal_novo_enriquecimento(page)
            _selecionar_campos(modal)
            _fazer_upload(modal, caminho_csv)

            if not permitir_job_real:
                modal.get_by_role("button", name="Cancelar").click()
                logger.warning(
                    "permitir_job_real=False: modal preenchido e validado, mas job NAO "
                    "foi disparado (sem custo). Chame com permitir_job_real=True para "
                    "efetivamente iniciar o enriquecimento."
                )
                return None

            modal.get_by_role("button", name="Iniciar job").click()
            page.wait_for_timeout(2000)
            logger.info("Job de enriquecimento iniciado no Nova Vida para %s", caminho_csv.name)

            raise NotImplementedError(
                "Job iniciado, mas acompanhamento de status e download automatico do "
                "resultado ainda nao foram implementados (ver _baixar_resultado)."
            )
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
