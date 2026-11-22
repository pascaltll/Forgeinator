#!/usr/bin/env bash
# Uso:  ./run_tests.sh [offline | live | live-download | all] [args de pytest…]
#   offline        (por defecto) suite completa con daemon falso + cobertura de ramas
#   live           contrato contra TU daemon real (health/search/variants), sin descargar
#   live-download  lo anterior + descarga real de una variante pequeña (Silent Hill / PlayStation)
#   all            offline + live-download
set -u
cd "$(dirname "$0")"
MODE="${1:-offline}"; shift || true
export HUB_SRC="${HUB_SRC:-$HOME/Games/recomp-hub}"
[ -f "$HUB_SRC/hub/catalogservice.py" ] || { echo "No encuentro Hub en $HUB_SRC (exporta HUB_SRC=…)"; exit 2; }

# 1) python: el primero que tenga pygame (como bin/hub); si ninguno, python3 (los tests ui se omiten)
PY=""
for c in "$HUB_SRC/.venv/bin/python" python3 /usr/bin/python3 "$HOME/miniconda3/bin/python" "$HOME/anaconda3/bin/python" "$HOME/.venv/bin/python"; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  "$c" -c "import pygame" >/dev/null 2>&1 && { PY="$c"; break; }
done
[ -z "$PY" ] && PY="$(command -v python3)"
echo "== python: $PY ($($PY -c 'import sys;print(sys.version.split()[0])'))  · Hub: $HUB_SRC"
$PY -c "import pygame" >/dev/null 2>&1 || echo "AVISO: ese python no tiene pygame → se omitirán los tests de UI"

# 2) entorno con pytest (hereda pygame del python elegido)
if ! $PY -c "import pytest, pytest_cov" >/dev/null 2>&1; then
  [ -x .venv/bin/python ] || "$PY" -m venv --system-site-packages .venv || { echo "no pude crear .venv"; exit 2; }
  .venv/bin/python -m pip install -q pytest pytest-cov || { echo "no pude instalar pytest (¿sin red?)"; exit 2; }
  PY=.venv/bin/python
fi

mkdir -p reports; export REPORT_DIR="$PWD/reports"
COMMON=(-q --junitxml=reports/junit.xml)
RC=0
case "$MODE" in
  offline)
    "$PY" -m pytest "${COMMON[@]}" --cov="$HUB_SRC/hub" --cov-branch --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml:reports/coverage.xml "$@" || RC=$? ;;
  live)
    CATALOG_LIVE=1 "$PY" -m pytest "${COMMON[@]}" -m live "$@" || RC=$? ;;
  live-download)
    CATALOG_LIVE=1 CATALOG_LIVE_DOWNLOAD=1 "$PY" -m pytest "${COMMON[@]}" -m live "$@" || RC=$? ;;
  all)
    CATALOG_LIVE=1 CATALOG_LIVE_DOWNLOAD=1 "$PY" -m pytest "${COMMON[@]}" --cov="$HUB_SRC/hub" --cov-branch --cov-config=.coveragerc --cov-report=term-missing "$@" || RC=$? ;;
  *) echo "modo desconocido: $MODE"; exit 2 ;;
esac
echo; echo "== informe: $PWD/reports/informe.md   (pégamelo entero si algo falla)"
exit $RC
