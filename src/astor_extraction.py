"""Modulo 1: Extracao Astor Tech (ver secao 5 do estudo de viabilidade).

Fluxo confirmado ao vivo em 17/07/2026:
  login -> Analise > Painel de Controle -> Tipo da Consulta = "Banco UY3 CLT"
  -> Consultar -> Exportar.

CONFIRMADO em 17/07/2026 (reaberto o dropdown "Campo" do bloco de Filtros e
listadas TODAS as opcoes via DOM, sem depender de scroll visual):
  - Os filtros "Limite por Periodo = 24 Horas" e "Valor Liberado" descritos no
    processo NAO EXISTEM como opcoes no dropdown "Campo" nesta conta/ambiente.
    As unicas 9 opcoes disponiveis sao: UF, DDD, Sexo, Idade, Banco,
    Data Nascimento, Data Consulta, Tem Telefone, Status do Telefone.
    Portanto esses dois filtros NAO podem ser aplicados na extracao (tela do
    Astor Tech) da forma como o processo original descreve - nem por engano
    ficaram fora so por scroll: a lista inteira foi extraida via JS.
  - Hipoteses (nao verificadas): (a) esse filtro exista em outro Tipo da
    Consulta que essa conta nao tem acesso a ver (so "Banco UY3 CLT" estava
    disponivel), (b) seja um filtro de outro modulo/tela do Astor Tech,
    (c) a consulta "Banco UY3 CLT" ja venha implicitamente limitada as
    ultimas 24h por natureza do banco/produto, ou (d) o processo descrito
    esteja desatualizado em relacao a versao atual do sistema.
  - Por nao ser possivel filtrar na origem, a regra de Valor Liberado >
    R$4.000,00 e aplicada garantidamente no modulo de tratamento
    (data_treatment.py) sobre a base bruta completa - o resultado final fica
    correto, so a extracao bruta traz mais linhas do que o necessario (sem
    o pre-filtro de 24h/valor que a UI nao oferece).
  - Ainda falta confirmar contra um arquivo exportado real se as colunas
    I/R/N (CPF/Nome/Valor Liberado) batem com o layout de fato.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import settings
from src.browser_utils import click_control_below_label, close_overlays
from src.logging_setup import get_logger

logger = get_logger("astor_extraction")


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
    ok = click_control_below_label(page, "Tipo da Consulta")
    if not ok:
        raise RuntimeError("Nao foi possivel localizar o campo 'Tipo da Consulta'.")
    page.wait_for_timeout(600)
    page.get_by_text(settings.ASTOR_TIPO_CONSULTA, exact=True).click(timeout=5000)
    page.wait_for_timeout(1000)
    logger.info("Tipo da Consulta selecionado: %s", settings.ASTOR_TIPO_CONSULTA)


def _consultar_e_exportar(page, download_dir: Path) -> Path:
    page.get_by_role("button", name="Consultar").click(timeout=5000)
    page.wait_for_timeout(4000)
    logger.info("Consulta disparada.")

    with page.expect_download(timeout=60000) as download_info:
        page.get_by_role("button", name="Exportar").click(timeout=5000)
    download = download_info.value

    nome_arquivo = f"UY3_{datetime.now():%d%m}_{settings.PERFIL_BASE}"
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        try:
            _login(page)
            _navegar_ate_painel_controle(page)
            _selecionar_tipo_consulta(page)
            destino = _consultar_e_exportar(page, settings.DATA_RAW_DIR)
            return destino
        finally:
            browser.close()


if __name__ == "__main__":
    extrair(permitir_consulta_real=False)
