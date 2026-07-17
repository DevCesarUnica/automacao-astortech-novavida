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

        filtros_label = page.get_by_text("Filtros", exact=True).first
        fbox = filtros_label.bounding_box()
        print("Filtros label box:", fbox)

        # icone deve estar na mesma linha (y proximo), x bem maior (extremo direito do card)
        icons = page.locator("svg, mat-icon, button").all()
        cands = []
        for el in icons:
            try:
                box = el.bounding_box()
                if not box or not fbox:
                    continue
                if abs(box["y"] - fbox["y"]) < 20 and box["x"] > fbox["x"] + 100:
                    cands.append((box["x"], box, el))
            except Exception:
                continue
        cands.sort(key=lambda t: t[0])
        for x, box, el in cands:
            print("x=", x, "box=", box, "tag=", el.evaluate("e=>e.tagName"))

        if cands:
            cands[0][2].click(timeout=5000)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT_DIR / "screenshots" / "astor_funil_aberto2.png"), full_page=True)
            print("=== textos apos clique ===")
            for el in page.locator("label, span, div, mat-label").all()[:300]:
                try:
                    t = el.inner_text().strip()
                    if t and len(t) < 50:
                        print(repr(t))
                except Exception:
                    pass
        else:
            print("Nenhum icone candidato encontrado")

        browser.close()


if __name__ == "__main__":
    main()
