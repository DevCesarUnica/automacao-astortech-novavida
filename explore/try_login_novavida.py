import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from config import settings

OUT_DIR = Path(__file__).resolve().parent
NOVAVIDA_URL = settings.NOVAVIDA_URL


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NOVAVIDA_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)

        page.locator("#sSenha").wait_for(timeout=5000)
        print("=== inputs no form de login ===")
        for el in page.locator("input").all():
            try:
                print(el.evaluate("e => ({id: e.id, name: e.name, placeholder: e.placeholder, type: e.type})"))
            except Exception:
                pass

        page.locator("input[placeholder='Usuário']").first.fill(settings.NOVAVIDA_USER)
        page.locator("#sSenha").fill(settings.NOVAVIDA_PASS)
        page.locator("input[placeholder='Cliente']").first.fill(settings.NOVAVIDA_EMPRESA)
        page.screenshot(path=str(OUT_DIR / "screenshots" / "novavida_form_preenchido.png"), full_page=True)

        page.on("console", lambda msg: print("CONSOLE:", msg.type, msg.text))
        page.on("response", lambda resp: print("RESP:", resp.status, resp.url) if "Login" in resp.url or resp.status >= 400 else None)

        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(8000)

        print("URL apos login:", page.url)
        print("Title:", page.title())
        html = page.content()
        (OUT_DIR / "dumps" / "novavida_after_login.html").write_text(html, encoding="utf-8")
        page.screenshot(path=str(OUT_DIR / "screenshots" / "novavida_after_login.png"), full_page=True)

        browser.close()


if __name__ == "__main__":
    main()
