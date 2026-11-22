# Pruebas de Recomp Hub + servicio de catálogo

Instalado en `~/Games/recomp-hub-tests`. No modifica Hub, el launcher, Steam ni tu daemon.

```bash
cd ~/Games/recomp-hub-tests
./run_tests.sh offline          # daemon FALSO con fallos inyectados + cobertura de ramas (no toca nada tuyo)
./run_tests.sh live             # contrato contra TU daemon real (health/search/variants de Silent Hill · PlayStation)
./run_tests.sh live-download    # lo anterior + descarga REAL de la variante más pequeña a una carpeta temporal
cat reports/informe.md          # resumen para pegar en el chat
```

Qué decide cada parte:
- **offline** → si falla, el fallo es de Hub (cliente RPC, jobs, UI). Incluye el modal paginado (0–60 opciones, 1280×800 y 1920×1080),
  el error `-2`, el job "completo" sin archivo, 401, timeouts, JSON roto, autoarranque, etc.
- **live / live-download** → si falla, el fallo es del `service.py` (no cumple el contrato). Cada mensaje dice qué espera Hub.

Variables útiles: `CATALOG_LIVE_QUERY`, `CATALOG_LIVE_SYSTEM`, `CATALOG_LIVE_MAX_MB` (por defecto 1500), `CATALOG_LIVE_TIMEOUT` (900 s),
`CATALOG_LIVE_SOURCE` + `CATALOG_LIVE_ITEM` (fuerzan un ítem concreto), `HUB_SRC` (por defecto `~/Games/recomp-hub`).

Elegir qué se descarga en `live-download`: `CATALOG_LIVE_FILTER="USA"` (la más pequeña que contenga ese texto) o `CATALOG_LIVE_VARIANT=<variant_id>`.
Los desvíos menores del estándar JSON-RPC salen como "desvíos menores" en el informe y no cuentan como fallo.
