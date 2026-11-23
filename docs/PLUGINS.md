# Forgeinator · complementos (plugins) v1

*English summary: a plugin is a zip with a `forgeinator-plugin.json` manifest and a program in any language. Forgeinator starts it when needed and talks to it over stdin/stdout with JSON lines (connector protocol v1: `hello`, `test`, `systems`, `games`, `download`, `cancel`, plus progress messages). Install from Settings › Files › Plugins, from `forgeinator-ctl --plugins instalar ZIP`, or through the client socket (`plugins.install`). See `plugins/catalogo-http/` for a complete example.*

Un complemento añade un **conector**: una forma nueva de llegar a tus juegos (un servidor con API propia, un servicio que rclone no conoce…). Lo que bajes con él va a tu carpeta de ROMs con la estructura de ES-DE, como con cualquier otra biblioteca. Cómo encaja con el resto está en [PROTOCOL.md](PROTOCOL.md).

## 1. Zona de complementos

| Qué | Dónde |
|---|---|
| Complementos instalados | `~/.local/share/forgeinator/plugins/<id>/` (común a estable y dev) |
| Activado o desactivado | `~/.local/share/forgeinator/plugins/estado.json` |
| Versión anterior al actualizar | `~/.local/share/forgeinator/plugins/.anteriores/<id>-<versión>-<fecha>/` |
| Complementos quitados | `~/.local/share/forgeinator/plugins/.papelera/<id>-<fecha>/` |
| Configuración de cada biblioteca | `remotes.json` (sin secretos) y `~/.config/forgeinator/remotes-secrets.json` (600) |

Nada se borra solo: actualizar guarda la versión anterior y quitar mueve la carpeta a la papelera.

**Instalar:**
- **Hub:** Ajustes › Archivos › Complementos › Instalar. Lista los zips de complementos que encuentra en `~/Games/actualizaciones`, `~/Downloads` y `~/Descargas`, o puedes buscar el zip a mano. Antes de instalar enseña el nombre, la versión, el autor y los permisos, y pide confirmación.
- **Terminal:** `bin/forgeinator-ctl --plugins ver ZIP` y luego `bin/forgeinator-ctl --plugins instalar ZIP`.
- **Otro cliente (QAM, teléfono):** `plugins.inspect` y `plugins.install` por el socket de clientes (PROTOCOL.md §2).

**Usar:** Ajustes › Archivos › Bibliotecas remotas › Añadir › «Complemento · <nombre>». Te pide los campos que declara su manifiesto.

## 2. El zip

```
forgeinator-plugin-<id>-<versión>.zip
└── <id>/                       (opcional: puede ir todo en la raíz)
    ├── forgeinator-plugin.json
    ├── main.py                 (o el programa que diga «run»)
    └── …
```

Reglas que se comprueban al instalar:
- Tiene que haber un `forgeinator-plugin.json` válido.
- Ninguna ruta con `..`, absoluta ni con `\`; ningún enlace simbólico.
- Como mucho 64 MB comprimido.
- El programa de `run` está dentro del complemento o es un intérprete permitido: `python3`, `python`, `sh`, `bash` o `node`.

## 3. Manifiesto `forgeinator-plugin.json` (schema 1)

```json
{
  "schema": 1,
  "id": "mi-servidor",
  "name": "Mi servidor",
  "version": "1.2.0",
  "type": "connector",
  "protocol": 1,
  "run": ["python3", "main.py"],
  "description": "Qué hace, en una o dos frases.",
  "author": "Tu nombre",
  "homepage": "https://…",
  "permissions": ["network"],
  "fields": [
    {"key": "url",   "label": "Dirección del servidor", "default": "https://", "required": true},
    {"key": "token", "label": "Token", "secret": true}
  ]
}
```

| Campo | Obligatorio | Notas |
|---|---|---|
| `schema` | sí | `1` |
| `id` | sí | minúsculas, números y guiones; de 2 a 40 caracteres. Es el nombre de la carpeta |
| `name`, `version` | sí | se enseñan al usuario; `version` se compara por números (`1.10.0` > `1.9.0`) |
| `type` | sí | por ahora solo `connector` |
| `protocol` | sí | `1` (protocolo de conectores de este documento) |
| `run` | sí | lista: programa y argumentos. Se ejecuta con la carpeta del complemento como directorio de trabajo |
| `fields` | no | lo que se pide al añadir una biblioteca: `key` (minúsculas, números y `_`), `label`, `default`, `secret`, `required` |
| `permissions` | no | informativo, se enseña antes de instalar: `network`, `files` (fuera de la carpeta de descarga), `exec` (otros programas) |
| `description`, `author`, `homepage` | no | |

## 4. Protocolo de conectores v1 (stdio)

Forgeinator arranca el programa para cada operación (explorar, bajar…), le escribe peticiones por su **entrada estándar** y lee sus respuestas de su **salida estándar**: **un objeto JSON por línea**, en UTF-8. Lo que el complemento escriba por la **salida de errores** acaba en el registro de Forgeinator (y en los informes de error). Cuando Forgeinator cierra la entrada estándar, el complemento debe terminar.

- **Petición:** `{"v":1,"id":7,"method":"games","params":{…}}`
- **Respuesta buena:** `{"v":1,"id":7,"ok":true,"result":…}`
- **Respuesta con error:** `{"v":1,"id":7,"ok":false,"error":"auth","detail":"El servidor rechazó el token"}`. `detail` se enseña tal cual al usuario: escríbelo para una persona.
- **Avance** (solo durante `download`, tantas veces como quieras, idealmente una o dos por segundo): `{"v":1,"id":7,"progress":{"done":1048576,"total":734003200,"eta":95,"speed":7700000}}`.
- Las líneas que no son JSON se ignoran y quedan en el registro.

Todas las peticiones llevan en `params.config` los campos de **esa** biblioteca (también los secretos) y `root`.

| Método | `params` | `result` |
|---|---|---|
| `hello` | `{protocol: 1, forgeinator: "<versión>"}` | `{protocol: 1, name?, version?, capabilities: [...]}`. Siempre es la primera |
| `test` | `{config}` | texto corto para el usuario: «conecta · 12 sistemas». Solo si `capabilities` incluye `test`; si no, Forgeinator usa `systems` |
| `systems` | `{config}` | `[{dir, system?, name?}]`. `dir` es tu identificador; `system` el nombre de ES-DE (si falta, se deduce de `dir`). Los que no son un sistema conocido se descartan |
| `games` | `{config, dir, system}` | `[{path, name, dir?, size?}]`. `path` es tu identificador; `name` el nombre del archivo o carpeta en la biblioteca (se le quita cualquier ruta); `dir: true` si el juego es una carpeta |
| `download` | `{config, game, system, dest, is_dir}` | lo que quieras (p. ej. `{bytes}`). Escribe **solo** en `dest`: un archivo, o una carpeta si `is_dir` |
| `cancel` | — (mismo `id` que la descarga) | no se responde: deja la descarga y responde a esa descarga con `"error":"cancelado"` |

Reglas de la descarga:
- `dest` es `<carpeta de ROMs>/<sistema>/<nombre>.parte`. Al terminar bien, Forgeinator lo renombra al nombre final; si falla o se cancela, lo deja como `.incompleto` (no se borra).
- Si tras un `cancel` el complemento no responde en 5 s, Forgeinator lo cierra.
- Sin respuesta ni avance durante 300 s en una descarga (60 s en lo demás), se da por colgado y se cierra.
- Comprueba la integridad si tu servidor da sumas (sha256) y falla con un `detail` claro si no coincide.

Entorno del proceso:
- `FORGEINATOR_PLUGIN_PROTOCOL=1` y `FORGEINATOR_VERSION=<versión>`.
- No hereda las variables del Hub cuyo nombre contiene TOKEN, SECRET, PASSW, COOKIE o acaba en KEY: lo que necesites, pídelo en `fields`.

## 5. Ejemplo mínimo (Python, solo biblioteca estándar)

```python
import json, sys

def reply(mid, result=None, error=None, detail=""):
    msg = {"v": 1, "id": mid, "ok": error is None}
    msg.update({"result": result} if error is None else {"error": error, "detail": detail})
    print(json.dumps(msg, ensure_ascii=False), flush=True)

for line in sys.stdin:
    m = json.loads(line)
    mid, p = m["id"], m.get("params") or {}
    if m["method"] == "hello":
        reply(mid, {"protocol": 1, "capabilities": ["systems", "games", "download"]})
    elif m["method"] == "systems":
        reply(mid, [{"dir": "psx", "system": "psx"}])
    elif m["method"] == "games":
        reply(mid, [{"path": "demo-1", "name": "Demo (EU).chd", "size": 5}])
    elif m["method"] == "download":
        with open(p["dest"], "wb") as f:
            f.write(b"hola!")
        print(json.dumps({"v": 1, "id": mid, "progress": {"done": 5, "total": 5}}), flush=True)
        reply(mid, {"bytes": 5})
    elif m["method"] != "cancel":
        reply(mid, error="metodo", detail=f"No sé hacer {m['method']}")
```

El complemento completo de ejemplo, **«Catálogo HTTP v1»** (`plugins/catalogo-http/`), habla con cualquier servidor que implemente el protocolo de catálogo HTTP v1 (PROTOCOL.md §5): pide el catálogo página a página, baja juegos de uno o varios archivos, comprueba sha256 y atiende `cancel` mientras descarga. Sale en cada release como `forgeinator-plugin-catalogo-http-<versión>.zip`.

## 6. Probarlo a mano

```bash
cd plugins/catalogo-http
printf '%s\n' '{"v":1,"id":1,"method":"hello","params":{"protocol":1}}' \
              '{"v":1,"id":2,"method":"systems","params":{"config":{"url":"https://nas.local/forgeinator/v1","token":"…"}}}' | python3 main.py
```

Para empaquetarlo: `python3 -c "from hub import plugins; print(plugins.pack('plugins/mi-servidor', 'dist'))"` desde la carpeta de Forgeinator.

## 7. Seguridad

Un complemento es un programa que se ejecuta en tu equipo con tu usuario, como cualquier otro. Forgeinator:
- no instala nada sin enseñar antes el manifiesto y pedir confirmación;
- valida el zip (rutas, enlaces, tamaño, programa);
- le pasa solo los campos de su propia biblioteca y le quita las variables de entorno con secretos;
- guarda sus secretos aparte, con permisos 600;
- permite desactivarlo o quitarlo (a la papelera) en cualquier momento.

Lo que no hace es aislarlo del sistema: instala solo complementos de gente en la que confíes.
