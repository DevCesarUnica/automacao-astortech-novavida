from playwright.sync_api import Page


def close_overlays(page: Page, tentativas: int = 4) -> None:
    """Fecha modais promocionais/tour que aparecem apos o login no Astor Tech.

    Repete o fechamento ate nao sobrar overlay (ate `tentativas` vezes) em vez
    de fechar so um: overlays podem ficar empilhados (ex. toast + tour), e
    fechar so o primeiro deixava um `.cdk-overlay-backdrop` residual capaz de
    interceptar cliques em elementos reais bem depois (bug confirmado em
    21/07/2026: backdrop leftover bloqueou o clique no menu de acoes da tela
    de Exportacoes mesmo apos um close_overlays() + reload de pagina).
    """
    for _ in range(tentativas):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass
        fechou_algo = False
        for sel in ["button[aria-label='Close']", ".cdk-overlay-backdrop"]:
            try:
                loc = page.locator(sel)
                if loc.count() > 0:
                    loc.first.click(timeout=2000)
                    page.wait_for_timeout(300)
                    fechou_algo = True
            except Exception:
                pass
        try:
            if page.get_by_role("button", name="Sair").count() > 0:
                page.get_by_role("button", name="Sair").click(timeout=2000)
                page.wait_for_timeout(300)
                fechou_algo = True
        except Exception:
            pass
        if not fechou_algo:
            break


def click_control_below_label(page: Page, label_text: str, exact: bool = True) -> bool:
    """Clica no controle (mat-select/ng-select/input) posicionado logo abaixo de um
    <label> pelo texto. Necessario porque o Astor Tech (Angular Material + ng-select)
    nao associa alguns labels via for/aria-labelledby, entao get_by_label falha.
    """
    label = page.get_by_text(label_text, exact=exact).first
    label_box = label.bounding_box()
    if not label_box:
        return False

    candidates = page.locator("div, input, span").all()
    found = []
    for el in candidates:
        try:
            box = el.bounding_box()
            if not box:
                continue
            if abs(box["x"] - label_box["x"]) < 15 and 0 < (box["y"] - label_box["y"]) < 60:
                found.append((box["y"] - label_box["y"], el))
        except Exception:
            continue
    found.sort(key=lambda t: t[0])
    if not found:
        return False
    found[0][1].click(timeout=5000)
    return True
