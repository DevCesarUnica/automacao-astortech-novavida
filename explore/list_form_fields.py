"""Lista inputs/buttons/labels visiveis na pagina para descobrir seletores reais."""
import sys

from playwright.sync_api import sync_playwright


def main():
    url = sys.argv[1]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        print("=== INPUTS ===")
        for el in page.locator("input").all():
            try:
                attrs = el.evaluate(
                    "e => ({type: e.type, name: e.name, id: e.id, placeholder: e.placeholder, "
                    "ariaLabel: e.getAttribute('aria-label'), formcontrolname: e.getAttribute('formcontrolname')})"
                )
                print(attrs)
            except Exception as e:
                print("erro:", e)

        print("=== BUTTONS ===")
        for el in page.locator("button").all():
            try:
                txt = el.inner_text().strip()
                attrs = el.evaluate("e => ({type: e.type, id: e.id, className: e.className})")
                print(txt, attrs)
            except Exception as e:
                print("erro:", e)

        browser.close()


if __name__ == "__main__":
    main()
