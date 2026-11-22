# Motor de temas · contrato para la sección «Apariencia» (v2.90, fase A)

Paquete `hub.themes`: Python puro (sin pygame). El Hub es el **backend**: resuelve la apariencia, la aplica y la publica.
La sección de personalización (otro programa o chat) solo LEE y PIDE cambios; no toca `ui.py`.

## Qué hay
| Pieza | Para qué |
|---|---|
| `legacy.catalog()` | Lista para pintar la pantalla: 15 temas (14 heredados + Obsidian) → paletas (colores de muestra) y fondos disponibles |
| `legacy.build(tema, paleta, fondo)` | Dict que aplica el Hub (idéntico a `themes_fam.build`; lo prueba `tests_pro/test_v290.py`) |
| `legacy.appearance(...)` | La misma apariencia por secciones: `colors`, `layout`, `typography`, `audio`, `motion`, `geometry` |
| `legacy.check_contrast(colors)` | Lista vacía = la paleta cumple el contraste del Hub (mismas reglas que `test_v238`). Úsala con cualquier color propio |
| `publish.publish(ruta, tema, paleta, fondo)` | Escribe `appearance.json` de forma atómica |
| `ThemeEngine`, `resolve`, `PRESETS`… | Base del modelo nuevo (presets + paleta + material + ajustes). Aún NO lo usa el Hub |

## Cómo se entera la sección de Apariencia
1. Lee `data/appearance.json` (el Hub lo reescribe cada vez que cambia el tema, paleta o fondo).
2. Para pedir un cambio: escribe `data/appearance-request.json` (ver «Protocolo de peticiones», abajo). El Hub lo revisa cada ~1 s.

## Reglas que NO se pueden romper
- Tema y paleta siempre pasan por `normalize()`: un nombre guardado desconocido cae en «limpio/oscuro», nunca falla.
- Todo color propio se valida con `check_contrast` antes de guardarlo.
- Una paleta no cambia la estructura del tema (tipografía, sonido, forma del Inicio): eso lo fija el tema.
- `catalog_data.py` es una foto generada: se regenera con `python3 tools_user/gen_theme_snapshot.py` (lee `src/hub/themes_fam.py` y los temas base de `ui.py`; hay que regenerarla cada vez que cambie `themes_fam.py`, y `test_v290` falla si no coinciden).
- Hay que mantener los botones ≥ 7,2 mm y las 1000+ pruebas verdes.

## Dos formatos de datos (NO mezclarlos)
| | Formato del Hub (v2.90+) | Formato del motor nuevo |
|---|---|---|
| Quién lo produce | `legacy.appearance()` / `publish.publish()` → `data/appearance.json` | `ThemeEngine.to_dict()` / `resolve()` |
| `schema_version` | **2** | **1** |
| Modelo | 15 temas (familias) × 59 paletas × fondos; colores `BG, PANEL, …, ORBS` | presets + paleta + layout + material + ajustes |
| Lo usa hoy | **El Hub** (lo que se ve en pantalla) | Nadie todavía (base de futuro) |
La transición se decidirá con el responsable de Apariencia: hasta que el modelo nuevo tenga equivalencia visual comprobada con los 14 temas, `legacy.build()` debe seguir idéntico a `themes_fam.build()` y el formato 2 es el que manda. Un lector debe mirar `schema_version` y rechazar lo que no conozca.

## Protocolo de peticiones (v2.91)
Quien personaliza escribe `data/appearance-request.json`; el Hub lo recoge (revisa cada ~1 s), valida, aplica y confirma:
```json
{"schema_version": 1, "request_id": "abc123", "changes": {"theme": "neon", "palette": "lima", "background": "stars"}}
```
- `changes`: solo `theme`, `palette`, `background` (todo opcional, mínimo uno). Un campo desconocido, un tema/paleta/fondo inexistente, una paleta que no es del tema o un contraste insuficiente → se rechaza la petición ENTERA y no cambia nada.
- Confirmación: `appearance.json` → `"request": {"id", "status": "applied"|"rejected"|"duplicate", "errors": [...]}`. Hay que esperar a que `request.id` sea el tuyo.
- El mismo `request_id` no se aplica dos veces (tampoco tras reiniciar el Hub). Usa un id nuevo en cada petición.
- JSON roto → `rejected` con «JSON ilegible». Los rechazos y los fallos de publicación se anotan en `hub.log` con la etiqueta `[apariencia]`.
- Por escribir: el fichero se escribe entero y de una vez (a un temporal y `os.replace`), para que el Hub nunca lea una petición a medias.
Validador puro (sin Hub): `hub.themes.appearance_request.validate(req, (tema, paleta, fondo))`.

## Estudio de temas (v2.97, prueba)
`hub/themes/studio.py`: las 8 identidades del documento «Visual Design System» (ids `v3:minimal`, `v3:showcase`, `v3:glass`, `v3:flow`, `v3:arcade`, `v3:terminal`, `v3:editorial`, `v3:brutalist`), resueltas con `resolve()` del motor nuevo y traducidas por `studio.to_hub()` (el **adaptador**) al dict que dibuja el Hub. No tocan los 15 temas heredados.
- `studio.palettes(id)`, `studio.layouts(id)`, `studio.backgrounds(id)`: solo lo que declara el preset. `studio.normalize()` corrige cualquier combinación no compatible.
- `studio.appearance(id, paleta, fondo, layout)`: lo que se publica (formato 2) + bloque `studio` con la `Appearance` del motor (formato 1) y `adapter_notes` (qué se aplica y qué no).
- Petición: `{"theme": "v3:flow", "palette": "violet", "layout": "coverflow", "background": "drift"}`. `layout` solo vale para `v3:…`.
- Lo que el adaptador NO aplica todavía (el Hub no lo dibuja): peso «medium», espaciado, intensidad/velocidad del fondo, volumen por tema, sombras/opacidad exactas de cada material, calidad high/balanced/low, organización propia de Explorar/Descargas/Ajustes por tema.

## v3.09 · Campos nuevos en appearance.json
- `quality`: «glass» (alta) | «balanced» (equilibrada: fondo quieto, sin destellos) | «perf» (rendimiento). Para cualquier tema.
- `accessibility`: `{reduce_motion, high_contrast, large_text}` (booleanos). Se aplican en el Hub a TODOS los temas después de construir el dict; un tema no tiene que hacer nada para cumplirlas.
- Solo identidades del Estudio: `motion.speed`, `motion.intensity` (factor; 1,0 = intensidad de los heredados, `intensity_doc / 0.20`), `motion.density`; `type_levels` (7 niveles: size en unidades del Hub, weight regular|medium|bold, case upper|null) y `density` (`compact|comfortable|spacious` con gap, pad y row ≥ 72). Tipos y densidad están **declarados**: el Hub aún no los aplica a las pantallas existentes.
- `studio.engine.appearance.render.quality` = high|balanced|low y `accessibility` del motor reflejan lo mismo.
