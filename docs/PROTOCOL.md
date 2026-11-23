# Forgeinator · conexiones y protocolos (v1)

*English summary: Forgeinator has one background service, `forgeinatord`, that all clients (the Hub, QAM Rail, the phone link) talk to over a local UNIX socket with JSON lines. Remote libraries come from connectors: built-in ones via rclone, or plugins that speak the connector protocol over stdio. Servers with their own API can implement the HTTP catalog protocol and be reached with the "Catálogo HTTP v1" plugin. Plugins are covered in [PLUGINS.md](PLUGINS.md).*

Este documento describe **cómo se conecta cada pieza** de Forgeinator y **qué protocolo habla**. Si quieres escribir un conector, lee además [PLUGINS.md](PLUGINS.md).

## 1. Piezas

```
 Hub (interfaz)     QAM Rail (tarjeta Descargas)     Teléfono (Forgeinator Link, E4)      forgeinator-ctl (terminal)
        \                     |                               /                                 |
         └──────── socket de clientes v1: $XDG_RUNTIME_DIR/forgeinator.sock (JSON por líneas) ───┘
                                          │
                         forgeinatord  (hub/service.py · sin ventana · cola de descargas)
                                          │
          ┌───────────────────────────────┼──────────────────────────────────┐
   conectores integrados            complementos (plugins)              directo
   rclone: WebDAV, SMB, SFTP,       protocolo de conectores v1          http/https y releases de GitHub
   FTP, remotos de rclone, local    por stdio (PLUGINS.md)              (hub/downloads.py)
                                          │
                                 p. ej. «Catálogo HTTP v1» → cualquier servidor que hable el
                                 protocolo de catálogo HTTP v1 (sección 5)
```

| Conexión | Transporte | Formato | Quién la usa | Sección |
|---|---|---|---|---|
| Clientes ↔ `forgeinatord` | socket UNIX local, permisos 600 | JSON, un mensaje por línea | Hub, QAM Rail, teléfono, terminal | 2 |
| `forgeinatord` ↔ conector integrado | proceso `rclone` | cadenas de conexión de rclone + `--use-json-log` | servicio | 3 |
| `forgeinatord` ↔ complemento | entrada y salida estándar del proceso del complemento | JSON, un mensaje por línea | servicio y Hub | 4 y PLUGINS.md |
| Complemento «Catálogo HTTP v1» ↔ servidor | HTTP o HTTPS | JSON, `Authorization: Bearer` | servidores con API | 5 |
| Hub ↔ QAM Rail | socket UNIX `$XDG_RUNTIME_DIR/qam-rail.sock` | JSON por líneas | lanzar juegos por su acceso de Steam | 6 |
| QAM Rail → Hub | programa `bin/forgeinator-ctl` | una línea JSON | estado, canal, avisos | 7 |

Nada de esto escucha en la red. Lo único que sale del equipo son las conexiones que hace un conector hacia tu servidor.

## 2. Socket de clientes v1

- **Dónde:** `$XDG_RUNTIME_DIR/forgeinator.sock`. La variable `FORGEINATOR_SOCK` lo cambia. Permisos 600: solo tu usuario.
- **Arranque:** el Hub arranca `forgeinatord` al encolar la primera descarga, con `systemd-run --user` si existe o en su propia sesión si no. Sobrevive al cierre del Hub y se apaga solo tras 10 minutos sin trabajo ni clientes. Para arrancarlo a mano: `bin/forgeinatord`; para ver qué hace: `bin/forgeinatord --estado`.
- **Petición:** `{"v":1,"id":<lo que quieras>,"method":"…","params":{…}}` y un salto de línea. En la misma conexión puedes mandar varias seguidas.
- **Respuesta:**
  - bien: `{"v":1,"id":<el mismo>,"ok":true,"result":…}`;
  - mal: `{"v":1,"id":…,"ok":false,"error":"<código>","detail":"<texto en claro>"}`.
- **Códigos de error:**

| Código | Significa |
|---|---|
| `metodo` | método desconocido |
| `no_existe` | id, fuente o complemento desconocidos |
| `invalido` | JSON o parámetros incorrectos |
| `remota` | falló la fuente o rclone (el texto ya explica el motivo) |
| `complemento` | falló un complemento: no arranca, no responde o devolvió un error |

### Métodos

| Método | Parámetros | Resultado |
|---|---|---|
| `ping` | — | `{version, channel, pid, protocol: 1, methods: […]}` |
| `sources.list` | — | `[{id, name, kind, fields, root, added}]`, sin secretos |
| `sources.test` | `{source}` | texto, p. ej. «12 sistemas: psx, ps2…» |
| `browse` | `{source}` | sistemas: `[{dir, system, name}]` |
| `browse` | `{source, path: <dir del sistema>, system}` | juegos: `[{path, name, dir, size}]` |
| `downloads.add` | `{source, game: {path, name, dir, size}, system}` | `{id}` (si ya estaba en la cola, el mismo id) |
| `downloads.list` | — | `[{id, source, path, name, system, state, done, total, eta, speed, error, dest?, t}]` |
| `downloads.pause` · `downloads.resume` · `downloads.cancel` | `{id}` | `true` |
| `downloads.clear` | — | `true`; quita las terminadas, fallidas y canceladas |
| `events.subscribe` | — | `{subscribed: true}`; después llegan eventos por la misma conexión |
| `plugins.list` | — | `[{id, name, version, type, protocol, fields, permissions, description, author, homepage, enabled, dir, error?}]` |
| `plugins.inspect` | `{path: <zip>}` | el manifiesto del zip más `installed_version` y `action` (`instalar`, `actualizar` o `reinstalar`), sin instalar nada |
| `plugins.install` | `{path: <zip>}` | el complemento instalado |
| `plugins.enable` · `plugins.disable` | `{id}` | `true` |
| `plugins.remove` | `{id}` | `{moved_to}`: no se borra, va a la papelera de complementos |
| `shutdown` | — | `true` |

- **Estados de una descarga:** `queued` → `active` → `done`, `error` o `cancelled`; además `paused`.
- **Eventos:** `{"event": "download.added" | "download.state" | "download.progress" | "download.done" | "download.error", "download": {…}}`. De `download.progress` llega como mucho uno por segundo y por descarga.
- **Instalar complementos desde un cliente:** muestra antes al usuario lo que devuelve `plugins.inspect` (nombre, versión, autor y permisos) y pide confirmación; luego llama a `plugins.install`. Para quitar, pide confirmación también.

Ejemplo desde la terminal:
```bash
printf '{"v":1,"id":1,"method":"downloads.list"}\n' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/forgeinator.sock
```

## 3. Conectores integrados (rclone)

- **Tipos:** `webdav` (`url`, `user`, `pass`) · `smb` (`host`, `user`, `pass`, `share`) · `sftp` y `ftp` (`host`, `user`, `pass`, `port`) · `rclone` (`remote` de tu `rclone.conf`: Google Drive, OneDrive y 40 más) · `local` (`path`, también USB, NFS o lo que tengas montado).
- **Estructura que se espera en la fuente:** como ES-DE, `<root>/<sistema>/<juego>`; `root` es `roms` por defecto. Un juego puede ser un archivo o una carpeta (varios discos). Los nombres de sistema y sus alias son los de `hub/esde.py`.
- **Cómo se conecta:** con cadenas de conexión de rclone (`:webdav,url='…',user='…',pass='…':ruta`), sin tocar tu `rclone.conf`.
- **Explorar:** `rclone lsjson`. **Bajar:** `rclone copyto` o `rclone copy` con `--use-json-log --stats 1s`, de donde sale el avance.
- **Dónde se guarda:** las fuentes en `~/.local/share/forgeinator/remotes.json`, sin secretos; las contraseñas, oscurecidas con `rclone obscure`, en `~/.config/forgeinator/remotes-secrets.json` (600).
- **Necesita:** el programa `rclone` (`brew install rclone` en Bazzite). Sin rclone solo funcionan las carpetas locales y los complementos.

## 4. Complementos (conectores instalables)

Un complemento es un programa con un manifiesto `forgeinator-plugin.json`. Forgeinator lo arranca cuando lo necesita y habla con él por su entrada y salida estándar con el **protocolo de conectores v1**: `hello`, `test`, `systems`, `games`, `download` y `cancel`, más mensajes de avance. La especificación completa, el formato del zip y la zona de instalación están en [PLUGINS.md](PLUGINS.md).

Las fuentes de un complemento se guardan como las demás, con `kind: "plugin"` y `fields.plugin = <id>`. Los campos que el manifiesto marca como secretos van al archivo de secretos (600) y solo se le pasan a ese complemento.

## 5. Protocolo de catálogo HTTP v1 (para servidores con API)

Si tienes un servidor con su propia API, puedes hacer que hable este protocolo y usar el complemento incluido **«Catálogo HTTP v1»**, sin escribir ningún conector. Si no puedes cambiar el servidor, escribe un complemento que traduzca su API (PLUGINS.md).

- **Base:** la dirección que pongas al añadir la biblioteca, p. ej. `https://nas.local:8080/forgeinator/v1`.
- **Autenticación:** `Authorization: Bearer <token>` si el servidor la pide. 401 o 403 = token rechazado.
- **Errores:** HTTP 4xx o 5xx con `{"error": "<código>", "detail": "<texto>"}`.

| Petición | Respuesta |
|---|---|
| `GET info` | `{name, version, protocol: 1, capabilities?}` |
| `GET catalog` · `GET catalog?since=<cursor>` | `{items: [{id, title, system, file?, files?, size?, region?, updated?}], next: <cursor> \| null}` |
| `GET items/{id}/files` | `[{name, size, sha256?, url}]` |
| `GET <url>` de un archivo | los bytes; conviene que admita `Range` |

- `system` es el nombre de ES-DE (`psx`, `ps2`, `n64`…) o un alias que entienda `hub/esde.py`.
- `file` es el nombre del archivo cuando el juego es uno solo (sale así en tu carpeta de ROMs); `files` > 1 indica que el juego es una carpeta con varios archivos.
- `url` puede ser absoluta o relativa a la base.
- Si viene `sha256`, el complemento comprueba cada archivo y, si no coincide, la descarga falla y lo bajado queda como `.incompleto`.
- `catalog` se pide página a página hasta que `next` sea `null`.
- Reservado para la v1.1 (aún no se usa): `GET search?q=…&system=…`.

## 6. Hub → QAM Rail (lanzar por el acceso de Steam)

Para que los juegos aparezcan en la barra lateral de Steam y tengan su TDP, el Hub pide al QAM que los abra por su acceso de Steam: socket `$XDG_RUNTIME_DIR/qam-rail.sock` (`QAM_RAIL_SOCK` lo cambia), JSON por líneas, operación `steam.run_shortcut`. El contrato completo vive en el proyecto (`forgeinator-qam-atajos`). Si el QAM no responde, el Hub lanza el juego él mismo.

## 7. QAM Rail → Hub (`forgeinator-ctl`)

Programa sin interfaz, responde en menos de 1 s y no necesita pygame:

| Orden | Qué hace |
|---|---|
| `--qam-status` | una línea JSON: versión, canal de esta copia, canal activo, si está abierta, avisos |
| `--canal [estado\|estable\|dev]` | ver o elegir el canal activo |
| `--where` | carpetas de esta copia |
| `--resolve-active` | carpeta de la copia que debe abrirse |
| `--plugins [lista\|ver ZIP\|instalar ZIP\|activar ID\|desactivar ID\|quitar ID]` | zona de complementos |

## 8. Seguridad

- Los sockets son locales y de tu usuario (600); nada escucha en la red.
- Los secretos no viajan por el socket de clientes: `sources.list` y `plugins.list` nunca los incluyen.
- Un complemento solo recibe los campos de su propia fuente. No hereda las variables de entorno con TOKEN, SECRET, PASS, COOKIE o KEY del Hub.
- Los informes de error tapan los secretos antes de la vista previa (Ajustes › Mantenimiento › Informe de error).
- Versionado: `v` en cada mensaje. Un cambio incompatible sube el número de protocolo; los campos nuevos y opcionales no lo cambian, y los clientes deben ignorar lo que no conozcan.
