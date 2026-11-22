#!/usr/bin/env python3
"""Mira de cerca las listas públicas de proyectos de decomp/recomp ANTES de decidir cuáles importar.
No cambia nada en el Hub. Descarga cada fuente, dice si es parseable, cuántos repos de GitHub encuentra,
cuántos son nuevos respecto al catálogo del Hub y cuánto se solapan entre sí.
Uso:  python3 ~/Games/recomp-hub/tools/probe_sources.py [--save carpeta]   (solo biblioteca estándar)"""
import json
import re
import sys
import urllib.request
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
SRC = {
    "samidyfr": "https://raw.githubusercontent.com/SamidyFR/Game-Decompilations/main/README.md",
    "charlotte": "https://raw.githubusercontent.com/CharlotteCross1998/awesome-game-decompilations/main/README.md",
    "awesome-decomp": "https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/README.md",
    "awesome-decomp-json": "https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/data/games.json",
    "pcgamingwiki": "https://www.pcgamingwiki.com/w/api.php?action=parse&page=List_of_unofficial_ports&prop=wikitext&format=json",
    "recompedia": "https://recompedia.com/",
    "gamewave": "https://gamewave.digital/",
    "decomp.wiki": "https://decomp.wiki/",
}
GH = re.compile(r"https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?=[/)\s\"'#?<]|$)", re.I)


def get(url):
    rq = urllib.request.Request(url, headers={"User-Agent": "recomp-hub-probe/1"})
    with urllib.request.urlopen(rq, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def repos(text):
    out = set()
    for o, r in GH.findall(text):
        if o.lower() not in ("sponsors", "topics", "orgs", "features", "settings") and r.lower() not in ("issues", "pulls"):
            out.add(f"{o}/{r}".lower())
    return out


def hub_repos():
    s = set()
    for f in list((HUB / "catalog").glob("*.json")) + list((HUB / "data").glob("**/*.json")):
        try:
            for m in GH.findall(f.read_text(encoding="utf-8")):
                s.add(f"{m[0]}/{m[1]}".lower())
            for m in re.findall(r'"repo"\s*:\s*"([\w.-]+/[\w.-]+)"', f.read_text(encoding="utf-8")):
                s.add(m.lower())
        except OSError:
            pass
    return s


def main():
    save = Path(sys.argv[sys.argv.index("--save") + 1]) if "--save" in sys.argv else None
    if save:
        save.mkdir(parents=True, exist_ok=True)
    mine = hub_repos()
    print(f"Catálogo actual del Hub: {len(mine)} repos\n")
    found = {}
    for name, url in SRC.items():
        try:
            t = get(url)
        except Exception as ex:  # noqa: BLE001
            print(f"✗ {name:20} no se pudo descargar: {type(ex).__name__} {ex}")
            continue
        if save:
            (save / f"{name}.txt").write_text(t, encoding="utf-8")
        r = repos(t)
        found[name] = r
        kind = "JSON" if t.lstrip()[:1] in "[{" else ("HTML" if "<html" in t[:2000].lower() else "texto/Markdown")
        dyn = " · parece cargarse con JavaScript (sin enlaces en el HTML)" if kind == "HTML" and not r else ""
        print(f"✓ {name:20} {len(t)//1024:5} KB · {kind} · {len(r)} repos GitHub · {len(r - mine)} nuevos para el Hub{dyn}")
        if kind == "JSON":
            try:
                d = json.loads(t)
                d = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
                print(f"    {len(d)} elementos · campos: {sorted(d[0].keys()) if d and isinstance(d[0], dict) else '?'}")
            except ValueError:
                pass
    names = [n for n in found if found[n]]
    if len(names) > 1:
        print("\nSolape entre fuentes (repos en común):")
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                print(f"  {a} ∩ {b}: {len(found[a] & found[b])}")
        union = set().union(*(found[n] for n in names))
        print(f"\nUnión sin repetidos: {len(union)} repos · nuevos para el Hub: {len(union - mine)}")
        for n in names:
            otros = set().union(*(found[m] for m in names if m != n))
            print(f"  aporta solo {n:20}: {len(found[n] - otros - mine)} repos nuevos que ninguna otra fuente tiene")
    if save:
        print(f"\nTextos guardados en {save} (envíame la carpeta o los de cabecera y escribo los indexadores a medida).")


if __name__ == "__main__":
    main()
