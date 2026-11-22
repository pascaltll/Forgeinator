#!/usr/bin/env python3
"""Construye los archivos de una release de Forgeinator desde el árbol del repositorio:
  install-hub-vX.sh            instalador autoextraíble (código + tests; data/ nunca)
  recomp-hub-update-vX.zip     el mismo instalador + SHA256SUMS (lo aplica la autoactualización desde ~/Games/actualizaciones)
Uso:  python3 tools/make_release.py [--out dist] [--version X]   (la versión, por defecto, la de VERSION)
Solo biblioteca estándar; lo usan el flujo de GitHub Actions y quien quiera construir una release a mano."""
import argparse
import base64
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_TOP = {"data", "tests", "dist", "build", ".git", ".github"}
EOFM = "HUB_" + "EOF"        # el marcador de los heredoc (escrito así para que este archivo pueda ir dentro del instalador)
SKIP_ANY = {"__pycache__", "reports", ".venv", ".pytest_cache"}


def app_files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not (SKIP_ANY & set(p.relative_to(ROOT).parts))
                  and p.relative_to(ROOT).parts[0] not in SKIP_TOP and not p.name.endswith((".pyc", ".zip"))
                  and not p.name.startswith("install-hub"))


def test_files():
    t = ROOT / "tests"
    if not t.is_dir():
        return []
    return sorted(p for p in t.rglob("*") if p.is_file() and not (SKIP_ANY & set(p.relative_to(t).parts))
                  and not p.name.endswith((".pyc", ".xml")) and not p.name.startswith(".coverage"))


HEAD = r'''#!/usr/bin/env bash
# Forgeinator (antes Recomp Hub) -> instala en ~/Games/recomp-hub (o $HUB_DIR). No toca juegos, launcher ni Steam.
set -euo pipefail
DEST="${HUB_DIR:-$HOME/Games/recomp-hub}"
if [ -e "$DEST" ] && [ -z "${FORCE:-}" ]; then
  echo "Ya existe $DEST. Para reinstalar el codigo (data/ se conserva):  FORCE=1 bash $0"; exit 1
fi
mkdir -p "$DEST"/{bin,hub,catalog,data,assets}
write() { mkdir -p "$(dirname "$DEST/$1")"; cat > "$DEST/$1"; }
writeb() { mkdir -p "$(dirname "$DEST/$1")"; base64 -d > "$DEST/$1"; }
'''
TAIL = r'''
chmod +x "$DEST/bin/hub" "$DEST/bin/hub-browser" "$DEST/bin/hub-update" "$DEST/bin/hub-tests" "$DEST/bin/hub-doctor" "$DEST/bin/hub-logs" "$DEST/bin/hub-archivo" "$DEST/main.py"
for cand in python3 /usr/bin/python3; do
  if command -v "$cand" >/dev/null 2>&1; then "$cand" -m py_compile "$DEST"/main.py "$DEST"/hub/*.py && echo "Sintaxis Python OK." || echo "AVISO: py_compile fallo."; break; fi
done
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
cat <<MSG

Instalado en: $DEST
  $DEST/bin/hub --list          (catalogo, sin interfaz)
  $DEST/bin/hub                 (interfaz: tactil + mando)
Para Steam: anade $DEST/bin/hub como juego no-Steam.
MSG
'''


def build_installer(out: Path) -> int:
    parts = [HEAD]
    entries = [(p.relative_to(ROOT).as_posix(), p) for p in app_files()] + [("tests/" + p.relative_to(ROOT / "tests").as_posix(), p) for p in test_files()]
    for rel, p in entries:
        if p.suffix.lower() in (".png", ".jpg"):
            b64 = base64.encodebytes(p.read_bytes()).decode()
            parts.append(f"\n# ── {rel} ──\nwriteb '{rel}' <<'{EOFM}'\n{b64}{EOFM}\n")
            continue
        body = p.read_text(encoding="utf-8")
        assert EOFM not in body, rel
        if body and not body.endswith("\n"):
            body += "\n"
        parts.append(f"\n# ── {rel} ──\nwrite '{rel}' <<'{EOFM}'\n{body}{EOFM}\n")
    parts.append(TAIL)
    out.write_text("".join(parts), encoding="utf-8")
    out.chmod(0o755)
    return len(entries)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="dist")
    ap.add_argument("--version")
    a = ap.parse_args()
    v = a.version or (ROOT / "VERSION").read_text().strip()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inst = out / f"install-hub-v{v}.sh"
    n = build_installer(inst)
    z = out / f"recomp-hub-update-v{v}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.write(inst, inst.name)
        f.writestr("SHA256SUMS", f"{hashlib.sha256(inst.read_bytes()).hexdigest()}  {inst.name}\n")
    print(f"{inst} ({n} archivos) · {z}")


if __name__ == "__main__":
    main()
