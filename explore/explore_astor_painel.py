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

        print("URL antes de navegar:", page.url)

        # Clicar em "Gestao de Carteira" (texto do menu, provavelmente maiusculo/label de secao)
        try:
            page.get_by_text("Carteira de clientes", exact=True).first.click(timeout=5000)
            page.wait_for_timeout(1500)
            print("Cliquei em 'Carteira de clientes'. URL:", page.url)
        except Exception as e:
            print("Falha ao clicar Carteira de clientes:", e)

        page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_carteira_1.png"), full_page=True)

        try:
            page.get_by_text("Análise", exact=True).first.click(timeout=5000)
            page.wait_for_timeout(1500)
            print("Cliquei em 'Analise'. URL:", page.url)
        except Exception as e:
            print("Falha ao clicar Analise:", e)

        page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_analise_1.png"), full_page=True)

        print("=== Textos visiveis apos navegacao ===")
        for el in page.locator("a, [role=button], span, button").all()[:400]:
            try:
                txt = el.inner_text().strip()
                if txt and len(txt) < 60:
                    print(repr(txt))
            except Exception:
                pass

        browser.close()


if __name__ == "__main__":
    main()
