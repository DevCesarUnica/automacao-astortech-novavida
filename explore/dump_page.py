"""Script de apoio (Fase 0): abre uma URL, tira screenshot e salva o HTML
renderizado para inspecao manual de seletores. Uso:
    python explore/dump_page.py <url> <nome_saida> [--wait-selector SEL]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parent
(OUT_DIR / "screenshots").mkdir(exist_ok=True)
(OUT_DIR / "dumps").mkdir(exist_ok=True)


def main():
    url = sys.argv[1]
    name = sys.argv[2]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.screenshot(path=str(OUT_DIR / "screenshots" / f"{name}.png"), full_page=True)
        html = page.content()
        (OUT_DIR / "dumps" / f"{name}.html").write_text(html, encoding="utf-8")
        print(f"OK: screenshot em screenshots/{name}.png, html em dumps/{name}.html")
        browser.close()


if __name__ == "__main__":
    main()
