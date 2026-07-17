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


def click_below_label(page, label_text, exact=True):
    label = page.get_by_text(label_text, exact=exact).first
    label_box = label.bounding_box()
    candidates = page.locator("div, input, span").all()
    found = []
    for el in candidates:
        try:
            box = el.bounding_box()
            if not box or not label_box:
                continue
            if abs(box["x"] - label_box["x"]) < 15 and 0 < (box["y"] - label_box["y"]) < 60:
                cls = el.get_attribute("class") or ""
                found.append((box["y"] - label_box["y"], el, cls))
        except Exception:
            continue
    found.sort(key=lambda t: t[0])
    if found:
        found[0][1].click(timeout=5000)
        return True
    return False


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

        click_below_label(page, "Tipo da Consulta")
        page.wait_for_timeout(800)
        page.get_by_text("Banco UY3 CLT", exact=True).click(timeout=5000)
        page.wait_for_timeout(1500)

        # Clicar no icone de funil dentro do card "Filtros"
        funil = page.locator("mat-icon:has-text('filter'), .mat-icon:has-text('filter')")
        print("qtd icones filter:", funil.count())
        if funil.count() == 0:
            # tentar por svg/icon generico proximo ao titulo Filtros
            funil = page.locator("text=Filtros").first.locator(
                "xpath=ancestor::*[self::div][1]//button | ancestor::*[self::div][1]//mat-icon"
            )
            print("fallback qtd:", funil.count())
        funil.first.click(timeout=5000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_funil_aberto.png"), full_page=True)

        print("=== Textos apos clicar funil ===")
        for el in page.locator("label, span, div").all()[:250]:
            try:
                t = el.inner_text().strip()
                if t and len(t) < 50:
                    print(repr(t))
            except Exception:
                pass

        browser.close()


if __name__ == "__main__":
    main()
