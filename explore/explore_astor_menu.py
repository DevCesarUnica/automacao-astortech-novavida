import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from config import settings

OUT_DIR = Path(__file__).resolve().parent


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

        # Fechar modal promocional se existir (tenta Esc e clique fora)
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass
        # tentar botao de fechar (X) generico
        for sel in ["button[aria-label='Close']", "button:has-text('×')", ".cdk-overlay-backdrop"]:
            try:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click(timeout=2000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                pass

        page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_menu_closed.png"), full_page=True)

        # Listar todos os itens de menu/links de texto na sidebar
        print("=== LINKS/MENU ITEMS ===")
        for el in page.locator("a, [role=button], .nav-link, span").all()[:300]:
            try:
                txt = el.inner_text().strip()
                if txt and len(txt) < 60:
                    print(repr(txt))
            except Exception:
                pass

        browser.close()


if __name__ == "__main__":
    main()
