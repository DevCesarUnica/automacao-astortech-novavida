import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from config import settings

OUT_DIR = Path(__file__).resolve().parent


def dump(page, name):
    page.screenshot(path=str(OUT_DIR / "screenshots" / f"{name}.png"), full_page=True)
    (OUT_DIR / "dumps" / f"{name}.html").write_text(page.content(), encoding="utf-8")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(settings.NOVAVIDA_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)

        page.locator("input[name='sUsuario']").fill(settings.NOVAVIDA_USER)
        page.locator("#sSenha").fill(settings.NOVAVIDA_PASS)
        page.locator("input[name='sCliente']").fill(settings.NOVAVIDA_EMPRESA)
        page.get_by_role("button", name="Entrar").click()
        page.wait_for_timeout(4000)
        print("Logado. URL:", page.url)
        dump(page, "nv_01_indicadores")

        # Explorar "Enriquecimentos"
        page.get_by_role("link", name="list Enriquecimentos").click()
        page.wait_for_timeout(3000)
        print("Enriquecimentos URL:", page.url)
        dump(page, "nv_02_enriquecimentos")

        print("=== botoes/links na tela de Enriquecimentos ===")
        for el in page.locator("button, a").all():
            try:
                txt = el.inner_text(timeout=500).strip()
                if txt:
                    print("-", txt)
            except Exception:
                pass

        print("=== inputs (possivel upload) ===")
        for el in page.locator("input").all():
            try:
                print(el.evaluate("e => ({id: e.id, name: e.name, type: e.type, accept: e.accept})"))
            except Exception:
                pass

        # Abrir modal "Adicionar" para mapear o formulario de upload (NAO enviar nada)
        page.get_by_role("button", name="Adicionar").click()
        page.wait_for_timeout(1500)
        dump(page, "nv_03_modal_adicionar")

        print("=== opcoes dos selects visiveis no modal ===")
        modal = page.locator(".modal, [role='dialog']").filter(has_text="Novo enriquecimento").first
        for sel in modal.locator("select").all():
            try:
                sel_id = sel.get_attribute("id") or "(sem id)"
                opts = [o.strip() for o in sel.locator("option").all_inner_texts()]
                print(f"-- select #{sel_id}: {opts}")
            except Exception as e:
                print("erro:", e)

        # IMPORTANTE: NAO clicar em "Iniciar job" nem soltar arquivo - isso dispararia
        # um job real de enriquecimento (possivel custo). Apenas fechar o modal.
        page.get_by_role("button", name="Cancelar").click()
        page.wait_for_timeout(500)
        print("Modal fechado sem iniciar job (sem custo gerado).")

        browser.close()


if __name__ == "__main__":
    main()
