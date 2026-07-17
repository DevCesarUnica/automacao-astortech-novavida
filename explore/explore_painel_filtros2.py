import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from config import settings

OUT_DIR = Path(__file__).resolve().parent


def close_modal(page):
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass
    for sel in ["button[aria-label='Close']", ".cdk-overlay-backdrop"]:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click(timeout=2000)
                page.wait_for_timeout(500)
        except Exception:
            pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(settings.ASTOR_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)
        page.get_by_label("Endereço de e-mail").fill(settings.ASTOR_USER)
        page.get_by_label("Senha").fill(settings.ASTOR_PASS)
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(4000)
        close_modal(page)

        page.get_by_text("Análise", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(1000)
        page.get_by_text("Painel de Controle", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(2500)

        try:
            page.get_by_role("button", name="Sair").click(timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass

        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        print("=== Todos mat-select na pagina com posicao ===")
        selects = page.locator("mat-select").all()
        for i, el in enumerate(selects):
            try:
                box = el.bounding_box()
                txt = el.inner_text().strip()
                print(i, "box=", box, "text=", repr(txt))
            except Exception as e:
                print(i, "erro", e)

        # Clicar no mat-select mais proximo do label "Tipo da Consulta" (geralmente o 2o, apos o de CPF)
        # Vamos tentar localizar por proximidade via XPath: mat-select logo apos texto "Tipo da Consulta"
        tipo_consulta_select = page.locator(
            "xpath=//*[contains(text(),'Tipo da Consulta')]/following::mat-select[1]"
        )
        tipo_consulta_select.click(timeout=5000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_tipo_consulta_aberto2.png"), full_page=True)

        print("=== Opcoes do dropdown Tipo da Consulta (2a tentativa) ===")
        for el in page.locator("mat-option, [role=option]").all():
            try:
                print(repr(el.inner_text().strip()))
            except Exception:
                pass

        browser.close()


if __name__ == "__main__":
    main()
