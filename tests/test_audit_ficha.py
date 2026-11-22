import pygame, os
from test_temas_y_fuzz import H, ui, run, sin_efectos_reales, estado_limpio  # noqa: F401
from conftest import shot


def test_audit(ui, H, monkeypatch):
    e = next(x for x in ui.entries if x.get("repo"))
    monkeypatch.setattr(H.recipes, "have_distrobox", lambda: True)
    monkeypatch.setattr(H.build, "_CC", {"x": (0, ["fedora"])})
    ui.open_detail(e)
    run(ui, 6)
    out = []
    def rep(name):
        ws = [w for w in ui.widgets if getattr(w, "rect", None) is not None]
        n = len(ws)
        small = min((min(w.rect.w, w.rect.h) for w in ws), default=0)
        out.append(f"{name}: {n} widgets, lado menor mínimo {small}px, pantalla {ui.screen.get_size()}")
        shot(ui, f"audit-{name}.png")
    rep("ficha")
    ui.more_open.add(e["id"])
    for k, _ in ui.TABS:
        ui.more_tab[e["id"]] = k
        run(ui, 6)
        rep("mas-" + k)
    open("/tmp/audit.txt", "w").write("\n".join(out))
