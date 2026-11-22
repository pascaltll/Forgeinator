"""v2.07: Ajustes no recorre el disco en cada fotograma para contar carátulas."""
import time
from hub import covers, config


def test_missing_usa_un_solo_listado(tmp_path, monkeypatch):
    d = tmp_path / "covers"; d.mkdir()
    (d / "a.png").write_bytes(b"x"); (d / "b.jpg").write_bytes(b"x"); (d / "c.txt").write_bytes(b"x")
    monkeypatch.setattr(covers, "dir_", lambda: d)
    es = [{"id": i} for i in "abcd"]
    assert [e["id"] for e in covers.missing(es)] == ["c", "d"]


def test_missing_sin_carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(covers, "dir_", lambda: tmp_path / "nada")
    assert len(covers.missing([{"id": "x"}])) == 1


def test_covers_txt_se_cachea(monkeypatch):
    from hub import ui
    n = {"c": 0}
    monkeypatch.setattr(covers, "missing", lambda es: (n.__setitem__("c", n["c"] + 1), [])[1])
    o = type("O", (), {"entries": [1, 2, 3]})()
    f = ui.UI._covers_txt
    for _ in range(50):
        f(o)
    assert n["c"] == 1
