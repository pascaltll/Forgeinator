# Forgeinator 3000 — historial de cambios

> Forgeinator se llamó **Recomp Hub** hasta la v3.10 y **Craftinador** en la v3.11. Este archivo conserva la documentación de uso original y el historial completo de versiones (en español). La guía actual está en [README.md](README.md) / [README.es.md](README.es.md).

## Documentación original (Recomp Hub)

Catálogo de ports/recomps + gestor de descargas + instalador que registra cada juego en el **launcher unificado**
(`~/Games/launcher`). Pensado para Steam Big Picture / Gamescope: **táctil y mando**, sin teclado ni ratón.

## Qué hace
1. **Catálogo** de juegos (cada uno apunta a un repositorio de GitHub). Trae una lista base y puedes **importar listas** en formato `apps.json`
   (el de GithubLauncher / Quiver Launcher) o añadir repos sueltos.
2. **Detalle**: última release, builds disponibles (elige el de Linux x86_64 por defecto), qué archivo de juego pide el port.
3. **Descargas** con gestor propio (estilo Motrix): cola, varias conexiones por archivo, pausa/reanudar (también tras reiniciar), reintentos y verificación SHA-256.
4. **Instalación automática**: extrae, detecta el ejecutable y escribe `~/Games/launcher/games/<id>.toml` (si ya existe escribe `<id>.toml.new`, nunca pisa el tuyo).
5. **Tu archivo del juego**: los ports no incluyen el juego. Hub **no lo descarga ni lo busca**: te muestra qué pide el port (serial, formato, SHA-1), tú lo consigues de tu copia,
   y Hub lo **reconoce** (por hash o serial) desde el selector de archivos o vigilando tu carpeta de descargas, lo enlaza en la biblioteca y lo coloca donde el port lo espera.

## Instalar
```
cd ~/Games && bash install-hub.sh          # reinstalar código: FORCE=1 bash install-hub.sh
~/Games/recomp-hub/bin/hub                 # abre la interfaz
```
Necesita `pygame-ce` (el mismo que el launcher): `pip install --user --break-system-packages pygame-ce`.
Para Steam: añade `~/Games/recomp-hub/bin/hub` como juego no-Steam.

## Controles
| | Mando | Táctil |
|---|---|---|
| Moverse | cruceta / stick | tocar |
| Abrir / pulsar | A | tap |
| Atrás | B | botón ‹ ATRÁS |
| Acción 2 / 3 | X / Y (ver barra inferior) | botones |
| Pestañas | LB / RB | pestañas arriba |
| Desplazar listas | cruceta | arrastrar con el dedo (con inercia) |

Teclado en pantalla propio (táctil + mando): X borra, Y mayúsculas. Selector de archivos propio: X sube de carpeta.

## Build de Linux, compilar y añadir repos a mano
- Cada tarjeta muestra tras consultar GitHub: **BUILD LINUX**, **SOLO WINDOWS · COMPILAR**, **SIN BUILD · COMPILAR** o **SIN REPOSITORIO**
  (la consulta se hace al abrir el juego o con X "Comprobar actualizaciones"; sin token de GitHub hay límite de ~60 consultas/hora, el resultado se guarda 6 h).
  Filtro "Build Linux" en la fila de chips.
- **Compilar desde el código**: en el detalle, COMPILAR AQUÍ clona el repo en la carpeta del juego y compila dentro del distrobox (por defecto `fedora`;
  cambia con CONTENEDOR, vacío = en el sistema). Detecta CMake / Meson / Cargo / Makefile o usa tu comando (EDITAR COMANDO; `$REPO` y `$JOBS`).
  Al terminar registra `games/<id>.toml` tipo `git-build` para que el launcher lo siga actualizando. Progreso y registro en la pestaña DESCARGAS.
  Nunca toca una carpeta existente que no sea un repo git; si ya es un repo solo hace `fetch` + `merge --ff-only`.
- **Añadir repositorios a mano**: en el detalle, BUSCAR REPO EN GITHUB abre `github.com/search?q=<nombre>+recomp` y BUSCAR EN GITHUB (YO MISMO) abre la búsqueda de GitHub vacía para que escribas tú; antes abría una búsqueda
  «<nombre> recomp github»; luego CAMBIAR / DEFINIR REPOSITORIO (con teclado en pantalla y botón PEGAR). En AJUSTES, AÑADIR JUEGO hace todo el flujo.
  Dentro de Steam/Big Picture se abre con el navegador de Steam (`steam://openurl/…`); la dirección siempre aparece en pantalla.

## Buscar un juego y crear su tarjeta (pestaña BUSCAR)
1. Escribe el nombre del juego (teclado en pantalla). Hub busca en GitHub «nombre + recomp» (cambia el sufijo: recomp / decomp / port / nativo / ninguno)
   y lista los repositorios con estrellas, lenguaje, fecha y avisos (ARCHIVADO, FORK, YA EN TU CATÁLOGO). Si prefieres ver GitHub tú mismo,
   ABRIR EN EL NAVEGADOR (o BUSCAR EN GITHUB (YO MISMO)); en Big Picture usa el navegador de Steam.
2. Si abres un repo en el navegador y **copias su dirección**, Hub lo detecta solo (banner «Repositorio copiado → USAR ESTE») o usa PEGAR URL / OWNER/REPO.
3. La pantalla del repo muestra descripción, licencia, temas, última release, si hay build de Linux y un resumen limpio del README.
   **ESTE · CREAR TARJETA** saca esa info y crea la tarjeta (nombre = lo que buscaste; plataforma deducida de los temas; ambos editables).
4. Antes de crear comprueba duplicados: mismo repo en tu catálogo o en el launcher («ABRIR ESA TARJETA» o «AÑADIR COMO VARIANTE», p. ej. otra ISO/mod
   del mismo repo) y nombres parecidos. Las tarjetas creadas viven en `data/catalog.local.json`.

## Sesión de GitHub (límites más altos)
Sin sesión: ~60 consultas/h y ~10 búsquedas/min. AJUSTES → GITHUB:
- **PEGAR TOKEN DE ACCESO**: un token personal de GitHub (sin permisos especiales basta para repos públicos). Se valida antes de guardarlo.
- **INICIAR SESIÓN (código en pantalla)**: flujo de dispositivo; muestra un código que escribes en github.com/login/device desde el móvil. Necesita el
  *Client ID* de una OAuth App tuya con «Device Flow» activado (github.com/settings/developers); Hub te lo pide una vez.
- El token se guarda en `data/credentials.json` con permisos 600 (solo tu usuario, **sin cifrar**) y nunca se escribe en los logs. CERRAR SESIÓN borra ese archivo.
  Si existe la variable `GITHUB_TOKEN`, tiene prioridad.

## Terminal (por SSH)
```
bin/hub --list                     # catálogo
bin/hub --import URL_o_archivo     # importa una lista apps.json
bin/hub --add owner/repo           # añade un repo
bin/hub --latest ID                # última release y asset elegido
bin/hub --fetch ID                 # descarga + instala sin interfaz
```

## Formato del catálogo
`catalog/seed.json` (incluido), `data/imports/*.json` (importadas), `data/catalog.local.json` (tuyas). Lo posterior pisa a lo anterior.
Campos: `id, name, repo, platform, folder, notes` y opcional `requires`:
```json
"requires": {"formats": [".bin", ".cue"], "serials": ["SCUS-94426"], "sha1": ["..."], "region": "USA",
             "note": "texto libre", "place": "assets/ctr-u.bin"}
```
`place` = ruta (dentro de la carpeta del port) donde enlazar tu archivo una vez reconocido. Sin `sha1`/`serials`, el reconocimiento queda en "no verificable" y te pide confirmar.
Las claves de las listas importadas se aceptan en varias variantes (`Name/name`, `Repo/Repository/GitHubRepo`, `FolderName/folder`…).

## Datos y seguridad
- Todo lo tuyo vive en `data/` (ajustes, catálogo local, descargas, enlaces): la reinstalación no lo toca.
- Nunca borra nada tuyo: cancelar una descarga elimina solo su `.part`; los archivos descargados se conservan.
- Extracción protegida contra rutas peligrosas (zip-slip). SHA-256 se verifica si GitHub publica el digest del asset.
- GitHub sin token permite ~60 consultas/hora; pon `GITHUB_TOKEN=...` en `data/.env` (sin comillas) para más.
- Ajustes avanzados en `data/settings.json` (`downloads_dir`, `library_dir`, `watch_dirs`, `max_active`, `connections`).

## Estructura
```
bin/hub  main.py
hub/config.py catalog.py github.py downloads.py install.py library.py gamepad.py ui.py
catalog/seed.json
```


## Portar a Linux un repo solo-Windows (con IA)

En el detalle, panel **PORTAR A LINUX CON IA** (se resalta en tarjetas «SOLO WINDOWS» / «SIN BUILD»):

1. **INFORME DE PORT** — clona en `data/port/<id>/repo` (copia aparte; nunca la carpeta instalada), detecta APIs solo-Windows
   (`windows.h`, `_WIN32`, `WinMain`, DirectX, XInput, MSVC, rutas con `\`…), lee el distrobox elegido (compiladores, SDL…) y escribe
   `PORTING_BRIEF.md` y `PROMPT_CHAT.txt`. No necesita API.
2. **COPIAR PROMPT PARA CLAUDE** — copia el prompt (wl-copy/xclip/xsel) para pegarlo en tu chat de Claude (plan Pro).
3. **CLAUDE CODE LOCAL** — ejecuta `claude -p` en la copia de trabajo: rama `linux-port`, edita ahí, compila solo vía
   `distrobox enter <contenedor> -- …`, y si obtiene un ejecutable lo registra en el launcher (sin actualizaciones automáticas).
   Se desactivan `.claude/` y `.mcp.json` del repo ajeno. Requiere `claude` instalado y login con tu suscripción (`claude` → `/login`).
   Se ignora `ANTHROPIC_API_KEY` para no cobrar por API sin querer; `"port_use_api": true` en `data/settings.json` lo permite.
   El uso cuenta contra los límites de tu plan (compartidos con claude.ai). Verifica siempre el resultado: es un intento, no una garantía.

## Tu biblioteca existente (ROMs/ISOs) — cruce automático

En AJUSTES → **CARPETA DE ROMS** (o en el detalle) indica la raíz, p. ej. `~/Nextcloud/Emulation/roms`; se autodetecta si existe.
Cada subcarpeta es una plataforma (`psx`, `n64`, `gc`… con alias). Hub **solo lee** tus archivos (índice en `data/romindex.json`).
- **LEER DATOS DEL README**: extrae del README del repo los serial, SHA-1, CRC32 y formatos que menciona y los guarda como `requires` de esa tarjeta.
- **BUSCAR EN MI BIBLIOTECA**: busca en la carpeta de la plataforma. Coincidencia **fuerte** (serial/SHA-1/CRC32; hashes en caché `data/romhash.json`) → se enlaza sola.
  Coincidencia **débil** (solo nombre parecido) → te pide confirmar. Nada se mueve ni se copia (enlace simbólico).
- BUSCAR/DETALLE: botones BUSCAR EN GITHUB, GITHUB (YO MISMO), BUSCAR EN GOOGLE.

## Pestaña BIBLIOTECA (estándar ES-DE)

Pestaña principal junto a JUEGOS/BUSCAR/DESCARGAS/AJUSTES. Lee tu colección (`~/Nextcloud/Emulation/roms/<plataforma>/…`, se autodetecta;
cámbiala con CARPETA DE ROMS, también en AJUSTES) y muestra un renglón por juego (ignora `.cue/.m3u` duplicados).
- **CON PORT**: coincide por nombre+plataforma con una tarjeta de tu catálogo → A abre su detalle (ahí BUSCAR EN MI BIBLIOTECA enlaza el archivo exacto por serial/hash).
- **SIN PORT CONOCIDO**: A abre BUSCAR con ese nombre y consulta GitHub; X lo abre en el navegador.
- Filtros por plataforma y CON/SIN PORT, REINDEXAR (Y). Solo lee: nunca mueve ni borra tus ROMs.

## Seguridad, credenciales y registro

- **Credenciales**: el token de GitHub se guarda en `~/.config/recomp-hub/credentials.json` (carpeta 700, archivo 600), **fuera del proyecto**, así no acaba en git.
  No está cifrado (solo protegido por permisos). Alternativas: variable `GITHUB_TOKEN` o `data/.env` (ignorado por git). Una versión antigua en `data/credentials.json` se migra sola.
  El proyecto trae `.gitignore` (`data/`, `.env`, `*.log`, `credentials.json`). Usa un token con los mínimos permisos (basta uno sin scopes: solo sube el límite).
- **AJUSTES → GITHUB: COMPROBAR SESIÓN Y LÍMITES** muestra si el token se usa y cuántas consultas quedan (general y búsquedas: 30/min con sesión, 10/min sin ella).
- **AJUSTES → VER REGISTRO** abre `data/hub.log`: errores de GitHub (`[gh]`), coincidencias de la biblioteca (`[match]`), asociaciones de instalados por repo (`[instalado]`) y eventos del mando (`[mando]`).
- Coincidencia de nombres estricta: todas las palabras de uno deben estar en el otro (Carbon ≠ Most Wanted, Tenkaichi 2 ≠ 3).
- Mando: el stick necesita empujarse >75 % para navegar; si queda fijo 3 s se considera deriva y se ignora. Se puede desactivar el stick en AJUSTES (la cruceta siempre funciona).

## Encontré el repo yo mismo (GitHub/Google): cómo lo agrego

1. Abre el repo en el navegador y **copia su URL** (o `owner/repo`). Hub lo detecta en **cualquier pestaña** y muestra un botón verde flotante:
   «REPO COPIADO: owner/repo — ANALIZAR Y CREAR TARJETA ›» (× para ignorarlo). También sirve PEGAR URL / REPO en BUSCAR.
2. Se abre la vista del repo con descripción, releases (¿build Linux?), plataforma (por temas) y **lo que el README pide** (región, versión, formatos, serial, hashes).
   Si ya tienes una tarjeta parecida avisa (duplicados). Pulsa **ESTE** → se crea la tarjeta **ya con esos requisitos**.

## Ficha del archivo requerido (LEER DATOS DEL README)

En el detalle, panel «ARCHIVO DEL JUEGO» → **LEER DATOS DEL README** descarga el README y abre la **ficha**: región, versión/disco, formatos, serial,
SHA-1/CRC32/MD5 y las frases clave del README. Si el README no es claro: abre **la página del proyecto** (ABRIR PROYECTO), **selecciona y copia** el texto
(Ctrl+C) y pulsa **PEGAR TEXTO COPIADO**: Hub extrae los datos del texto y los suma a la tarjeta (y guarda la frase). También puedes editar a mano
REGIÓN, VERSIÓN/DISCO, FORMATOS y NOTA. X del mando = borrar la ficha. Con SHA-1/CRC32/MD5/serial, BUSCAR EN MI BIBLIOTECA verifica tu archivo (región y versión son informativas).

## Dónde comprar el juego

Botón **DÓNDE COMPRAR** (panel «ARCHIVO DEL JUEGO» y dentro de la ficha). Elige **región** (NTSC-U/USA, PAL/Europa, NTSC-J/Japón; se preselecciona con la de la ficha) y
**formato** (físico/digital) y abre GOOGLE, GOOGLE SHOPPING o EBAY con «nombre + plataforma + región + comprar». Tu última elección se recuerda.
El aviso «Repo copiado» ahora también sale como mensaje al detectarlo; en `hub.log` quedan líneas `[clip]` para diagnosticar el portapapeles.

## Versiones digitales, comprimidos y otros formatos

Si compraste el juego digital (o lo tienes comprimido) y **ya tienes el archivo en tu equipo**, Hub lo prepara solo al usarlo (ELEGIR ARCHIVO, USAR DETECTADO o BUSCAR EN MI BIBLIOTECA):
- **.zip**: mira dentro sin extraer (CRC32 del índice y serial) y extrae solo lo necesario (iso/bin/cue) a `~/Games/library/converted/`. **.7z/.rar**: necesitan `7z`.
- **.chd** → bin/cue o iso con `chdman` (paquete mame-tools); **.rvz/.wia/.gcz** → iso con `dolphin-tool`. Si falta la herramienta, te dice cuál instalar.
- Comprueba antes que hay espacio libre. Después compara por serial/SHA-1/CRC32/MD5 sobre el archivo ya preparado.
- **No** descifra nada: `.pkg` de PSN, `.nsp/.xci` de eShop, `.wad`, EBOOT `.pbp` o `.cso` se reconocen pero no se convierten (usa tu propio volcado en formato estándar).
- Ojo: una versión digital puede no ser idéntica byte a byte a la del disco (otra región, parches, otro empaquetado). Si el serial coincide pero el hash no, suele ser la misma versión; revisa en la ficha qué región/versión pide el repo.

## Guardar el juego en tu biblioteca estilo ES-DE

Al reconocer tu archivo (por serial/hash) Hub puede guardarlo en `<tu carpeta de ROMs>/<sistema>/` (p. ej. `~/Nextcloud/Emulation/roms/psx/`):
- Los nombres de sistema salen de la **lista oficial de ES-DE** (`catalog/esde_systems.json`, 172 sistemas, generada de su `es_systems.xml`, licencia MIT):
  «PlayStation» → `psx`, «PlayStation 2» → `ps2`, «GameCube» → `gc`, «Nintendo 64» → `n64`… Si la plataforma no existe en ES-DE (p. ej. PS4) no pregunta y solo enlaza.
- Pregunta: **COPIAR** (deja el original), **MOVER** (lo borra tras copiar) o **SOLO ENLAZAR**. AJUSTES → «AL RECONOCER UN JUEGO» fija la respuesta (preguntar/copiar/mover/enlazar).
- Un `.cue` viaja con sus `.bin` (y al revés). Si descargaste un `.zip`/`.chd` y ES-DE lo acepta para ese sistema se guarda tal cual; el port usa el archivo ya extraído/convertido.
- Nunca pisa un archivo existente; comprueba el espacio libre; si ya está dentro de tu biblioteca no pregunta. Después la pestaña BIBLIOTECA se reindexa.
- Ojo: si esa carpeta es de Nextcloud, el archivo se sincronizará/subirá a tu servidor.

## Descargas del navegador, pop-ups y volver a Hub

Hub **no puede ver ni controlar el interior** del navegador de Steam (botones atrás, pop-ups, cuándo pulsas «descargar»). Lo que sí hace es vigilar desde fuera:
- **Detección de descargas**: vigila `watch_dirs` (por defecto `~/Downloads`, `~/Descargas`). Al aparecer un `.crdownload/.part/.tmp` nuevo muestra «⬇ DESCARGANDO: nombre · tamaño · velocidad» (el tamaño total lo sabe solo el navegador),
  también en DESCARGAS → «NAVEGADOR», y avisa al terminar («DESCARGA TERMINADA ›»). Si estás en el detalle de un juego, el archivo queda como «detectado» (USAR DETECTADO).
- **Volver a Hub** al empezar/terminar una descarga (AJUSTES → «VOLVER A HUB AL DETECTAR UNA DESCARGA»): intenta enfocar la ventana (pygame y `xdotool` si existe). `steam://rungameid` se probó y Steam responde «game is already running», así que está desactivado (`steam_resume`: false).
  Qué pasos funcionan depende de tu Steam/Gamescope: cada intento queda en `hub.log` (`[volver]`).
- **Navegador propio** (AJUSTES → NAVEGADOR → COMANDO PROPIO, p. ej. `firefox {url}`): se abre como ventana aparte, usa su bloqueador de pop-ups, se cierra con un solo «atrás/cerrar» y **Hub vuelve solo al cerrarlo**.
  Es la forma más fiable de evitar el «atrás muchas veces» del navegador de Steam.
- Descargas a otra carpeta: añádela a `watch_dirs` en `data/settings.json`.

**Falsos positivos**: solo cuentan como descarga los archivos `.crdownload`, `.part`, `.download` y `.opdownload` (parciales de navegador) que aparecen nuevos en `watch_dirs`. Se ignoran archivos ocultos
(sincronizadores), `.tmp` ajenos y archivos que otros programas escriben directo (activable con `"dl_detect_direct": true`). El aviso muestra el archivo y su carpeta, tiene botón **IGNORAR**,
y `hub.log` guarda la ruta completa (`[descarga] inicio: /ruta/archivo`).

## Carpeta de descargas del proyecto y descarga directa por URL
- Todo lo que descarga Hub va a `data/downloads/` (dentro del proyecto; `data/` no se sube a git). Las instalaciones antiguas que usaban `~/Games/hub-downloads` se migran solas a esta carpeta.
- `data/downloads/navegador/` es la carpeta para lo que bajes con un navegador: Hub la vigila (además de `~/Downloads`). El navegador de Steam **no permite elegir carpeta**; si quieres que guarde ahí, usa un navegador propio (AJUSTES → NAVEGADOR → COMANDO PROPIO, p. ej. `firefox {url}`) y fija su carpeta de descargas a `data/downloads/navegador`.
- **Descarga directa con Hub (no depende del navegador):** copia el enlace de un release de GitHub (`…/releases/download/…`) o de cualquier archivo (`.zip .7z .iso .chd…`) y aparece el botón verde **DESCARGAR CON HUB**. También puedes pegarlo en DESCARGAS → **AÑADIR DESCARGA POR URL**. Si el enlace es de un repo del catálogo, se instala solo al terminar.
- Cada descarga queda en `data/hub.log` con la etiqueta `[dl]` (añadida, terminada o el error exacto, p. ej. `El servidor respondió 404`).

## Si Hub se cierra solo (diagnóstico)
- Hub ignora SIGHUP/SIGPIPE: cerrar o dormirse la sesión SSH ya no lo mata. Antes, al caducar la sesión por inactividad, el sistema podía enviarle SIGHUP y cerrarlo sin dejar rastro.
- `data/hub.log` anota ahora el motivo: `[salida] señal …`, `[salida] evento QUIT…` (con los segundos de inactividad), `[ventana] …` (foco/minimizado), `[error]` con el traceback si falla un fotograma (Hub sigue en marcha) y, al terminar, `Hub terminó con código N` (137 = SIGKILL/falta de RAM, 143 = SIGTERM).
- Cada 2 min escribe `[vivo]` con RAM, hilos, descriptores y fps: si la última línea antes de morir muestra RAM creciente, hay una fuga.

## Teclado de Steam y navegadores predefinidos
- **Teclado:** AJUSTES → TECLADO (AUTOMÁTICO / STEAM / DE HUB). En AUTOMÁTICO, dentro de Big Picture/Game Mode Hub usa el teclado de Steam: al abrir un campo de texto muestra la caja arriba y pide el teclado con `steam://open/keyboard`; lo que escribes llega a Hub como texto (Intro acepta). Si el teclado no aparece, el botón TECLADO DE STEAM lo reintenta y TECLADO DE HUB cambia al teclado propio solo para ese campo. Fuera de Steam se sigue usando el teclado de Hub.
- **Navegador:** AJUSTES → NAVEGADOR ofrece **FIREFOX** y **MICROSOFT EDGE**; Hub detecta si están instalados (Flatpak `org.mozilla.firefox` / `com.microsoft.Edge`, o binario nativo) y guarda el comando correcto. Si no están, dice cómo instalarlos. Al cerrar el navegador Hub vuelve solo.
- Pendiente de verificar en tu aparato: que `steam://open/keyboard` abra el teclado desde un juego no-Steam en Game Mode (el registro `[teclado]` en data/hub.log dice qué comando se lanzó).

## Si SDL pierde la ventana (autorrecuperación) y ajustes del navegador
- Si el servidor gráfico suelta la ventana (`video system not initialized`), Hub ya no muere: anota `[video] PERDIDO` con los procesos y sockets gráficos que quedan vivos, e intenta reabrir la ventana durante ~40 s (`[video] ventana reabierta`). Conserva todo el estado.
- Edge se lanza en pantalla completa (evita el 4:3), con eventos táctiles y zoom ajustable (AJUSTES → ZOOM DEL NAVEGADOR EDGE). Firefox se lanza con XInput2 táctil; su zoom se fija con Ctrl +/− y lo recuerda por sitio.
- Teclado de Steam dentro de otro navegador: en Game Mode suele abrirse con el botón Steam + X (no lo controla Hub).

## Navegador de Hub (recomendado en Big Picture/Gamescope)
Navegador propio (Qt WebEngine = Chromium) hecho para la consola: **pantalla completa, botones grandes, arrastrar para desplazarse (como un móvil), zoom +/−, teclado de Steam al tocar la barra o un campo de texto, bloqueo de pop-ups y descargas nativas** a `data/downloads/navegador/` (Hub las detecta, las cruza con tu biblioteca y las guarda como siempre). Mantiene tu sesión (cookies) en `data/browser/`.
- Instalar: AJUSTES → NAVEGADOR → **NAVEGADOR DE HUB** (o AJUSTES → NAVEGADOR DE HUB → INSTALAR). Descarga PyQt6 + Qt WebEngine (~150 MB; ~550 MB en `data/browser-venv`) con el progreso y registro en DESCARGAS. Manualmente: `bin/hub-browser --setup`.
- Botones: ◀ ▶ ⟳ · barra de dirección (también acepta búsquedas) · ⌨ teclado de Steam · − + zoom · ✋/T (arrastrar = desplazar / seleccionar texto) · **ANALIZAR EN HUB** (en una página de repo de GitHub: cierra el navegador y Hub abre la tarjeta del repo) · **VOLVER A HUB**.
- Mensajes al registro (`data/hub.log`): `[navegador] …`, `[browser] …` (teclado, descargas, errores).
- Sin verificar en hardware real: táctil/arrastre en Gamescope y que `steam://open/keyboard` abra el teclado de Steam.

## Archivos recibidos por el navegador (descomprimir, mover, enlazar, guardar)
En DESCARGAS aparece **ARCHIVOS RECIBIDOS POR TU NAVEGADOR**: lo que bajaste (zip/7z/rar/iso/chd/roms…) en los últimos 14 días, en `data/downloads/navegador/`, tus carpetas vigiladas (`~/Downloads`…) y lo ya descomprimido. Al tocar un archivo:
- **ENLAZAR CON UN JUEGO DEL CATÁLOGO…**: sugiere los juegos cuyo nombre coincide (p. ej. «Bomberman 64 (USA).zip» → Bomberman 64) y lanza el reconocimiento habitual (hash/serial, zip/7z/CHD/RVZ…) y el guardado en tu biblioteca.
- **GUARDAR EN MI BIBLIOTECA (plataforma)…**: adivina la plataforma por lo que hay dentro del zip (`.z64` → n64) y copia/mueve a `roms/<plataforma>/` (ES-DE), sin pisar nada.
- **DESCOMPRIMIR**: a `data/downloads/extraido/<nombre>/` (nunca sobre una carpeta existente).
- **MOVER A LA CARPETA DE DESCARGAS DEL PROYECTO**: trae a `data/downloads/navegador/` lo que Edge/Firefox dejó en `~/Downloads` (esos navegadores no se pueden obligar a usar otra carpeta; el navegador de Hub sí lo hace solo).
- Navegador de Hub: al abrirlo muestra «Abriendo el navegador de Hub…» hasta que la ventana está lista; el registro anota `[browser] +Ns …` con el tiempo de cada fase de arranque y `[navegador] navegador de Hub listo en Ns`. Si la aceleración gráfica da problemas, prueba `HUB_BROWSER_FLAGS=--disable-gpu`.

## Si el navegador de Hub se cuelga o tarda (compatibilidad gráfica)
- Chromium puede colgarse con la aceleración gráfica en Gamescope (el registro muestra «terminó (código -5)» = SIGTRAP o «-11» = SIGSEGV). Hub lo detecta: si se cuelga en el primer minuto, **reintenta solo** subiendo de nivel — AUTO (con GPU) → SIN GPU → SIN GPU Y SIN SANDBOX — y recuerda el nivel. También se cambia a mano en AJUSTES → NAVEGADOR DE HUB · COMPATIBILIDAD GRÁFICA.
- Ver el detalle de un cuelgue: `grep -n -A25 "hub -> " data/hub.log | tail -60` (los mensajes de Chromium van al mismo registro).

## Si la consola se queda «colgada» (sin respuesta a botones)
- Recuperación sin reiniciar, por SSH: `pkill -f QtWebEngineProcess; pkill -f hub_browser.py; pkill -f recomp-hub/main.py`. Luego vuelve a abrir Hub desde Steam.
- El navegador de Hub ahora: se cierra con **Esc** (o Ctrl+Q / Alt+F4) además del botón VOLVER A HUB; muere si Hub desaparece; recarga la página si su proceso interno muere (o se cierra tras 3 fallos); y Hub mata todo su grupo de procesos al cerrarlo o al salir.
- Al arrancar, Hub ya no «trae al frente» su ventana salvo que haya abierto un navegador en la última media hora (antes un archivo en `~/Downloads` podía disparar ese gesto al inicio y dejar el logo de Steam girando).
- Niveles de compatibilidad: AUTO → SIN SANDBOX → SIN SANDBOX Y SIN GPU. El registro mostraba `zygote_host_impl_linux.cc: Check failed … No such file or directory` (Chromium no puede crear su sandbox dentro del lanzamiento de Steam); el nivel SIN SANDBOX lo evita a costa de quitar el aislamiento de Chromium.

## Parciales abandonados y error fatal del sandbox (v1.29)
- Un archivo parcial viejo en `~/Downloads` (`*.crdownload`, `*.part`…) que ya estaba al arrancar y no crece **no cuenta** como descarga (antes aparecía «Descarga detectada» en cada arranque). Si vuelve a crecer, sí.
- Hub lee el stderr del navegador de Hub: si Chromium declara un error `FATAL` de sandbox/zygote (antes se quedaba ~60 s colgado y luego moría con -5), Hub lo corta de inmediato y reintenta en el nivel siguiente (SIN SANDBOX), que recuerda.

## Arranque lento/colgado del navegador de Hub en Gamescope (v1.30)
- Tu registro mostraba, tras «QApplication creada», solo mensajes de `[Gamescope WSI]` (Vulkan) y nada más: la ventana se quedaba esperando a Vulkan/GPU. Además Qt avisaba de locale ANSI.
- Ahora Hub lanza el navegador con `LANG=C.UTF-8`, y tiene un **vigilante**: si la ventana no queda lista en 25 s (o Chromium da un `FATAL`, o se cuelga), lo corta y reintenta en el nivel siguiente, que recuerda:
  1. AUTO.
  2. OPENGL Y SIN SANDBOX (`--no-sandbox`, `QSG_RHI_BACKEND=opengl`: evita Vulkan).
  3. SOFTWARE Y SIN SANDBOX (`--disable-gpu`, `QT_QUICK_BACKEND=software`).
- Se cambia a mano en AJUSTES → NAVEGADOR DE HUB · COMPATIBILIDAD GRÁFICA.

## Contadores de «generando descarga» que no avanzan (v1.31)
- Chromium frena los temporizadores de una página que cree en segundo plano (ventana sin foco en Gamescope) y muchas webs pausan su cuenta atrás si `document.hidden`. El navegador de Hub ahora arranca con `--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows` e inyecta en cada página que la ventana está visible y con foco.
- Diagnóstico en `data/hub.log`: `[browser] página: <sitio> → visible | true | false | <user-agent>` (estado de visibilidad, foco, `navigator.webdriver` y UA) y `[browser] js: …` (hasta 40 avisos/errores de JavaScript de la página). Un navegador de Hub **no se firma ni se anuncia como bot**: es Chromium real con `navigator.webdriver = false`.

## Si al cerrar y volver a abrir Hub se queda el logo de Steam girando (v1.32)
Steam espera a que terminen **todos** los procesos que lanzó el juego; si queda alguno vivo (un Hub colgado, el navegador de Hub, un `QtWebEngineProcess`), no deja relanzarlo.
- `bin/hub` ahora, al arrancar, cierra un Hub anterior vivo y los restos del navegador de Hub; y al terminar vuelve a limpiar. Hub, al salir, cierra todos sus procesos hijos (`[salida] cerré N proceso(s) hijo(s)…`).
- Antes de reiniciar la consola, por SSH: `ps -eo pid,ppid,pgid,etimes,stat,args | grep -E "recomp-hub|hub_browser|QtWebEngine|SteamLaunch AppId=2199108210" | grep -v grep` (qué sigue vivo) y `pkill -9 -f recomp-hub; pkill -9 -f "SteamLaunch AppId=2199108210"`; si aún no abre, `steam -shutdown` (Game Mode reinicia Steam solo).

## Navegador de Hub: salir con descargas y errores en slots (v1.33)
- Si cierras el navegador (VOLVER A HUB, Esc) con una descarga en curso, avisa y exige pulsar otra vez en 6 s para cancelarla (antes se quedaba a medias).
- Un error de Python dentro del navegador ya no aborta el proceso (en tu registro: «wrapped C/C++ object of type QLabel has been deleted» → código -6); se anota como `[browser] excepción ignorada`.
- Si «no responde ningún botón» pero Hub está vivo (`[vivo] … fps 45`, `inactivo` creciendo), la entrada no llega a Hub: casi seguro el teclado/superposición de Steam o el foco de Gamescope siguen en otra ventana. Pulsa el botón Steam y cierra el teclado, o por SSH `pkill -9 -f QtWebEngineProcess`.

## JUGAR, carpeta del juego, partidas y Steam (v1.34)
- **JUGAR cierra Hub** (ajuste «AL PULSAR JUGAR», por defecto activado). El juego se lanza con `bin/play` en su propia sesión y Hub sale 2 s después; lo que Hub cierra al salir **nunca** incluye al juego, y Hub no vuelve a ponerse delante. Queda en el registro como `[jugar]`. Antes Hub seguía abierto detrás/encima del juego, por eso parecía que «se cerraba solo».
- **Dónde queda cada juego**: `~/Games/<carpeta>/` (el mismo criterio que los proyectos iniciales); el binario, el `.release_version` y, si lo activas, sus partidas. La ficha muestra la ruta exacta en el panel **LAUNCHER, STEAM Y PARTIDAS**.
- **PARTIDAS EN LA CARPETA DEL JUEGO**: edita `~/Games/launcher/games/<id>.toml` (copia `.toml.hub-bak`, bloque marcado `# hub:portable`) para que el juego use `XDG_CONFIG_HOME=$INSTALL_DIR/config` y `XDG_DATA_HOME=$INSTALL_DIR/data`, y añade `config/` y `data/` a `preserve` (las actualizaciones no las tocan). **Copia** (no mueve) lo que el juego ya tenía en `~/.config` / `~/.local/share`. Solo sirve si el juego respeta XDG (los de SDL/Qt/Recomp normalmente sí; no está verificado juego a juego). Se revierte con el mismo botón.
- **SELECTOR EN MI BIBLIOTECA**: pone `[run] cwd` del `.toml` en la carpeta donde está tu archivo reconocido (p. ej. `~/Nextcloud/Emulation/roms/n64`). Que el diálogo de «elegir archivo» del juego empiece ahí depende del juego (muchos usan el directorio actual, otros recuerdan el último). Requiere haber reconocido/elegido el archivo antes.
- **ARTE E ICONO PARA STEAM**: ejecuta `bin/play --shortcuts` y `bin/play --art <id>` (SteamGridDB; necesita la clave en `~/Games/launcher/.env`) y muestra el registro en DESCARGAS. **AÑADIR A STEAM** ejecuta `bin/play --steam --yes` (cierra Steam, copia `shortcuts.vdf`): solo en modo escritorio; en Big Picture muestra el comando para lanzarlo desde allí.
- Si el juego te pide el archivo en **cada** arranque, es comportamiento del propio juego (BM64Recompiled guarda sus datos en `~/.config/BM64Recompiled`); el modo portátil lo deja dentro de `~/Games/<juego>/config` para poder verlo y conservarlo.

## Rediseño visual estilo Apple (v1.35)
Paleta oscura «sistema» (negro casi puro, grises por capas, azul/verde/naranja/rojo de iOS), tarjetas y paneles con esquinas más redondas y sin bordes (solo el anillo blanco de foco), pestañas como control segmentado, chips en forma de píldora (el activo en blanco), estados con fondo teñido, ajustes como lista agrupada con «›», y barras superior/inferior sin bloque sólido (solo una línea fina). Todo sale de `button()`, `rr()` y la paleta de `hub/ui.py`: cambiar ahí cambia toda la interfaz. Sin desenfoques ni sombras difusas a propósito (bajarían los FPS en la Ally).

## Inicio pensado para mando, fondos propios y «Añadir a Steam» (v1.36)
- **Secciones**: INICIO · EXPLORAR · DESCARGAS · AJUSTES (LB/RB cambian). **Inicio** solo muestra tus juegos instalados en tarjetas grandes: **A = jugar**, **Y = opciones del juego** (ficha), **X = actualizar** si hay versión nueva; debajo, 4 accesos: Explorar, Actualizaciones, Descargas, Añadir a Steam. **Explorar** primero enseña las consolas (con cuántos juegos hay/instalados) y, al abrir una, la lista; **B** vuelve atrás. «Buscar en GitHub» y «Mi biblioteca de ROMs» viven dentro de Explorar. Lo táctil/avanzado (ficha completa, compilar, portar, ajustes) sigue igual.
- **Fondo e icono propios**: en la ficha (panel LAUNCHER, STEAM Y PARTIDAS) → «FONDO E ICONO PROPIOS»: eliges una imagen (png/jpg/webp) y Hub genera en `~/Games/<juego>/art/`: `icon.png` (512²), `portrait.png` (600×900), `banner.png` (920×430), `hero.png` (1920×620), `logo.png` (transparente), `cover.png` (la portada de Hub, sin texto). Enlaza esos archivos en el `.toml` del launcher (`[steam] icon/portrait/banner/hero/logo` y `[ui] background`; no pisa claves que ya pusiste a mano) y las tarjetas del inicio usan la portada. «QUITAR ARTE PROPIO» lo desenlaza sin borrar los archivos. Sin dependencias extra (solo pygame).
- **AÑADIR TODO A STEAM** (Inicio → «Añadir a Steam», o en Ajustes): en Big Picture el botón **Pasar al escritorio** deja un arranque automático de una sola vez y ejecuta `steamos-session-select plasma` (si falla prueba `desktop`); Hub se cierra y, ya en el escritorio, se abre solo en **Preparar Steam**: eliges el fondo de cada juego y pulsas **Aplicar a Steam** (`bin/play --shortcuts`, `--art`, `--steam --yes`: cierra Steam, copia `shortcuts.vdf`). Cuando acaba, **Volver al modo juego** (`steamos-session-select gamescope`) o lo haces tú. Si no existe `steamos-session-select`, Hub te dice cómo hacerlo a mano. `hub --steam-setup` abre esa pantalla directamente.
- **Sin verificar en hardware**: el cambio de sesión (`steamos-session-select plasma|desktop|gamescope`) y que el arranque automático se abra en tu escritorio; que Steam acepte el arte propio tras `--steam`; el aspecto con mando real.

## Elegir el arte de cada juego y portadas con relleno difuminado (v1.37)
- **Elegir arte (SteamGridDB)**: ficha → «ELEGIR ARTE», o Inicio → Añadir a Steam → A sobre el juego. Primero eliges **cuál es el juego** entre los resultados de SteamGridDB (si no sale el tuyo: «BUSCAR CON OTRO NOMBRE»; sirve para juegos como Bomberman cuyo nombre de carpeta no coincide) y luego una imagen de cada tipo: portada vertical, banner, fondo (hero), icono y logo (LB/RB cambia de tipo). Lo elegido se guarda en `~/Games/<juego>/art/<tipo>.png` y se enlaza en el `.toml` del launcher. Esto reemplaza el «siempre la primera opción» de `bin/play --art`.
- **Clave**: la misma del launcher (`STEAMGRIDDB_KEY` en `~/Games/launcher/.env`); si falta, Hub te pide pegarla y la escribe ahí (una sola copia).
- **Arte ya bajado por el launcher** (`~/Games/launcher/art/<id>/`) se **copia** a la carpeta del juego la primera vez que se muestra (no pisa lo que ya haya).
- **Portadas en Hub**: las tarjetas del Inicio usan la primera que exista en `art/` (`cover`, `hero`, `banner`, `portrait`). Si la proporción no encaja (p. ej. portada vertical en tarjeta apaisada) se muestra entera y el hueco se rellena con la misma imagen ampliada y difuminada.
- Pendiente de verificar con la API real de SteamGridDB (aquí se probó con un servidor simulado): los filtros de medidas y de estilo pueden cambiar.

## Varias fuentes de carátulas y tiempos de espera (v1.38)
- En el selector de arte, **FUENTE** alterna entre **SteamGridDB** (con clave) y **libretro** (libretro-thumbnails, **sin cuenta ni clave**; es lo que usa RetroArch). Si no hay clave de SteamGridDB, se empieza por libretro. Lo último elegido se recuerda (`art_source`).
- **libretro**: Hub lee el listado de `thumbnails.libretro.com/<sistema>/Named_Boxarts/`, propone los títulos más parecidos a tu búsqueda (tú eliges cuál) y ofrece portada (Named_Boxarts), banner (Named_Titles), fondo (Named_Snaps/Titles), icono y logo si existen. Solo hay carpeta para consolas clásicas (N64, GameCube, Wii, SNES, NES, GB/GBC/GBA, DS/3DS, PS1/PS2/PS3/PSP, Dreamcast, Saturn, Mega Drive, Xbox…): **no hay para PC ni PS4**. El listado se guarda 7 días en `data/cache/libretro/`.
- **Tiempos de espera**: las peticiones usan 45 s y un reintento; si no responden, el mensaje dice qué servidor falló y sugiere probar la otra fuente o definir `HTTPS_PROXY` (algunas redes bloquean o ralentizan SteamGridDB). Queda en `hub.log` como `[arte] error:`.
- **ScreenScraper** (screenscraper.fr): no incluido. Su API exige credenciales de desarrollador (devid/devpassword) además de tu cuenta, y no puedo llevarlas en Hub. Si consigues las tuyas se puede añadir como tercera fuente.
- Sin verificar con los servidores reales: el formato del listado HTML de libretro y los nombres exactos de sus carpetas (probado con un servidor simulado).

## ScreenScraper, vista previa antes de elegir y una sola clave (v1.39)
- **ScreenScraper** como tercera fuente (botón FUENTE): botones **USUARIO** y **CONTRASEÑA** guardan `SCREENSCRAPER_USER` / `SCREENSCRAPER_PASSWORD` en `~/Games/launcher/.env` (permisos 0600, el mismo archivo que la clave de SteamGridDB: una sola copia para los dos proyectos). Si tienes credenciales de desarrollador, añade a mano `SCREENSCRAPER_DEV_ID` y `SCREENSCRAPER_DEV_PASSWORD` en ese mismo archivo. Búsqueda por nombre (los resultados del sistema de tu juego salen primero) y medios: box-2D → portada, sstitle/marquee → banner, fanart/ss → fondo, wheel → logo. La contraseña se escribe con el teclado en pantalla (se ve al teclear).
- **SteamGridDB**: Hub lee la clave directamente de `~/Games/launcher/.env`; no hay que copiarla.
- **Vista previa**: **A** sobre una miniatura abre la imagen grande (baja la completa en segundo plano) junto a «Así se verá en Hub» (la tarjeta con el relleno difuminado). **◀ ▶** pasan a la opción anterior/siguiente, **A** (o «USAR ESTA IMAGEN») la guarda, **B** vuelve a la lista. LB/RB cambian de tipo de imagen.
- Sin verificar con el servicio real: que ScreenScraper acepte solo usuario/contraseña sin credenciales de desarrollador, la estructura exacta de su respuesta y la ausencia de límites para tu cuenta.

## JUGAR espera a que el juego arranque (v1.40)
Al pulsar JUGAR, Hub ya no se cierra a los 2 s: vigila el lanzador (`bin/play`). Si sigue vivo a los 6 s lo da por arrancado y se cierra; si termina antes con error, **Hub se queda abierto** y avisa con el código y el registro del launcher (`~/Games/launcher/state/<id>.log`). Todo queda en `hub.log` como `[jugar]`. Los avisos `ld.so … gameoverlayrenderer.so … ELFCLASS32` del arranque son ruido inofensivo de Steam (overlay de 32 bits).
SteamGridDB desde Rusia: `The handshake operation timed out` = el servidor no completa el TLS desde tu red; usa libretro o ScreenScraper, o define `HTTPS_PROXY` para Hub.

## Teclado de Steam más robusto y registro de entrada (v1.41)
- Con el **teclado de Steam** abierto, Hub solo acepta texto, Backspace y Enter: las demás teclas (flechas, Tab, etc.) ya no mueven el foco ni disparan acciones, que era lo que hacía «saltar de recuadro».
- Mientras hay un teclado abierto, `hub.log` guarda una línea `[tecla]` por evento (máx. 400): tipo, nombre de la tecla (**nunca el carácter**, por si es una contraseña), tipo de teclado, foco y si la ventana tiene el foco de entrada. Úsalo para ver si Steam entrega la entrada a Hub o la retiene.
- Para investigar un cuelgue justo después de reproducirlo (por SSH): `tail -n 80 ~/Games/recomp-hub/data/hub.log`, `uptime; free -m`, `ps -eo pid,etimes,stat,pcpu,pmem,cmd --sort=-pcpu | head -15` y `kill -USR2 $(pgrep -f 'recomp-hub/main.py')` (vuelca la pila de todos los hilos en el log).

## Miniaturas del selector de arte: más rápidas y sin condiciones de carrera (v1.42)
- Las miniaturas se bajan **en paralelo** (6 a la vez) y se guardan en `data/cache/art/`: la segunda vez que ves las mismas opciones es instantáneo. Antes se bajaban de una en una, cada una con su propia conexión TLS, y en redes lentas (apretón TLS de varios segundos) se acumulaba. La barra de estado muestra «Cargando miniaturas n/N» y `hub.log` anota `[arte] <tipo>: N opciones, M miniaturas en X s`.
- Si una miniatura falla, el recuadro dice «sin miniatura (A para ver)» (la vista previa baja la imagen completa) y el motivo queda en `hub.log` como `[arte] miniatura … falló`. Antes el fallo se silenciaba y el recuadro quedaba vacío.
- La clave de SteamGridDB solo se envía a la API, ya no a los servidores de imágenes (CDN).
- Cambiar de fuente, nombre o tipo mientras algo carga ya no deja que una respuesta vieja pise la nueva.

## Registro de «Aplicar a Steam» y de los trabajos (v1.43)
- Cada línea de los trabajos de fondo (ARTE PARA STEAM, STEAM: TODO) se guarda también en `hub.log` con la etiqueta `[trabajo]`: la orden ejecutada, su salida y el código de cada paso. Si «termina con avisos», el mensaje dice **qué paso falló** (p. ej. «Descargando carátulas (código 1)») y queda como `[trabajo] … terminó con avisos`.
- Ver lo ocurrido: `grep "\[trabajo\]" ~/Games/recomp-hub/data/hub.log | tail -n 60`. Un aviso en «Descargando carátulas» suele ser SteamGridDB sin respuesta o un juego sin arte; **no impide** que el paso «Aplicando en Steam» se ejecute.
- Repetir a mano y ver todo: `~/Games/launcher/bin/play --shortcuts`, `~/Games/launcher/bin/play --art`, `~/Games/launcher/bin/play --steam --dry-run`.

## «Aplicar a Steam» ya no se queda esperando una respuesta (v1.44)
- `bin/play --art` es **interactivo** (pregunta «¿Cuál es 'Bomberman 64'? [número, Enter=1…]»). Hub no puede contestar, así que fallaba y el trabajo terminaba «con avisos». Ahora «Aplicar a Steam» solo ejecuta `--shortcuts` y `--steam --yes`; el arte se elige antes con **ELEGIR ARTE** (Hub lo guarda en la carpeta del juego y lo enlaza en el `.toml`, que es lo que lee `--steam`).
- Si hay juegos instalados **sin ningún arte**, Hub avisa antes de aplicar (y lo anota como `[steam] juegos SIN arte`): se añadirían a Steam sin carátula.
- Ninguna orden de fondo puede quedarse esperando el teclado: se ejecutan con la entrada cerrada y fallan rápido.
- En la ficha, el botón antiguo pasa a llamarse **GENERAR ACCESO PARA STEAM** (solo `--shortcuts`).
- Si prefieres el asistente de la terminal: `~/Games/launcher/bin/play --art <id>` y contestas tú.

## Pulido de diseño (v1.45)
- **Iconos dibujados**: ◀ ▶ ✓ ▼ no existen en la fuente del sistema (salían como cuadrados, p. ej. en «Descargas simultáneas»). Ahora flechas, marcas ✓ y chevrones se dibujan con formas, sin depender de la fuente.
- **Fuente de imágenes**: selector de 3 opciones tocables (SteamGridDB / libretro / ScreenScraper) con la activa resaltada; sin «(clave) (cambiar)». Los botones PEGAR CLAVE / USUARIO / CONTRASEÑA **solo aparecen si faltan**; si ya hay clave o credenciales no se piden. El teclado de Steam no se reabre dos veces en <1,5 s.
- **Inicio / desplazamiento**: al volver arriba con la cruceta el contenido regresa a 0 (el título «Tus juegos» ya no queda cortado); cuando hay más contenido abajo aparece un degradado con la pastilla «Más abajo ⌄».
- **Descargas**: título grande, tarjetas redondeadas con anillo de foco blanco, barras de progreso más gruesas, estado vacío cuidado.
- **Ajustes**: secciones (Descargas, Catálogo, GitHub, Juegos y compilación, Steam y juego, Navegador y teclado, Sistema), etiqueta a la izquierda y valor a la derecha con chevrón, texto en mayúscula/minúscula normal, selector numérico con botones dibujados.

## Catálogo de RecompLauncher y Liberty City Stories (v1.46)
- **AJUSTES → IMPORTAR CATÁLOGO → RecompLauncher**: lee el `sitemap.xml` público de recomplauncher.com (~280 juegos de PC), baja cada `/game/<nombre>` (5 a la vez, con reintentos), saca nombre, descripción, plataforma, si anuncia Linux y **el repositorio de GitHub**, y lo guarda en `data/imports/recomplauncher.json`. Releases, builds de Linux y requisitos los sigue consultando Hub en GitHub. Los juegos sin repositorio aparecen como «SIN REPOSITORIO». Tarda ~1 min; el aviso muestra el avance. Respeta su `robots.txt` (solo `/admin/` está vetado).
- Probado con un servidor simulado; **no verificado con la web real** (formato de las páginas visto en `2ship2harkinian`: `<title>`, meta description, JSON-LD `operatingSystem`, enlace a GitHub). Si una página cambia de formato se salta y queda en `hub.log` como `[recomplauncher]`.
- RecompStore (PS5) se descartó: es una tienda de homebrew para PS5 sin lista pública.
- **GTA: Liberty City Stories** (`elmasas/lcs-recomp`) añadido a la lista base: no está en Quiver ni en RecompLauncher. Requiere ULUS-10041 v1.05 (EBOOT.ELF descifrado + PSP_GAME); se compila en distrobox. RecompLauncher sí trae «Vice City Stories».

## Con el menú de Steam (QAM/overlay) encima, Hub no reacciona (v1.47)
- Causa: Hub lee el mando directamente de `/dev/input` (no a través de Steam), así que al abrir el QAM o el overlay, las flechas llegaban **a los dos**. Ahora el mando se **ignora** mientras la ventana de Hub no tiene el foco (`WINDOWFOCUSLOST`), durante 0,4 s tras recuperarlo (para que el botón que cierra el menú no active nada en Hub) y si el evento es viejo (>0,6 s). Al perder el foco se vacían la cola y las teclas mantenidas.
- Además, el botón **Steam/guía** (`BTN_MODE`, si tu mando lo expone) pausa la entrada 1,5 s por si el overlay no quita el foco.
- Queda en `hub.log` como `[foco]` (primer evento ignorado, y los 20 y 100) y `[ventana] WindowFocusLost/Gained`. Para ver qué pasa al abrir el QAM: `grep -E "\[foco\]|\[ventana\]" ~/Games/recomp-hub/data/hub.log | tail -n 30`.
- **Sin verificar en el Ally**: que Gamescope entregue `WINDOWFOCUSLOST` cuando abre el QAM. Si el log no muestra ese evento al abrirlo, la protección que actúa es solo la pausa del botón Steam (y puede que el botón «…» del QAM no pase por ahí).

### Ajuste tras ver el log real (v1.48)
- En tu `hub.log` casi cada apertura del menú aparece como `WindowHidden → WindowExposed → WindowFocusGained` **sin** `WindowFocusLost` delante: la v1.47 solo reaccionaba a `FocusLost`. Ahora `WindowHidden` y `WindowMinimized` también ponen el mando en pausa.
- Las líneas `[ventana]` llevan hora y el estado de foco de SDL en ese instante, para ver cuánto dura cada ocultación.
- Red de seguridad: si SDL informa foco pero no llegó `FocusGained` en 2 s, la entrada se reanuda (`[foco] SDL informa foco de nuevo`), para no quedarse sordo.

## Foco de Gamescope: el mando se pausa mientras haya un menú de Steam encima (v1.49)
- Tu `hub.log` mostró que SDL sigue diciendo «foco = sí» con el QAM abierto, y que `WindowHidden/Exposed/FocusGained` es un parpadeo de repintado. Así que Hub lee ahora **quién tiene el foco en Gamescope** (`GAMESCOPE_FOCUSED_WINDOW` y `GAMESCOPE_FOCUSED_APP` de la ventana raíz, con `xprop`, cada 0,4 s). La primera lectura (Hub delante) es la referencia; si el foco pasa a **otra ventana** (QAM, overlay, teclado de Steam), el mando se ignora hasta que Hub vuelva a tener el foco (+0,4 s para que el botón que cerró el menú no le llegue).
- Requiere `xprop` (en tu sistema ya está). Sin Gamescope o sin `xprop` no hace nada y siguen las otras protecciones (foco de SDL y pausa del botón Steam).
- Válvula de seguridad: si pasan 90 s con «otra ventana» (p. ej. Hub recreó su ventana y cambió el id), se toma esa como nueva referencia.
- `hub.log`: `[foco] gamescope: ventana de Hub=… app=…` al arrancar; `[foco] gamescope HH:MM:SS: ventana=… · OTRA ventana tiene el foco (menú de Steam encima)` / `Hub vuelve a tener el foco` en cada cambio; `[foco] mando ignorado (…) · menú encima=SÍ`.
- **Sin verificar en el Ally**: que `GAMESCOPE_FOCUSED_WINDOW` cambie al abrir el QAM (en tu `xprop` existe, pero no vi su valor con el menú abierto).

### Corrección v1.50: dónde se lee el foco de Gamescope
- Tu `xprop` mostró que `GAMESCOPE_FOCUSED_WINDOW` está en el display **:0**, no en **:1** (el Xwayland de los juegos, que es el `DISPLAY` de Hub cuando lo lanza Steam). La v1.49 miraba solo el suyo y no encontraba nada. Ahora prueba `:0`, `:1` y su `DISPLAY`, y recuerda cuál funcionó (`leído en :0` en `hub.log`). Si no lo encuentra en ninguno lo dice una vez: `[foco] gamescope: no encuentro GAMESCOPE_FOCUSED_WINDOW en …`.

### Corrección v1.51: la UI de Steam se distingue por la app, no por la ventana
- Tu log: referencia `ventana=10485770 app=2199108210` (Hub) y después `ventana=10485770 app=769`: la ventana no cambia al abrir el menú, **cambia la app** (769 = interfaz de Steam). Ahora el mando se pausa si `GAMESCOPE_FOCUSED_APP` es 769 o si (ventana, app) difiere de la referencia de Hub. Si Hub arranca con la UI de Steam delante, la referencia se toma en la primera lectura que no sea 769.
- Pendiente de confirmar con otro log: que al **cerrar** el menú la app vuelva a la de Hub (debe aparecer `Hub vuelve a tener el foco` con `app=2199108210`).

## Cambiar la clave / cuenta de las carátulas (v1.52)
- En **ELEGIR ARTE** los botones de cuenta ya **no desaparecen** cuando hay datos guardados: si falta algo salen destacados (azul); si ya existe, salen discretos con ✓ para poder **cambiarlos** (SteamGridDB: «CAMBIAR CLAVE»; ScreenScraper: «USUARIO: <nombre>» y «CONTRASEÑA»). Guardar uno nuevo reemplaza el anterior en `~/Games/launcher/.env` y repite la búsqueda.
- Si ScreenScraper rechaza el login, el aviso dice «no aceptó tu usuario o contraseña (…respuesta del servidor…)» y los dos botones se destacan.
- También en **AJUSTES → Imágenes (carátulas)**: clave de SteamGridDB, usuario y contraseña de ScreenScraper.
- Sin verificar con el servidor real: el texto exacto con el que ScreenScraper responde a un login erróneo (se detectan palabras como «login», «identifiant», «403»). Si te sale otro mensaje, pégalo y lo añado.
- Foco de Gamescope (v1.51), según tu log: el menú de Steam se detecta (`app=769`) y Hub ignora el mando; al cerrar, `Hub vuelve a tener el foco`. Se vieron además cambios de ventana con la **misma app** (`ventana=20971530`, `20971567`) que Hub trata como «otra ventana encima».

## ScreenScraper pide credenciales de desarrollador (v1.53)
- Confirmado con la respuesta real del servidor: `Erreur de login : Vérifier vos identifiants développeur !`. La API de ScreenScraper exige **devid + devpassword** (credenciales de desarrollador, que se piden en el foro de screenscraper.fr) además de tu cuenta; con solo usuario y contraseña **no funciona**, aunque sean correctos. Hub no puede llevarlas incluidas.
- Si las consigues: **AJUSTES → Imágenes → ID / CONTRASEÑA DE DESARROLLADOR**, o a mano en `~/Games/launcher/.env`: `SCREENSCRAPER_USER`, `SCREENSCRAPER_PASSWORD`, `SCREENSCRAPER_DEV_ID`, `SCREENSCRAPER_DEV_PASSWORD`.
- El aviso de Hub ahora dice exactamente eso («exige credenciales de DESARROLLADOR…»), en vez de culpar a tu usuario/contraseña. Sin ellas, usa **libretro** (sin cuenta) o **SteamGridDB**.

## TheGamesDB como fuente; ScreenScraper fuera del menú (v1.54)
- **FUENTE DE IMÁGENES**: SteamGridDB · libretro · **TheGamesDB**. ScreenScraper se quitó del menú (exige credenciales de desarrollador); el código sigue en `artsrc.py` por si algún día las consigues. Si tenías ScreenScraper como fuente recordada, Hub vuelve a SteamGridDB.
- **TheGamesDB** (api.thegamesdb.net, el otro scraper de ES-DE): necesita una **clave de API**. Botón **PEGAR CLAVE** (o AJUSTES → Imágenes → Clave de TheGamesDB); se guarda como `THEGAMESDB_KEY` en `~/Games/launcher/.env`. Búsqueda por nombre (primero la plataforma de tu juego) y imágenes: portada = boxart frontal, banner, fondo = fanart (o captura), logo = clearlogo.
- **Sin verificar**: cómo se consigue la clave (creo que desde tu cuenta en thegamesdb.net / su foro, y puede exigir solicitud, como ScreenScraper), y la forma exacta de sus respuestas (probado con un servidor simulado según su documentación pública, que recuerdo de memoria). Los ids de plataforma que uso para ordenar resultados son aproximados; si alguno falla solo cambia el orden.
- Errores claros: sin clave → «TheGamesDB necesita clave de API…»; 401/403 → «no aceptó la clave de API: revísala».

## Tu servidor de catálogo (JSON-RPC local) (v1.55)
Cliente del daemon propio `http://localhost:8765/rpc` (JSON-RPC 2.0, cabecera `X-Catalog-Token` leída de `~/.cache/catalog-service/token`). Solo biblioteca estándar.
- **`hub/catalogservice.py`**: `call()` + `health/search/variants/download/job_status/job_cancel`. Si el puerto no responde arranca `~/Games/local-catalog-service/service.py` (con su `.venv` o `python3`, `start_new_session=True`, `stdin=DEVNULL`, log en `~/.cache/catalog-service/service.log`) y espera hasta 5 s. Errores tipados: `TransportError`, `TokenError`, `RpcError` → `MethodNotFound` (-32601), `InvalidParams` (-32602), `ServiceError` (cualquier otro código, se conserva `.code`/`.message`). Variables de entorno para pruebas: `HUB_CATALOG_URL`, `HUB_CATALOG_TOKEN_FILE`, `HUB_CATALOG_LOG`, `HUB_CATALOG_DIR`.
  - Terminal: `python3 ~/Games/recomp-hub/hub/catalogservice.py health` · `… search "bomberman" [sistema]` · `… variants FUENTE ITEM_ID`.
- **`hub/catalogjobs.py`**: consulta `job_status` cada 500 ms y expone cada trabajo con la forma de `Download` (progreso, velocidad, fase, estado), así que usa la misma fila de **DESCARGAS**. Fases: «Resolviendo servidor…» / «Descargando». Tolera que `completed` no traiga `sha1`/`crc32` (si vienen, se anotan en `hub.log` como `[catalogo] completa …`). 3 fallos de conexión seguidos marcan error.
- **Ficha del juego → ARCHIVO DEL JUEGO → BUSCAR EN MI SERVIDOR**: busca (con el nombre y plataforma del juego y su `requires`), lista los 8 mejores por confianza (A elige, B vuelve), luego las variantes (archivo · región · formato · tamaño) y descarga a la carpeta de descargas de Hub. Las fuentes `DEAD` salen en gris «(caída)» y solo avisan; si **todas** están caídas el botón se desactiva. El estado de salud se consulta en segundo plano cada 60 s **sin arrancar el daemon**.
- **Al completar**: el `path` pasa por `check_file`, el mismo flujo que un archivo elegido a mano (`library.match` + `adopt`). Se verifica siempre, aunque el daemon dé hash.
- **En DESCARGAS**: el contrato no tiene pausa/reanudar, así que estas filas solo muestran **CANCELAR** (pide `job_cancel`) y **VER** al terminar; `resumable=false` se indica como «(sin pausa)» al elegir la variante.
- Sin verificar contra tu daemon real: códigos de error propios, nombres exactos de fases y que `search` acepte `system` con el nombre de plataforma de Hub (p. ej. «Nintendo 64»). Pruebas con un daemon falso: `test/test_catalog.py`, `test/test_catalog_ui.py`.

## El servicio de catálogo arranca con Hub y el fallo del token (v1.56)
- **Causa del «error de token»**: el cliente leía el token **antes** de llamar; si el daemon crea ese archivo al arrancar, sin daemon no había token y fallaba antes de intentar arrancarlo. Ahora, si falta el token, Hub arranca el servicio y espera hasta 5 s a que abra el puerto **y** cree el token. Si el servicio ya escucha pero el token no aparece, el error dice eso (`TokenMissing`) en vez de lanzar otro daemon encima.
- **Autoarranque**: al abrir Hub, en segundo plano, se deja el servicio corriendo (si existe `~/Games/local-catalog-service/service.py`). Queda en `hub.log` como `[catalogo] autoarranque: OK · …` o el motivo. AJUSTES → «Servidor de catálogo» → «Arrancar el servicio con Hub: SÍ/NO». El daemon se lanza en su propia sesión (`start_new_session`), así que **sigue vivo cuando Hub se cierra** (no lo detengo yo).
- Para ver qué pasa: `grep "\[catalogo\]" ~/Games/recomp-hub/data/hub.log | tail` · `tail ~/.cache/catalog-service/service.log` · `ss -ltnp | grep 8765`.

## Compatibilidad con Python < 3.12 (v1.57)
- `catalog.py` tenía una f-string con una barra invertida dentro (`f"…{re.sub(r'\.git$', …)}"`), que **solo es válida desde Python 3.12**. Con un `.venv` activo de Python 3.11 o anterior, el instalador avisaba «py_compile falló» y ese módulo no se podía importar. Corregido; `test/test_py311.py` compila todo el código con Python 3.11 para que no vuelva a pasar.
- Si te aparece el aviso al instalar pero el Hub ya funcionaba: `bin/hub` elige el primer Python que tenga `pygame` (no tiene por qué ser el de tu `.venv`). Para ver cuál usa: `grep "python" ~/Games/recomp-hub/data/hub.log | tail -n 3`.

## v1.58 — Listas largas de variantes (modal paginado)
- El modal de elección (variantes, resultados del servidor, etc.) ya no se sale de la pantalla: muestra las opciones que caben y añade **ANTERIOR / SIGUIENTE** (con A en el mando) y el título "(1/3 · 24 opciones)".
- El tope de variantes pasa de 10 a 60.
- Sin verificar en la Ally real: cuántas caben por página en tu resolución (en 1280×800 salen 10).

## v1.58b — Descarga del catálogo: carpeta de destino
- Antes de `download` se crea la carpeta de descargas y se envía como ruta absoluta; el log muestra `dest_dir`, el `variant_id` y el código/datos del error del daemon.
- Sin verificar: la causa real del "no existe el directorio" (falta el log).

## v1.58c — Descarga "completa" sin archivo
- Si el daemon marca el job como completo pero la ruta no existe, Hub lo dice (aviso + log) en vez de intentar abrirlo.

## v1.59 — Borrar repo con papelera, listas con scroll, sonda de rendimiento
- **Quitado «Dónde comprar»** (botón, modal y atajos).
- **Borrar** (al final de la ficha): modal con casillas — *Quitar de la biblioteca*, *Carpeta del proyecto*, *Archivos descargados* (esta última **desmarcada por defecto**) —, el foco empieza en **Cancelar**. Confirmar es en dos pasos: primer toque «armado» (el botón cambia y se bloquea 1 s), segundo toque en ≥0,8 s y antes de 5 s; si no, se desarma. No se usa «mantener pulsado» porque evdev solo manda eventos de pulsación, sin soltar.
- **Papelera**: nada se borra de verdad; se mueve a `~/Games/.papelera-hub/<fecha>-<nombre>/` con `meta.json`. AJUSTES → «Papelera»: *Restaurar la última* (nunca sobrescribe) y *Vaciar* (con confirmación). Rutas validadas (home, «/», launcher y carpetas ajenas se rechazan) y los enlaces simbólicos (tus ROMs) **nunca se siguen**.
- **Listas largas** (variantes, resultados del servidor): scroll real con rueda/táctil/mando y **flechas ▲▼** que aparecen cuando hay más arriba o abajo; el título dice «(N opciones)». Sustituye a la paginación de v1.58.
- **Sonda de rendimiento**: AJUSTES → «Registrar rendimiento: SÍ» (o `HUB_PERF=1`; umbral `HUB_PERF_MS`, 40 por defecto). Escribe en `hub.log` líneas `[rendimiento]` con el tiempo de eventos/lógica/dibujo, las funciones más lentas y cuánto tarda releer el launcher. Apagada no cuesta nada.
  - Ver: `grep "\[rendimiento\]" ~/Games/recomp-hub/data/hub.log | tail -n 60`
  - Hipótesis (sin confirmar en la Ally): la lentitud al entrar en AJUSTES/EXPLORAR viene de `inst()` releyendo disco de ~300 juegos, no de Python; no hace falta Rust.
- Sin verificar: borrado entre sistemas de ficheros distintos (usa copia+borrado), y que 1 s/0,8 s de armado se sientan bien con el mando.

## v1.60 — Selector de archivos más cómodo + sondeo de listas de proyectos
- **ELEGIR ARCHIVO…** ahora abre directamente en la carpeta de ROMs de la plataforma del juego (p. ej. `…/roms/n64` para Banjo-Kazooie), buscando entre tus `rom_dirs` la subcarpeta cuyo nombre equivale a la plataforma (n64, psx, «Nintendo 64»…). Si no existe, cae al comportamiento anterior (carpetas vigiladas).
- Botones rápidos: **ROMS <sistema>**, **DESCARGAS**, **INICIO** y tus carpetas vigiladas.
- **FILTRAR**: teclado en pantalla para quedarte con los nombres que contengan el texto (p. ej. «banjo»); **QUITAR FILTRO** lo deshace.
- **▲ PÁGINA / PÁGINA ▼** (táctil y mando), flechas de «hay más» y contador de elementos.
- **`tools/probe_sources.py`**: baja las listas públicas (awesome-decomp-games, SamidyFR, CharlotteCross1998, PCGamingWiki, Recompedia, GameWave, decomp.wiki), dice cuántos repos tiene cada una, cuántos son nuevos para el Hub y cuánto se solapan. No modifica nada. `python3 ~/Games/recomp-hub/tools/probe_sources.py --save ~/fuentes`.
- Sin verificar: PCGamingWiki, Recompedia, GameWave y decomp.wiki (mi entorno no llega a ellas).

## v1.61 — Primer fotograma de Inicio sin tirón + sonda más fina
- **Medido en tu Ally** (`HUB_PERF=1`): Ajustes y Explorar **no** dibujan lento (por debajo de 5 ms); el único fotograma lento era el primero de Inicio (~320 ms con el perfilador encendido), por cargar de golpe 3 portadas (`image.load` + `convert` + desenfoque) más releer ~230 juegos del launcher.
- **Portadas**: se carga **una por fotograma** (las demás aparecen en los siguientes, sin tirón).
- **Instalados**: la caché de `inst()` sube de 2 s a 10 s (se invalida igualmente al instalar/desinstalar/borrar).
- **Sonda**: ya no lista `select`/`poll` (son del hilo del mando, no de la interfaz; el perfilador de Python ≥3.12 mira todos los hilos) y registra `ciclo N ms entre fotogramas · flip M ms`, para ver si el retraso está en presentar la imagen (vsync/gamescope) y no en dibujar.
- Sin verificar: que esto quite la sensación de «no hace caso» al entrar en Ajustes; si no, el nuevo `ciclo … flip …` dirá dónde está.

## v1.62 — Portadas en segundo plano
- Medido en tu máquina (`HUB_PERF=1`, por SSH, ventana `offscreen` 1024×768): Ajustes y Explorar **no** aparecen como lentos; Inicio tenía 3-4 fotogramas de 70-109 ms al abrir (con el perfilador, que lo infla) por preparar las portadas, y ~10-25 ms por fotograma de forma continua (dibujo por CPU).
- **Portadas**: se leen, escalan y desenfocan en un **hilo**; la tarjeta sale sin portada un instante y la muestra al terminar. Ya no hay tirones al abrir Inicio. (Sustituye el «una por fotograma» de v1.61.)
- **installed_info**: ya no intenta leer la versión de ~230 juegos que no tienen carpeta ni registro.
- Pendiente/sin verificar: la medición **en modo juego de Steam** (no por SSH; el log dijo `driver=offscreen`); el dibujo continuo de ~10-25 ms por fotograma en Inicio (posible mejora: bajar a ~20 fps en reposo); y que el cierre `código 137 (SIGKILL)` de tu prueba fue tuyo y no falta de memoria.

## v1.63 — Indexador de awesome-decomp-games (≈2200 proyectos)
- **Qué es**: `hub/indexers.py` baja `data/games.json` de [SubmitGame/awesome-decomp-games](https://github.com/SubmitGame/awesome-decomp-games) (que ya agrega a SamidyFR y CharlotteCross1998) y escribe `data/imports/00-awesome-decomp.json`.
- **Reglas**: entran recompilación estática, port de código fuente, engine-remake y decompilación. **Con release → «listos para usar»** (~1140; aunque estén archivados o sin actividad, se marcan `sin-mantenimiento` en la ficha porque un proyecto terminado no necesita actualizarse). **Sin release → etiqueta `solo-codigo`** (~1060: hay que compilarlos) y quedan **ocultos** salvo en Explorar → «Solo código». Se descartan disassembly, browser-port, tool, mods y lo que no sea GitHub.
- **No pisa tu catálogo**: se salta los repos que ya están en el seed, en `catalog.local.json` o en otras listas; el prefijo `00-` hace que cualquier otra lista o tu catálogo local la pisen a ella. Si el resultado saliera vacío o el JSON cambiara de forma, **no toca la lista anterior**; escritura atómica.
- **Cómo actualizar**: AJUSTES → «Catálogo» → «ACTUALIZAR LISTA DE PROYECTOS», o por terminal `~/Games/recomp-hub/bin/hub --update-awesome`.
- Las consolas piden «tu propia copia del juego» (nota en `requires`); PC/DOS/móvil no, salvo `needs_assets`.
- **Rendimiento con ~1100 entradas**: `visible_entries()` se guarda mientras no cambie filtro/búsqueda/instalados/releases (3 ms → 0 ms por fotograma en mi máquina).
- Sin verificar: cómo va con ~2200 entradas en la Ally; el nombre de plataforma de algunas consolas raras; que «Solo código» al final de Explorar sea fácil de encontrar.
- Tests: `tests_pro/test_indexers.py` (16). Nota: crear muchas interfaces en un mismo proceso de pruebas hacía fallar después a `test_ui_flow` («video system not initialized»); no ocurre en Hub (solo hay una), pero las pruebas de UI del indexador comparten una.

## v1.64 — Sonidos de la interfaz y capas translúcidas
- **Sonidos** (`hub/sfx.py`): sintetizados por código, sin archivos ni copyright. Clic suave al mover el foco (el tono sube un poco), dos notas ascendentes al aceptar, dos descendentes al volver, uno de pestaña (LB/RB), uno al abrir un menú y uno grave de error. Todos < 160 ms, volumen bajo. Suenan con mando, teclado y táctil; el movimiento solo suena si el foco cambia de verdad (nada al chocar con el borde) y no se amontonan al mantener pulsado.
- AJUSTES → «Sonido»: activar/desactivar y volumen (25/50/75/100 %). Si no hay audio, queda mudo sin molestar (`[sonido] desactivado` en `hub.log`).
- **Sonidos tuyos**: deja `move`, `confirm`, `back`, `tab`, `open` o `error` (`.wav`/`.ogg`/`.mp3`) en `~/Games/recomp-hub/data/sounds/` y sustituyen al generado (p. ej. los CC0 de Kenney: «Interface Sounds» en OpenGameArt o «UI Audio»). Un archivo estropeado se ignora.
- **Capas translúcidas, sin cálculo por fotograma**: fondo con degradado y dos resplandores suaves (se prepara una vez por tamaño de ventana); barra superior e inferior de cristal (cacheadas) y el contenido de la pantalla se ve pasar por debajo al desplazar; los menús (confirmar, elegir, teclado…) toman **una instantánea desenfocada y oscurecida** de lo de detrás al abrirse y la reutilizan: **con un menú abierto ya no se redibuja la pantalla de debajo** (ahorra CPU) y desaparece el velo alfa de pantalla completa que se creaba en cada fotograma.
- Menús: filo fino alrededor del panel.
- Sin verificar en la Ally: que las barras se vean bien con tu pantalla/brillo, y que el audio salga por gamescope (si no suena, mira `grep sonido ~/Games/recomp-hub/data/hub.log`).
- Tests: `test_sfx.py` (22), `test_glass.py` (8).

## v1.65 — Descargas en tarjetas y selector del juego en tu ROM

- **DESCARGAS rediseñada**: tarjetas en dos columnas con un anillo de avance (porcentaje, ✓ al terminar, rojo si falló), título, estado y dos botones compactos. Arriba, un resumen suelto (activas · en cola · velocidad). Orden: activas, pausadas, en cola, fallidas, terminadas. Compilaciones y archivos recibidos usan las mismas tarjetas.
- **Insignia en la pestaña Descargas** con el número de descargas/compilaciones en curso; late un instante al añadir una descarga (instalación o servicio de catálogo).
- Los errores del servicio se muestran en una sola línea en la tarjeta.
- **Selector de archivos del propio juego** (p. ej. Banjo-Kazooie: «no hay O2R, ¿generar?»): al reconocer el archivo de tu juego, Hub activa solo «SELECTOR EN MI BIBLIOTECA» (`[run] cwd` = carpeta del archivo ya preparado, es decir, el .z64 extraído si bajaste un .zip). Se desactiva con `"auto_libcwd": false` en la configuración o desde el panel del juego. También se aplica al terminar de instalar si el archivo ya estaba reconocido.
- Nota: el .zip sí se abre en Hub (resolve → extrae el .z64 a `library/converted`); el juego no lee zips, por eso el selector ahora empieza donde está el .z64 listo.
- Tests: `tests_pro/test_descargas_v165.py`.

## v1.66 — Siempre extraído a tu biblioteca + ROM en la carpeta del port

- Al reconocer un archivo comprimido (.zip/.7z/.rar o convertido: chd/rvz), Hub **guarda en tu biblioteca el archivo llano** (`roms/<sistema>/Juego.z64|iso|…`) y **elimina el paquete** original una vez comprobado el tamaño de la copia. Si algo falla, no se borra nada. Funciona también si el zip ya estaba en tu biblioteca.
- Ajustes de configuración: `extract_to_library` (por defecto sí) y `delete_archive` (por defecto sí). Con `esde_store = "link"` Hub no toca nada, como antes.
- **`requires.rom_dest`** (o tabla interna por repo; Lighthouse = `~/.local/share/lighthouse`): Hub enlaza ahí la ROM de la biblioteca (enlace simbólico; nunca pisa un archivo real). Así el selector propio del juego (p. ej. «no hay O2R, ¿generar?») la ve de inmediato.
- Nota: la papelera de Hub no se usa aquí (no toca ROMs); la eliminación del paquete es definitiva.
- Tests: `tests_pro/test_extraer_a_biblioteca.py`.

## v1.67 — Pulido de DESCARGAS
- El cuadrado dentro de los círculos era un carácter que la fuente de Gamescope no trae (⬇ ⚙ ▤…): ahora los iconos (✓, ✕, flecha, engranaje, archivo, puntos) se **dibujan con formas**. Un test impide volver a usar símbolos Unicode en las tarjetas.
- Color por estado: fondo con un matiz suave (azul activa, ámbar pausada, rojo fallo, verde lista), filo de color a la izquierda y anillo con centro más oscuro.
- La insignia de la pestaña se sube a la esquina; el banner superior ya no usa ⬇.

## v1.68 — Plan de compilación leído del README (sin IA)
- Ficha del juego → **PLAN DE COMPILACIÓN (LEE EL README)**. Hub lee el README y `BUILDING.md`/`INSTALL.md`/`docs/…` (del clon local si ya existe; si no, por la API de GitHub), toma los bloques de código de las secciones de Linux/compilar y arma un **plan editable**: dependencias → preparar (submódulos) → configurar → compilar. Lo enseña **antes de ejecutar nada**: COMPILAR CON ESTE PLAN · EDITAR LOS COMANDOS · CERRAR. Al compilar se guarda en el catálogo local (`build.cmd`) y a partir de ahí COMPILAR AQUÍ lo usa.
- Reglas (módulo `hub/buildplan.py`): descarta secciones de Windows/macOS/Android/consolas; si hay un bloque **Fedora** descarta Debian/Arch/etc.; traduce `apt install` → `sudo dnf install -y` con tabla de nombres (los que no conoce se avisan en el plan); `git clone --recursive` → `git submodule update --init --recursive`; ignora `git clone`, `cd <repo>`, `--version`, arrancar el juego; quita comentarios y fija `-j$JOBS`; de varias variantes del mismo `make` conserva la primera; el script para en el primer error (`set -e`). Todo se ejecuta dentro del distrobox elegido.
- **Futuro asistente**: `buildplan.PROVIDERS` es una lista de proveedores `(docs, ctx) -> plan`; hoy solo la heurística. Un proveedor con Claude Code local (`claude -p`) o un chat se añade con `register()` y entra sin tocar la interfaz (pensado para cuando la heurística no encuentra nada o la compilación falla; `ctx` ya lleva entrada, carpeta y contenedor).
- Probado contra READMEs reales (`HarbourMasters/Shipwright` docs/BUILDING.md, `n64decomp/sm64`): plan correcto. Limitaciones: instrucciones solo en wikis/imágenes, pasos que necesitan tu ROM (p. ej. generar `.o2r`), nombres de paquetes de apt sin equivalente conocido.
- Tests: `tests_pro/test_buildplan.py` (14).

## v1.69 — Tirón periódico corregido (medido en el Ally) + sonda de parones
- **Causa real** (de tu `hub.log` en modo Steam): `installed_info` se llamaba ~2400 veces en un fotograma y cada una recorría todas las tarjetas y registros (búsqueda cuadrática, con comparaciones de rutas): **50–250 ms de golpe cada vez que caducaba la caché (10 s)**, y la primera vez 170–250 ms. Ahora `install.build_index()` da el resultado en O(1) por tarjeta (mismo resultado que antes, comprobado en test contra el camino lento) y la caché caducada se **renueva en un hilo** y se cambia de golpe; mientras tanto se sigue sirviendo lo anterior.
- **Parones de 300–700 ms entre fotogramas** (`ciclo … ms entre fotogramas`) que no vienen del dibujo: con «Registrar rendimiento» activo, un muestreador anota cada 50 ms qué hace el hilo principal y, al detectar un parón > 200 ms, escribe `parón: el hilo principal estaba en …` y qué hacían los otros hilos. Así se sabrá si es un candado, el vsync de gamescope o falta de CPU.
- Tests: `test_instalados_rapido.py`, `test_perf.py` (muestreador).

## v1.70 — Primera entrada a Inicio sin tirón (segunda ronda con tu registro)
- Tu registro con v1.69 mostró que la primera entrada a Inicio seguía en ~270 ms: el coste ya no era la búsqueda cuadrática sino **crear rutas y tocar el disco por cada una de las ~2400 tarjetas** (`is_dir`/`iterdir`), **releer y parsear los ~25 `.toml` del launcher (64 ms)** y **crear las fuentes dentro del primer fotograma (~90 ms)**.
- `installed_info` usa ahora un camino rápido con cadenas y diccionarios: **una sola lectura de `~/Games`** por pasada (solo se miran en disco los juegos registrados). Mismo resultado que el camino general (test de equivalencia). Pasada completa de 2400 tarjetas: ~10 ms en el sandbox.
- `launcher_games()` guarda cada `.toml` ya parseado y solo reparsea los que cambian (fecha/tamaño).
- Al arrancar se **precalientan** las fuentes habituales y la caché de instalados (en un hilo).
- Test corregido: `test_descarga_manda_dest_dir…` fallaba suelto por una carrera (miraba la última llamada al servicio, que a veces era `job_status`).
- Pendiente de tu medición: los parones de 300–900 ms «entre fotogramas» en Ajustes/Juegos; la sonda de v1.69 ya los explicará (el último registro solo capturó uno, en Inicio, y estaba dentro de `installed_info`).

## v1.71 — Diagnóstico de las pérdidas de vídeo (los parones de 700–800 ms)
- Tu registro mostró que los parones de 719/799 ms son **pérdidas de vídeo** (`[video] PERDIDO… display_init=False`, sin error de SDL) seguidas de la reapertura de la ventana (`ventana reabierta … driver=x11`), a veces tres seguidas en una sesión, en Gamescope (`DISPLAY=:1`). El diagnóstico (`ps | grep`) y la reapertura ocurren en el hilo principal.
- Aún no se sabe **quién** cierra el vídeo. Ahora, al perderse, el registro guarda: el texto y la pila de la excepción de pygame, y si algún código de Python llamó a `pygame.display.quit()`/`pygame.quit()` (con su pila) o **ninguna** (lo cerró SDL o el servidor gráfico). El muestreador de parones guarda ahora la pila propia completa (7 niveles, sin ruido de la biblioteca estándar).
- No cambia el comportamiento: solo escribe más en `hub.log` al ocurrir. Tras reproducirlo, pasa: `grep -n "\[video\]" ~/Games/recomp-hub/data/hub.log | tail -n 30`.
- Test: `test_perf.py::test_se_anota_quien_cierra_el_video`.

## v1.72 — Pérdidas de vídeo: cada ~5 min con Hub sin tocar, menos hipo al recuperar y menos ruido en el log
- Tu `hub.log` (v1.70) mostró que **el vídeo se pierde cada ~5 minutos con Hub sin tocar** (`inactivo 251s … 371s`), siempre con la ventana reabierta al primer intento y `WindowHidden → WindowExposed → FocusGained` justo después: parece que Gamescope/el sistema oculta y devuelve la ventana tras un rato de inactividad. Hub se recupera solo, pero el primer toque tras volver cae dentro de un **parón de 700–800 ms**, que es muy probablemente el «lag» al entrar en Ajustes/Explorar. (Aún no confirmado quién cierra el vídeo: v1.71 añade ese diagnóstico.)
- **Recuperación más rápida**: el diagnóstico con `ps | grep` (~300 ms, en el hilo principal) solo se hace la **primera** pérdida de la sesión; las siguientes escriben una línea corta con `PERDIDO #n tras Ns sin tocar nada`.
- **Menos ruido**: el aviso `«x» se asocia a «y» SOLO por compartir repo…` salía cada 10 s (cada renovación de la caché); ahora una vez por sesión. La línea `caché de instalados renovada` solo sale si tarda ≥ 40 ms.
- Incluye el diagnóstico de v1.71 (qué código llamó a `display.quit`, texto y pila de la excepción de pygame).
- Tests: `test_instalados_rapido.py`, `test_perf.py`.

## v1.73 — Causa de las pérdidas de vídeo encontrada y corregida
- **Causa**: el hilo del portapapeles (`_clip_watcher`, cada segundo) llamaba a `pygame.scrap.init()` en cada lectura cuando no hay `wl-paste`/`xclip`/`xsel` (tu caso en Gamescope). Repetir `scrap.init()` desde un hilo acaba dejando SDL sin sistema de vídeo (`pygame.error: video system not initialized`, `display_init=False`, y «ninguna llamada de Python a display.quit» en tu registro v1.71). Reproducido en X11 con Xvfb: init repetido desde un hilo → vídeo perdido a los ~13 s; init una vez + `get_text()` desde el hilo → estable.
- **Arreglo**: `pygame.scrap.init()` se llama **una sola vez, en `UI.__init__` (hilo principal)**; `clipboard()`/`clipboard_full()` solo hacen `get_text()`. Sin pérdidas de vídeo no hay reapertura de ventana ni los parones de 700–800 ms.
- Probable explicación también del viejo «video system not initialized» que rompía `test_ui_flow` al crear varias interfaces en un mismo proceso (los hilos de portapapeles de las interfaces anteriores seguían llamando a `scrap.init()`); el aviso de deprecación de `scrap.init` pasó de ~150 a ~18 por ejecución de tests.
- Tests: `test_portapapeles_video.py` (comprueba que solo hay un `scrap.init()` y, con Xvfb, que el hilo del portapapeles no pierde el vídeo en X11); `test_perf.py` ajustado.

## v1.74 — Estado `waiting_interaction` (el motor espera al usuario)
- **Contrato con el daemon** (JSON-RPC, `job_status`): nuevo valor `state: "waiting_interaction"` (acepta también `"waiting"`) con `message` opcional (qué debe hacer el usuario: «resuelve el captcha», «pulsa el botón en la página»…). El resto de campos (`progress`, `phase`) se conservan. Hub lo trata como un trabajo **vivo**: sigue consultando cada 500 ms y, cuando el daemon vuelve a `running`/`completed`, se reanuda solo.
- **DESCARGAS**: la tarjeta pasa a ámbar con «Esperando tu intervención» y el mensaje del servicio; sale la primera, cuenta en la insignia de la pestaña y en el resumen («n te esperan»). **Aviso una sola vez por parada** (mensaje + sonido), otra si vuelve a pararse.
- Nota: el servicio del catálogo es JSON-RPC (`POST /rpc`, método `job_status`), no Flask; el equivalente de `GET /api/tasks/<id>/status` ya es `job_status {job_id}` → `{state, message, …}`. Hub no modifica tu `service.py`; el lado del daemon (añadir el estado a su máquina de estados y devolver `message`) lo haces tú o me pasas el archivo.
- Tests: `tests_pro/test_estado_espera.py` (6).

## v1.75 — auditoría del cliente de catálogo (huecos cerrados)
Sin tocar el daemon, `service.py`, `sites/`, `download_worker.py`, `.playwright-profile/` ni el token.
- `catalogservice.py`: `job_status`/`job_cancel` con timeout de 5 s (antes 10); `ensure_running` espera 15 s por defecto (antes 5).
- `catalogjobs.py`: un sondeo que vuela mientras cancelas ya no «resucita» el trabajo (se queda en Cancelada).
- `ui.py`: `variant_id … desconocido` en `download` → aviso y se vuelve a pedir `variants` (nunca reintenta `download` solo); log «sin hash» si el servicio no informa sha1/crc32.
- Tests nuevos: `pytest -q tests_pro/test_catalog_*.py` (estados, caída, auth, variant desconocido, sin hash, path inexistente, cancelar).

## v1.76 — robustez (revisión del orquestador)
- `catalogservice.call`/`autostart`: un `OSError`/`SubprocessError` al arrancar el daemon (permisos, intérprete inexistente) se convierte en `TransportError` («no pude arrancar el servicio…») en vez de matar el hilo.
- `catalogjobs.poll`: cualquier excepción inesperada de `job_status` cuenta como fallo (3 → error) y no mata el hilo que sondea todos los jobs.
- `ui.cat_start`: `OSError` al crear la carpeta de descargas → aviso «No pude crear la carpeta de descargas».
- `ui._cat_done`: si el `path` es una carpeta, aviso propio («devolvió una carpeta») en vez de «no existe».
- Tests: `test_catalog_robustez.py` + 1 en `test_catalog_unknown_variant.py` y ajuste en `test_catalog_path_inexistente.py`.

## v1.77 — respuestas raras del daemon y caché de instalados
- `reload()` invalida la caché de instalados y un refresco en vuelo con el catálogo viejo descarta su resultado (contador `_inst_gen`).
- `cat_open`/`cat_variants`: `result` null, tipos inesperados o `confidence` no numérica → aviso «Respuesta inesperada del servicio», sin matar el hilo.
- `gh_login_flow` (guardar sesión) y `gh_paste_token` (guardar login) capturan `OSError`.
- Tests: `test_catalog_respuestas_raras.py`.

## v1.78 — health() raro
- `cat_open`: si `health` devuelve `null`/no-lista, se ignora el estado por fuente y se sigue buscando (antes moría el hilo).
- `cat_refresh_health`: igual, sin excepciones en el log.
- `gh_paste_token`: `OSError` al guardar el token → aviso «No pude guardar el token».
- Test `test_la_cache_caducada…` más robusto (espera al prewarm de la UI).

## v1.79 — Quiver como fuente (solo lectura)
Nueva fuente de builds: la API pública de Quiver (`https://api.quiverlauncher.com/api/v1`). En la ficha de una tarjeta, **BUSCAR EN QUIVER**:
1. busca por el nombre de la tarjeta (solo apps con build de Linux);
2. eliges el resultado (nombre · proyecto · consolas · versión verificada);
3. Hub lee la última release verificada, elige el archivo de **Linux x86_64** (tar/AppImage antes que Flatpak; sin ARM ni macOS/Windows) y lo descarga con el gestor de siempre, comprobando el **SHA-256 que Quiver fijó** (aparece como «verificado» en DESCARGAS). La instalación posterior es la de siempre.
- Si el repositorio de Quiver no es el de tu tarjeta, pide confirmación. Si el archivo no trae SHA-256, lo avisa.
- `hub/quiversrc.py`: solo GET (nunca `…/check` ni `…/download-problem`), sin cuenta ni token, User-Agent propio `recomp-hub`, caché en memoria (5 min listas, 30 min fichas/releases, la API ya cachea 60 s/30 min), 0,25 s entre peticiones, IPv4 primero (tu IPv6 se colgaba en el TLS), host de respaldo del despliegue si falla el principal, y la última caché si no hay red.
- Variables: `HUB_QUIVER_API`, `HUB_QUIVER_FALLBACK`. Terminal: `python3 -m hub.quiversrc search "banjo"` / `assets SLUG`.
- Tests: `tests_pro/test_quiver_cliente.py` y `test_quiver_ui.py` (servidor falso `fakes/quiver.py`).
- Probado en tu red con `tools/quiver_probe.py`: 200 en 0,4–1 s; caché de Cloudflare `max-age=15, s-maxage=60` (listas) y `1800` (fichas/releases); sin cabeceras de límite visibles.

## v1.80 — Enlace del juego en la carpeta del proyecto + prueba real de Quiver
- Al reconocer/guardar un juego en la biblioteca (o al terminar de instalar un port con juego ya reconocido), Hub deja un **enlace simbólico a la ROM de la biblioteca en la raíz de la carpeta del proyecto**, para que el selector de archivos del port lo encuentre aunque no abra en la carpeta de la plataforma. Si el catálogo fija `requires.place` o `rom_dest`, se respeta eso y no se crea este. Nunca pisa un archivo real; reemplaza solo enlaces que apunten a otro sitio. Ajuste `link_in_project` (por defecto activo) en `settings`.
- `python3 -m hub.quiversrc check "banjo"`: prueba de punta a punta contra el Quiver real (búsqueda → ficha → release → descarga del archivo más pequeño → comparación del SHA-256). Probado desde mi entorno con Banjo Recompiled v1.0.2: SHA-256 coincide. Falta probarlo en tu red.
- Tests: `tests_pro/test_enlace_en_proyecto.py`.

## v1.81 — Actualizar Hub desde un zip + versión visible
**Por qué:** Hub no mostraba su versión, así que una actualización correcta no se notaba. Ahora Ajustes → «Versión de Hub» (y la última actualización) lo dice, y hay un sistema de actualización por zip.

**Cómo se usa**
1. Descarga `recomp-hub-update-vX.Y.zip` (lleva dentro `install-hub-vX.Y.sh`, opcionalmente `install-hub-tests-vN.sh` y `SHA256SUMS`).
2. Déjalo en `~/Games/actualizaciones` (también vale `~/Downloads`, `~/Descargas` o `~/Nextcloud/Downloads`; o un `install-hub-vX.Y.sh` suelto con ese nombre).
3. Abre Hub como siempre: `bin/hub` ejecuta antes `bin/hub-update --auto`; si hay una versión **mayor** que la instalada, la instala y reinicia con el código nuevo. O bien Ajustes → «ACTUALIZAR HUB DESDE ZIP», o en terminal `~/Games/recomp-hub/bin/hub-update`.

**Seguridad:** verifica `SHA256SUMS` si está; rechaza nombres de archivo peligrosos del zip; antes de instalar guarda el código en `data/backups/hub-<versión>-<fecha>.tgz` (últimas 3; tus datos no se tocan); tras instalar compila todo el Python y, si algo falla, **restaura solo** la versión anterior y lo anota en `data/update.json`. El zip aplicado pasa a `~/Games/actualizaciones/aplicadas/`; los tests se dejan en `~/Games/hub_test.sh` (copia `.bak`).
- Opciones: `--check` (solo dice qué haría), `--force`, `--file RUTA`, `--rollback` (vuelve a la copia anterior). Ajuste `auto_update` (Ajustes → «ACTUALIZAR SOLO AL ABRIR HUB»).
- La **primera vez** hay que instalar v1.81 a mano (`FORCE=1 bash installer.sh`); desde ahí, solo zips.
- Crear el zip: `python3 make_update_zip.py 1.81`.
- Quiver: 3 reintentos con pausa ante el error SSL intermitente «UNEXPECTED_EOF».
- Tests: `test_hub_update.py` (11) y `test_actualizar_ui.py`.

## v1.82 — Pruebas dentro de Hub
- Los tests viven en `tests/` dentro de la instalación (ya no hace falta el instalador de tests aparte).
- **Desde la interfaz:** Ajustes → Avanzado… (sección «Pruebas»): «EJECUTAR PRUEBAS DE HUB» (aparece en DESCARGAS) y «ÚLTIMO RESULTADO» (abre el informe).
- **Desde terminal:** `~/Games/recomp-hub/bin/hub-tests` (suite completa, sin descargas reales). Opciones: `-k quiver` para filtrar, `--live` para incluir el daemon de catálogo real, `--resumen` para ver el último resultado.
- Resultados en `data/tests/resumen.txt` e `informe.md` (fallos al principio). Usa el Python de Hub; si falta pytest, avisa con el comando de instalación.
- Verificado: instalación limpia de 1.82 y suite completa dentro de ella: 436 pasados, 14 omitidos.

## v1.87 — Rediseño completo (etapas 1.83–1.87 juntas)
- **Actualizar desde la interfaz:** al abrir Hub (o cada pocos minutos) busca un zip mayor en `~/Games/actualizaciones`. Si lo hay, sale un aviso arriba y basta pulsar/Tab+A para instalar y reiniciar. También en Ajustes → Hub.
- **Temas:** Oscuro, Claro y Cristal; efectos «Cristal (blur precalculado)» o «Rendimiento» (fondo plano, sin blur) para compararlos con los tests de rendimiento. Ajustes → Aspecto.
- **Ficha del juego en 3 pasos** (archivo del juego → obtener el port/release → jugar). Modo local/servidor. Compilar/adaptar a Linux y demás quedan en «Más opciones».
- **Diccionario proyecto → juego** (`catalog/games.json`, ~40 entradas; tu propio `data/games.local.json` lo amplía): buscar «ocarina» o «soh» encuentra Shipwright.
- **Ajustes:** solo lo esencial (Aspecto, Descargas, Mis juegos, Hub, Sonido) + **AVANZADO** plegable con todo lo ocasional: añadir proyectos y buscar en GitHub (movido desde Explorar), importar catálogos, sesión GitHub, compilar, imágenes, Steam, navegador, papelera, pruebas, registro.
- **Biblioteca:** las carpetas que ES-DE no reconoce se marcan «· sin clasificar» (siguen siendo navegables).
- **Carátulas:** Avanzado → «DESCARGAR CARÁTULAS FALTANTES»: una sola pasada por SteamGridDB (clave existente), guardadas en `data/covers/<id>.*`; no se repite lo ya bajado. Se usan si el juego no tiene arte propio en `art/`.
- **Registro de compilaciones:** cada compilación (bien o mal) se anota en `data/buildlog.jsonl`; Avanzado → «COMPILACIONES REGISTRADAS» muestra herramientas, contenedores, hilos y errores más frecuentes.
- **Doctor:** `bin/hub-doctor [--no-net]` o Avanzado → «DOCTOR». Comprueba DISPLAY/XAUTHORITY, espacio en disco, launcher, TLS por IPv4 a GitHub, `.toml` con el mismo `install_dir` e instaladores `*-setup*` sueltos.
- **No hecho:** menú con cruceta/Guía dentro del juego (Hub se cierra al jugar); Quiver como fuente de carátulas sigue siendo solo experimento; tema claro es primera pasada.
- Tests: `tests_pro/test_v183_etapas.py`.

## v1.88 — Tema «Quiver» + pruebas de interfaz más duras
- **Nuevo tema «Quiver»** (Ajustes → Aspecto, el botón de tema ahora recorre Oscuro → Claro → Quiver): copia el aspecto del render de Quiver Launcher que enviaste — fondo casi negro azulado, botones y filas **solo con contorno**, esquinas más cuadradas, foco azul claro, plano (sin blur ni sombras, por lo que es el más barato de dibujar). Primera pasada: los fondos de portadas y menús siguen la paleta, pero el detalle fino (iconos, chips) puede pedir retoques.
- **Corregido:** el degradado «Más abajo» se quedaba oscuro al pasar al tema claro.
- **Pruebas** `tests_pro/test_temas_y_fuzz.py` (22): contraste mínimo de la paleta de cada tema (falla si el texto sobre el botón primario es ilegible), renderiza 16 pantallas/menús × 3 temas × 2 efectos comprobando que no están vacías, que ningún widget se sale por los lados y que su texto es visible; cambio de tema en caliente en cada pantalla; fuzz con ~700 pulsaciones de mando por tema buscando excepciones y focos perdidos (con subprocesos, navegador y reinicio simulados); pulsa una vez cada botón de cada pantalla. Capturas en `data/tests/capturas/temas/` (o `tests_pro/reports/capturas/temas`).
- `hub-tests`: el informe ya no incluye las líneas `[match]`/`[foco]` de tu biblioteca real.

## v1.90 — Navegador de MiniTube (retirado en v2.11), cookies de GitHub y tema «Prototipo»
- **Navegador = el de MiniTube (ytmini v50).** MiniTube ganó dos órdenes: `launcher.sh url <https://…>` (abre cualquier web en la misma vista táctil de Steam que usa YouTube, con `NavigateToExternalWeb`) y `launcher.sh cookies <archivo.json>` (carga cookies de github.com en el navegador de Steam). Hub las usa para **todo** «abrir navegador»: modo `minitube` o, en AUTOMÁTICO, si MiniTube v50+ está en `~/Games/{steam-ytmini,miniTube,minitube,ytmini}` (o `minitube_dir` / `HUB_MINITUBE`) y Steam está en Big Picture (CEF :8080). Si falla (Steam sin Big Picture, MiniTube antigua…) cae al navegador de siempre y lo dice. Ajustes → Avanzado → «MINITUBE» muestra si la encuentra.
- **Cookies de GitHub:** Avanzado → «GITHUB: IMPORTAR COOKIES (.json de Cookie-Editor)». Se filtran a las esenciales (`user_session`, `__Host-user_session_same_site`, `logged_in`, `dotcom_user`, `_device_id`, `saved_user_sessions`, `_gh_sess`; solo dominios github.com), se guardan en `data/github-cookies.json` y como `GITHUB_COOKIES=…` en el `.env` del launcher, ambos **0600**, y se cargan en el navegador de Steam. «BORRAR COOKIES» las quita. Nunca se imprimen valores.
- **Inicio:** «Sesión de GitHub» (con cookies guardadas las carga y abre github.com ya dentro; sin ellas abre el login) y «Abrir un proyecto en GitHub» (owner/repo o URL).
- **Tema «Prototipo»** (Ajustes → Aspecto; el botón de tema recorre Oscuro → Claro → Quiver → Prototipo): el render que enviaste — barra lateral con iconos (Inicio, Explorar, Descargas, Ajustes, con insignia de descargas), acento naranja con texto oscuro, héroe «Continuar · hace 2 h» con el último juego jugado y botón Jugar, «Mis juegos» en tarjetas verticales con insignia de plataforma y ✓/↑. El resto de pantallas se desplazan a la derecha de la barra. Mando: IZQUIERDA desde el contenido llega a la barra. Plano (sin blur).
- Los textos sobre botones/fichas de color se eligen por luminancia (`on_color`), así que el naranja lleva letra oscura y el rojo/verde/azul letra blanca.
- Pruebas: `test_minitube_cookies.py` (10) y `test_temas_y_fuzz.py` ampliado a 4 temas + barra lateral (30).

## v1.91 — Prototipo más grande, glifos sin cuadrados, límite de GitHub y logos de consola
- **Prototipo ×1,25:** el tema agranda toda la interfaz (letra, barra lateral de ~130 px, tarjetas, héroe) para el panel del Ally. Es el ajuste `SCALE` del tema; Oscuro/Claro/Quiver no cambian.
- **Sin cuadrados:** si la fuente del sistema no trae un carácter (✓ ↑ ▶ ‹ › · — …) Hub lo cambia por un equivalente ASCII antes de dibujarlo (`UI.sane`). El círculo verde de las tarjetas y el «▶ Jugar» ahora se dibujan con formas, no con texto.
- **Límite de GitHub — qué pasaba:** pulsar X en Inicio/Explorar («Actualizaciones») comprobaba **todas** las fichas del catálogo (~1100 llamadas, ignorando la caché) y se comía las 5000/h aun con sesión.
  Ahora solo consulta lo **instalado**, una vez por repositorio, con `If-None-Match` (ETag: una respuesta 304 no gasta cuota) y se **para** si GitHub devuelve límite (cortacircuitos hasta que pase).
  `ghstats` cuenta las llamadas (con/sin sesión, nuevas, 304, errores) y separa los 403: **cuota agotada** (X-RateLimit-Remaining=0), **límite secundario** (Retry-After) y **otro 403**.
  Ajustes → Avanzado → «GITHUB: COMPROBAR SESIÓN Y LÍMITES» ahora muestra además cuántas llamadas ha hecho Hub. En `bin/hub` el log `[gh] …` indica tipo, sesión sí/no y cuota restante.
- **Logos de consola:** `assets/platform-logos/` (246 PNG de PRO100BYTE/console-logos, 1,4 MB, ya recortados; viene en el instalador, sin red ni cuota). Salen en las fichas de Explorar y como insignia de las tarjetas del Inicio del Prototipo (sobre placa clara). 145 de 172 sistemas de ES-DE tienen logo; los demás siguen con texto.
- **Pruebas** `tests_pro/test_v191.py` (16): token enviado, 304, tipos de 403, cortacircuitos, solo instalados, glifos (simula una fuente sin ✓↑▶‹›), logos y **descripción en texto de cada pantalla** a 1280×720 y 1920×1080 (botones en mm, letra mínima, textos que se pisan, glifos ausentes, dibujo ASCII). Todo sale en `data/tests/informe.md` → «Cómo se ve».
- **No hecho:** el interruptor «En mi equipo / En mi servidor» y la fila de plataformas del Inicio del prototipo; verificar en el Ally real el tamaño percibido.

## v1.92 — Pulido: rectángulos, cruceta, Ajustes, Descargas, Explorar, iconos y registros de arranque
- **Rectángulos en el texto** (p. ej. «Castlevania 64 · recompilación estática»): venían de caracteres invisibles de las descripciones de GitHub (unión de emoji, selector de variación, espacios y guion «duros») que algunas fuentes dibujan como cuadro. `UI.sane` los quita/sustituye antes de dibujar, y ahora también exige que la fuente dé avance al glifo.
- **Ficha con la cruceta:** ahora recorre por filas (Atrás → Biblioteca → Elegir archivo → Instalar/Jugar → Más opciones) y vuelve por el mismo camino; antes se saltaba los botones de la derecha. Cambio general (`UI.nav`: primero la fila/columna más cercana y dentro de ella la más alineada). Test: desde el primer botón de CADA pantalla se llega a todos los demás con la cruceta.
- **Rendimiento en Ajustes:** las filas fuera de pantalla se registran (la cruceta las alcanza) pero no se dibujan; el recorte de textos (`fit`) y la limpieza de glifos (`sane`) se cachean; y Ajustes baja a 20 fps cuando llevas 1 s sin tocar nada (45 fps en el resto).
- **Descargas:** misma cabecera y márgenes que Explorar, botones abajo sin pisar el texto (tarjetas más altas). Test de solapes a 1280×720 y 1920×1080 con 4 descargas.
- **Explorar:** cada juego de la lista lleva su **miniatura** (carátula del juego o de SteamGridDB; mientras no hay, un bloque de color con el logo de su consola). Se cargan en hilos de 3 en 3 y se guardan como máximo 420 en memoria. Las tarjetas entran deslizándose de forma escalonada. En el Inicio, las tarjetas verticales prefieren arte vertical (portrait/grid) y el héroe el apaisado.
- **Iconos de Lucide** (lucide-icons/lucide, ISC) para la barra lateral (casa, brújula, descarga, engranaje): `assets/icons/*.png`, teñidos y escalados bajo demanda (`hub/icons.py`). Hay también play, check, search, gamepad…
- **Registros de arranque fallido:** la salida del lanzador y del juego ya no va a /dev/null: `data/launch-logs/<id>-<fecha>.out`. Si el lanzador termina enseguida se escribe `<id>-<fecha>.md` con código de salida, cola de la salida, log del launcher, su `.toml`, si el binario existe/es ejecutable y las bibliotecas que faltan (`ldd`), sesión gráfica y versión. Un arranque que murió después de cerrarse Hub se detecta al abrir Hub la siguiente vez.
  En la **ficha** sale «Ver registro del último arranque fallido»; en Ajustes → Avanzado «REGISTROS DE ARRANQUE… PREPARAR PARA ENVIAR» junta los últimos 8 en `data/launch-logs/ENVIAR.md`, lo copia al portapapeles y lo muestra; por terminal: `bin/hub-logs` (lo imprime). Solo guarda los 30 más recientes. No incluye tokens ni cookies.
- **Informe de pruebas:** `data/tests/informe.md` ahora incluye los omitidos con su motivo y la sección «Cómo se ve» (botones en mm, letra mínima, solapes, glifos, dibujo ASCII), sin el ruido de advertencias.
- **Cruceta en listas grandes:** IZQUIERDA/DERECHA prefieren lo que está en la misma fila (antes, en la última columna, IZQUIERDA saltaba a una pestaña) y dos fichas con el mismo id ya no comparten foco. Probado con 1250 fichas e ids repetidos.
- Pruebas: `tests_pro/test_v192.py` (16).
- **No hecho:** interruptor «En mi equipo / En mi servidor» y fila de plataformas del Inicio; probar en el Ally real el rendimiento de Ajustes y la nitidez de los iconos.

## v1.93 — Pruebas sin el mando real, Inicio completo del Prototipo, aviso de bibliotecas y ui.py por partes
- **Los 2 fallos de `bin/hub-tests` en el Ally** (`…heroe_y_tarjetas` y `…baja_los_fps_en_reposo`): Hub lee el mando directo de `/dev/input`, y las pruebas también lo hacían. Tocar el Ally (o la deriva del stick) mientras corrían abría un menú (`ch:0…`) o mantenía los 45 fps. Ahora las pruebas arrancan Hub con `HUB_NO_PAD=1` (ni evdev ni SDL). Además, cada prueba de interfaz espera a que terminen los hilos que lanzó antes de pasar a la siguiente, y si vuelve a fallar dice qué modal estaba abierto.
- **Inicio del Prototipo:** arriba a la derecha «Tus archivos: En mi equipo / En mi servidor» (el mismo ajuste que la ficha: dónde se busca tu copia del juego). Debajo del héroe, la **fila de plataformas** con los logos de las consolas de tu catálogo: primero donde tienes juegos, solo las que caben. Al tocar una se abre Explorar filtrado por esa consola.
- **Cruceta:** arriba/abajo ya no salta a algo que está al lado (la barra lateral junto al héroe), y las pestañas y el contenido son dos columnas: desde el héroe ARRIBA va al interruptor y ABAJO a las plataformas; desde las plataformas ABAJO va a «Mis juegos». Sigue probado que se llega a todos los botones de cada pantalla.
- **Bibliotecas que faltan, antes de lanzar:** al pulsar JUGAR, Hub mira con `ldd` el ejecutable del `.toml`. Descuenta lo que el port trae en su carpeta, `lib/`, `lib64/` o `libs/`. Si falta algo (p. ej. `libjpeg.so.8` en Silent Hill) avisa: «Faltan bibliotecas del sistema… así no arrancará», con LANZAR DE TODOS MODOS o CANCELAR. La ficha muestra el mismo aviso en rojo. El resultado de `ldd` se guarda y solo se repite si cambia el binario.
  Arreglado también el informe de arranque fallido: buscaba `exec=` en el `.toml`, pero Hub escribe `[run] exe = …`, así que nunca comprobaba el binario ni `ldd` en los juegos instalados por Hub.
- **`bin/hub-archivo <archivo> [parte del nombre]`:** diagnóstico de un zip/7z/rar/chd sin tocar nada. Muestra tipo, herramientas (7z, chdman…), espacio libre, carpetas de ROMs, lo que pide el catálogo y qué extraería Hub. Con `--extraer` hace lo mismo que Hub y lo compara.
- **`ui.py` por partes:** pasa de 5 944 a ~4 350 líneas. Inicio (`ui_home.py`), Explorar (`ui_explore.py`), Descargas, Ajustes, Ficha, Modales y Archivos del juego van en archivos propios. Siguen siendo la misma clase `UI` (mixins) y usan los mismos nombres globales que `ui.py`, así que el tema y las pruebas se comportan igual.
- Pruebas: `tests_pro/test_v193.py` (11).
- **No hecho:** agrandar los botones de menos de 7 mm; probar en el Ally real el Inicio del Prototipo, el aviso de bibliotecas con Silent Hill y las pruebas sin `HUB_NO_PAD`.

## v1.94 — Plataforma correcta y aviso de bibliotecas sin falsos positivos
- **«PC» en vez de PSP** (p. ej. GTA: Liberty City Stories): en algunas listas importadas (Quiver, RecompLauncher…), «plataforma» es dónde *corre* el port (PC/Windows/Linux), y al fusionar pisaba la consola que ya tenía la ficha. Ahora una plataforma de ese tipo nunca sustituye a una consola; una consola sí puede corregir a otra. Si una ficha solo trae «PC/Windows», Hub deduce la consola por palabras sueltas del nombre, el repo, la carpeta, las etiquetas o las notas («psp», «ps2», «n64»…), y solo si hay una única pista.
- **Bibliotecas, sin avisos falsos:**
  - `ldd` usa el `LD_LIBRARY_PATH` de `[run.env]` del `.toml`, como el launcher.
  - Si el juego se compiló en un distrobox (`build_in = ["distrobox", "enter", "fedora", …]`), el aviso lo dice: «se compiló dentro del distrobox «fedora» y el launcher lo abre en el sistema».
  - **LANZAR DE TODOS MODOS** ya no vuelve a preguntar por ese juego (se guarda en `libs_ok`).
  - Si un juego con aviso arranca bien, Hub aprende solo que era un falso positivo. La ficha deja de mostrar el aviso en ambos casos.
- Pruebas: `tests_pro/test_v194.py` (5).
- **No verificado en el Ally:** si GTA LCS arranca con el binario compilado en fedora (eso decide si el aviso era cierto o falso).

## v1.95 — Versión de Windows (Proton) junto a la de Linux, elegible por juego
- **Por qué:** algunos ports publican build de Linux y de Windows, y el de Linux puede fallar. Silent Hill (SlickAmogus/silent-hill-decomp): el nativo se cierra con SIGSEGV y su README recomienda Wine en Linux.
- **En la ficha** (juego instalado, si la release trae un zip/7z de Windows x64): «Versión que abren JUGAR y Steam: LINUX (NATIVO) / WINDOWS (PROTON)».
  - La primera vez, WINDOWS · DESCARGAR explica lo que va a pasar y pide confirmación. Luego descarga el build de Windows y reorganiza la carpeta del juego:
    `<juego>/linux/` (lo que ya tenías, movido con renombrados en el mismo disco y con diario: si algo falla se deshace), `<juego>/windows/` y `<juego>/proton-prefix/` (el «C:» de Proton de ese juego, donde quedan sus partidas de Windows).
  - Después cambias entre las dos con un toque.
- **Cómo se aplica:** Hub reescribe el `games/<id>.toml` del launcher: `install_dir` (linux/ o windows/), `[run] exe` y `[update] asset` (`*linux-x64*.tar.gz` ↔ `*windows-x64*.zip`), y guarda una copia `.toml.hub-bak`. Así JUGAR y el acceso de Steam (`shortcuts/<id>.sh` → `bin/play <id>`) abren siempre la versión elegida, y el launcher sigue actualizando esa versión.
- **La versión de Windows** se abre con `windows/hub-run.sh`, que Hub genera y puedes editar: `umu-run` con el GE-Proton más reciente de `compatibilitytools.d` (si no hay, `GE-Proton`, que umu descarga) y `WINEPREFIX=<juego>/proton-prefix`. Hub elige el `.exe` del juego, no instaladores, `vc_redist` ni lanzadores de errores. Los archivos que exige el port (`require`) se enlazan desde linux/, sin copiarlos.
- **Juegos que solo publican Windows:** «INSTALAR (WINDOWS · PROTON)» los instala directamente en `<juego>/windows`.
- `osver.unsplit` deshace la reorganización si solo hay versión de Linux.
- **Partidas:** no se sincronizan entre versiones. Las de Linux siguen donde estaban (dentro de linux/ o en `~/.local/share`) y las de Windows quedan en `proton-prefix`.
- Pruebas: `tests_pro/test_v195.py` (7). También va aquí el arreglo del indexador («PS1 / PSP / Saturn» ya no pone siempre «PlayStation») y la prueba del degradado sin inercia de la anterior.
- **No verificado en el Ally:** que el launcher actualice bien `windows/` con su `github-archive` (la estructura del zip), el primer arranque de Proton (crea el prefijo y tarda) con el `grace_seconds = 10` del launcher, y Silent Hill de Windows de verdad.

## v1.96 — Juegos con su propia ficha en Big Picture, carpeta de trabajo correcta y pruebas de calidad
- **JUGAR abre el juego con su acceso de Steam.** Antes, en Big Picture (selector de ventanas, overlay) el juego salía como «Recomp Hub»: Steam agrupa todo lo que lanza una app no-Steam bajo esa app.
  Ahora, si Hub corre dentro de Steam y el juego tiene acceso propio en Steam (`shortcuts.vdf`: el de `shortcuts/<id>.sh`, `bin/play <id>` o el mismo nombre), Hub le pide a Steam `steam://rungameid/<id>` y se cierra. Steam abre entonces el juego como su propia app, con su nombre y arte.
  La petición sale 2 s después desde `systemd-run --user`, fuera del árbol de procesos de Hub, para que Steam no la cuente como parte de Hub.
  La ficha dice cuál se va a usar; si no hay acceso, avisa («se verá como Recomp Hub»). Ajustes: «AL PULSAR JUGAR: ABRIR CON EL ACCESO DE STEAM DEL JUEGO / HUB LO ABRE DIRECTAMENTE».
- **Carpeta de trabajo = carpeta del juego.** Silent Hill olvidaba su configuración por un ajuste de **Hub**: al reconocer tu archivo, cambiaba `[run] cwd` a tu carpeta de ROMs (para que el selector de archivos del juego empezara allí), y el juego guardaba su `config.cfg` en esa carpeta.
  Ese ajuste (`auto_libcwd`) queda apagado. Al abrir esta versión, Hub restaura una vez el `cwd` original de los juegos donde lo cambió y deja enlazada tu ROM dentro de la carpeta del juego (`.cue` junto con su `.bin`).
  La versión de Windows también recibe esos enlaces. Activarlo a mano en «Más opciones» sigue siendo posible, con aviso.
- **La ficha dice dónde está cada cosa:** carpeta del juego (la de la versión elegida), carpeta de trabajo (en amarillo si es distinta) y tu archivo.
- **Pruebas nuevas en `test_calidad.py`:**
  - Milisegundos por fotograma de cada pantalla (Prototipo y Oscuro), medidos en el equipo donde corren. Van a «Rendimiento» del informe, marcando lo que pase de 22 ms; falla si alguna supera 250 ms.
  - Todos los textos reales de tus listas importadas y tu catálogo local, pasados por la limpieza de glifos: avisa si alguno saldría como rectángulo con tu fuente.
- La píldora «Más abajo» ya no cuenta como «texto que se pisa».
- **No verificado en el Ally:** que Steam abra el acceso tras cerrarse Hub (el retraso de 2 s y systemd-run) y qué hace Silent Hill sin el `cwd` en la carpeta de ROMs (si busca la ROM en otra subcarpeta, hay que fijar `requires.place` en su ficha).

## v1.97 — Tu archivo donde lo pide el README del port
- **Por qué:** muchos ports dicen en su README dónde quieren tu archivo: «Place your disc image in the `gamedata/` folder», «Put EBOOT.ELF and PSP_GAME in `lcs/game/`», «Copy baserom.us.z64 into the root». Hasta ahora Hub solo dejaba el enlace en la raíz de la carpeta del juego.
- **Lectura del README:** al abrir la ficha de un juego instalado con tu archivo ya reconocido, Hub lee su README una vez por sesión. Si nombra **una sola** carpeta clara, la guarda en la ficha (`requires.place`, marcada «según su README») y enlaza ahí tu archivo, con el `.bin` de un `.cue`. Siempre dentro de la carpeta de la versión elegida (linux/ o windows/), nunca fuera.
  - Si el README nombra varias carpetas, o el catálogo ya fija una carpeta externa (`rom_dest`), no adivina.
  - «LEER DATOS DEL README» hace lo mismo a mano.
  - Solo cuentan frases que hablan del archivo del juego. Se descartan rutas absolutas, URLs y nombres de archivo («copy X to `baserom.us.z64`»).
- **La ficha dice dónde lo enlaza:** «Lo enlaza en: …/linux/gamedata/ (según su README)» o la carpeta fija que pide el port.
- Pruebas: `tests_pro/test_v197.py` (12, con frases reales en inglés y en español).

## v1.98 — Modo de energía (TDP) y pruebas comparables entre TDP
- **Modo de energía** (Ajustes → «MODO DE ENERGÍA»):
  - **AUTOMÁTICO** (por defecto): pasa a ahorro con TDP ≤ 9 W o con la batería por debajo del 25 % y desenchufado.
  - **AHORRO**: 30 fps, 15 fps tras 3 s sin tocar nada (en cualquier pantalla), Ajustes a 15 fps en reposo y sin animaciones de entrada.
  - **RENDIMIENTO**: 45 fps siempre (Ajustes sigue bajando a 20 en reposo).
- **De dónde sale el TDP:** Hub lo lee de `/sys` sin permisos, tal como lo deje tu plugin de TDP (Decky, hhd o tu QAM):
  - `asus-armoury ppt_pl1_spl`, `asus-nb-wmi ppt_pl1_spl` o el `power1_cap` de amdgpu;
  - la batería de `power_supply/BAT*`;
  - el consumo de `power1_average`, y la frecuencia y el perfil de la CPU.
  - Se relee cada 10 s.
- **Pruebas:** «Rendimiento» del informe anota la energía del momento («TDP 7 W · batería 80 % descargando · …») y si Hub estaría en ahorro.
  Cada medición se guarda en `data/tests/rendimiento.jsonl`. Con mediciones a TDP distintos, el informe añade una tabla comparando el p95 de cada pantalla con el último resultado de cada TDP.
  Para el resto de pruebas el TDP real no cuenta (`HUB_SYSFS` aislado), así no cambian según el TDP.
- Pruebas: `test_calidad.py` +2 (lectura de TDP/batería con un /sys falso; fps y animaciones en ahorro).

## v1.99 — Prueba de rendimiento por TDP con Panel de Control
- **TDP de tu Ally:** Hub lo lee de `asus-armoury ppt_pl1_spl` (13 W en tu equipo), el primer sitio que prueba.
- **Prueba por TDP** (solo si la pides: `HUB_TDP_BENCH=auto bin/hub-tests`, o `HUB_TDP_BENCH=7,10,13` para elegir los vatios). Para cada nivel:
  - Hub le pide el TDP a **Panel de Control** (`set_tdp_watts`, alcance global) y espera 4,5 s a que se aplique.
  - Lee el TDP aplicado y mide el p95 de cada pantalla, la velocidad de CPU en un hilo (SHA-256 por segundo) y el consumo.
  - Al terminar **devuelve el TDP que había**. Si no puede, lo avisa en el informe para que lo pongas a mano.
  - Con `auto`, los niveles van con peso en los bajos (mínimo, mínimo+2, mínimo+4, medio y máximo), igual que la prueba de fluidez de QAM Rail.
  - El informe saca «Rendimiento por TDP» con una fila por nivel, y cada medición se suma al historial `data/tests/rendimiento.jsonl`.
- **Cómo habla con Panel de Control:** igual que QAM Rail, llama a sus métodos ya existentes (`get_tdp_state`, `set_tdp_watts`, `get_power_draw`) a través de Decky, sin copiar su código.
  Desde fuera de Steam entra por el depurador de CEF que Decky deja abierto en `127.0.0.1:8080` y ejecuta la llamada en `SharedJSContext`, donde viven los plugins. Es un cliente WebSocket propio, solo local (`hub/tdpctl.py`).
- Pruebas: `test_tdp_bench.py`: el cliente contra un Steam falso (lista de páginas, WebSocket, `Runtime.evaluate`), el error sin Steam, los niveles y la prueba real (omitida salvo que la pidas).
- **No verificado en el Ally:** que la vía de Decky responda desde fuera del panel. QAM Rail prueba tres vías y aquí se prueban las mismas.

## v2.0 — Ajustes por categorías y «Más opciones» por bloques
- **Ajustes** abre con 7 categorías, cada una con una línea que dice qué contiene: Aspecto y control, Al jugar, Mis juegos y archivos, Catálogo, GitHub y navegador, Compilar y Mantenimiento.
  - Dentro de cada una, cada opción lleva también una línea que explica qué hace («Con su acceso, Big Picture muestra el juego con su nombre y arte…», «Cerrar Hub libera memoria y batería…», «Bájala si el navegador se queda en negro…»).
  - «‹ Ajustes» o **B** vuelven a las categorías con el foco donde estabas.
  - «Todos los ajustes (lista completa)» lo enseña todo seguido, agrupado por categoría, por si no encuentras algo.
  - Si hay una actualización de Hub esperando, sale arriba del todo.
  - Nombres más claros: «Cómo se abre el juego: con su acceso de Steam / desde Hub», «Hub al empezar a jugar: se cierra / se queda abierto», «Al reconocer tu archivo…».
- **Ficha → Más opciones**, en este orden:
  1. **Tu archivo del juego** (lo más usado).
  2. **Repositorio**.
  3. **Versión**.
  4. **Partidas y configuración**: dónde guarda el juego sus partidas y **dónde arranca**. El antiguo «Selector en mi biblioteca» ahora dice qué hace: «Que arranque en tu carpeta de ROMs» / «Que arranque en su carpeta (recomendado)», con el aviso de que el juego guardará allí su configuración.
  5. **Steam y arte**.
  6. **Compilar**.
  7. **Portar con IA**.
  8. **Borrar**.
- Pruebas: `tests_pro/test_v200.py` (5): entrar y volver con B en los dos temas, que ninguna opción de antes se haya perdido, la lista completa, y el orden y los textos de los bloques de la ficha.

## v2.01 — Cruceta sin repeticiones fantasma, Ajustes fluido, prueba de navegación y God of War de PS4
- **Movimientos «al azar» de la cruceta** (sobre todo al entrar en una consola de Explorar): Hub lee el mando por dos vías, SDL y directamente `/dev/input` (evdev). La vía evdev solo avisaba al **pulsar**, nunca al **soltar**.
  Si su aviso llegaba justo después del «soltar» de SDL (un fotograma pesado, como al abrir una lista de 1 000 juegos, basta para cambiar el orden), la dirección se quedaba «pulsada» y se repetía sola cada 0,11 s hasta que tocabas otra cosa.
  Ahora evdev también avisa al soltar (botones y cruceta), y ninguna dirección puede seguir «pulsada» más de 6 s.
- **Ajustes «a tirones» al desplazarse:** Ajustes baja a 20 fps tras 1 s sin tocar nada, pero las pulsaciones del mando por evdev no contaban como actividad, así que con la cruceta casi siempre iba a 20 fps. Ahora cuentan.
  Además, Hub no baja de fps mientras algo se desplaza (inercia, arrastre o el nuevo desplazamiento suave).
- **Desplazamiento suave:** al bajar con la cruceta, la lista se desliza hacia el foco en ~0,15 s en vez de saltar. Los saltos largos (y el modo ahorro) siguen siendo directos.
- **Prueba de navegación** (como la de fluidez de QAM Rail): recorre con la cruceta secciones (RB), categorías de Ajustes (A/B), la lista completa de Ajustes (25 abajo y 10 arriba), una consola de Explorar, su lista, una ficha y vuelta.
  Mide lo que tarda cada pulsación en dibujarse y cuántos fotogramas tarda en asentarse el desplazamiento. Sale en el informe («Navegación con la cruceta») en los dos temas.
- **Prueba por TDP, ampliada:**
  - aviso «no toques el Ally» con cuenta atrás;
  - CPU con **todos los núcleos** (ahí sí se nota el límite de potencia);
  - la navegación con la cruceta en cada nivel;
  - lo que respondió Panel de Control (ok, aplicado, detalle, `get_power_draw`). En tu primera prueba el TDP de sysfs se quedó en 13 W en los tres niveles: con esto sabremos si Panel no lo aplicó o si lo aplica por otra vía (ryzenadj) que no se refleja ahí.
- **God of War III (SpartanPort) es God of War III Remastered de PS4**, no de PS1. El adivinador de plataforma ahora conoce PS4 y PS5.
- Pruebas: `test_v201.py` (5) y `test_calidad.py` (navegación, 2).

## v2.02 — Descargas con peso y velocidad, zona de descargas nueva y todo a tamaño táctil

**Descargas.**
- El peso y lo que falta salen siempre que se puedan saber: «40 % · 3 MB/s · quedan 2 min», debajo «320 MB de 800 MB · faltan 480 MB». Si el tamaño total aún no se sabe, lo dice y muestra lo descargado.
- Si el servicio del catálogo manda la velocidad a 0 (es su fallo: calcula `bps` después de actualizar `last_size`, así que la diferencia siempre es 0), Hub la calcula él mismo con lo descargado entre consultas, suavizada. El tamaño también se acepta como texto («3.2 GB») o como `total_bytes`/`downloaded`.
- Descargas del navegador: la velocidad es la media de los últimos ~3 s (ya no cae a 0 entre lecturas) y aparece desde la segunda lectura.
- La pantalla se divide en **En curso** y **Terminadas**. Los botones de cada tarjeta y los de arriba (AÑADIR POR URL, LIMPIAR TERMINADAS) son más grandes.

**Todos los temas a las medidas del prototipo.** Oscuro, claro y el resto usan la misma escala (1,25) y una barra de pestañas más alta.

**Ningún botón por debajo de 7 mm** en ninguna pantalla (biblioteca, buscar, lista, ficha y «Más opciones», selector de archivos, teclado, confirmaciones), en 1280×720 y 1920×1080.

**Pruebas nuevas (`test_v202.py`):**
- velocidad calculada cuando el servicio da 0, tamaño como texto, media del navegador;
- secciones y textos de peso en Descargas;
- medidas táctiles y botones que se pisan en todas las pantallas de cada tema; el informe incluye una tabla con el botón más pequeño por pantalla.

**Corrección de v2.01:** la prueba de rendimiento por TDP se ejecutaba aunque no la pidieras (el «solo si HUB_TDP_BENCH» había quedado en otra función) y fallaba si Steam no estaba abierto. Ahora solo corre con `HUB_TDP_BENCH=…`.

## v2.03 — Batería de pruebas que da lo mismo en tu Ally y aquí, y prueba de TDP que mide de verdad

**Prueba de TDP corregida.** Panel de Control aplica el perfil del contexto que está delante. Hub tiene el suyo (`ns:hub`), así que escribir el TDP global no cambiaba nada: por eso la tabla de v1.99–v2.02 salía siempre con el mismo límite. Ahora:
- Hub escribe su propio perfil (`scope: game`, `ns:hub`). Comprobado en tu Ally: 30 → 7 W en el firmware.
- Al terminar devuelve ese perfil al valor que tenía.
- Si el límite que lee el firmware no coincide con lo pedido (±1 W), la prueba falla y dice qué nivel no se aplicó, en vez de dar una tabla que no mide nada.

**Las pruebas ya no tocan tu carpeta personal.** Usan una casa temporal: no leen tus ROMs, tus Descargas ni tus accesos de Steam, y no escriben en tu `~/.config`. La biblioteca de prueba es siempre la misma (150 juegos en 3 plataformas), así que el resultado no depende de lo que tengas.

**`bin/hub-tests` busca solo un Python que sirva** (3.11 o más, con pygame y pytest): primero el de tu terminal; si no vale, el de miniforge/conda y sus entornos, `/usr/bin/python3`… Si ninguno sirve, dice qué le falta a cada uno y el comando para arreglarlo. Para forzar uno: `HUB_TESTS_PYTHON=/ruta/python3 bin/hub-tests`. El informe dice con qué Python se ejecutó.

**Un archivo de pruebas roto ya no corta la batería:** sale como error y el resto se ejecuta.

**Botones:** «MOSTRAR MÁS» de Biblioteca (6 mm) pasa a tamaño táctil, y el teclado en pantalla gana margen. La variante con el teclado de Steam (la que sale en Modo Juego) tenía sus botones a 7,0 mm: era el «modal_teclado 7,0 mm» de tu informe; ahora también se mide en las pruebas. La prueba de tamaños exige ahora 7,2 mm, para que unas décimas de diferencia entre equipos no la tumben.

**Guardas nuevas (`test_v203.py`):**
- ninguna prueba cambia el TDP sin su `skipif` (lo que falló en v2.01);
- la prueba de TDP escribe el perfil de Hub, no el global;
- las pruebas usan la casa temporal y la biblioteca de prueba;
- `hub-tests` rechaza Python viejo o sin pygame y explica cómo arreglarlo;
- cada prueba deja **toda** la configuración como estaba (antes era una lista a mano y se colaban cambios del fuzz, como el tipo de teclado); y las pruebas ignoran que se lancen desde Modo Juego.

## v2.04 — God of War (PS2) del port PC en el catálogo, con actualización por compilación local

Nueva ficha **«God of War (PS2 · port PC)»** (`danielalves96/gow-pc-port`), con el mismo flujo que Liberty City Stories:
- **Compilar aquí** clona el repo en `~/Games/gow-ps2`, ejecuta `./install.sh --compiler g++ --jobs N` (el compilador con el que te compiló bien) dentro de tu distrobox y registra el juego en el launcher como `git-build`.
- Al abrir el juego, el launcher hace `git fetch`; si hay cambios, avanza el repo y vuelve a ejecutar `install.sh`, que solo recompila lo que cambió (un cambio en headers generados o en un `CMakeLists.txt` obliga a recompilar todo).
- **JUGAR** ejecuta el `run_gow.sh` del repo. No fija Wayland ni `XDG_RUNTIME_DIR`: eso solo hacía falta al lanzar por SSH.
- La ficha pide tu imagen **USA (SCUS-97399)** y la enlaza en `game/God of War.iso`. Las partidas quedan en `Mcd001.ps2`, dentro del repo.

**Qué NO está verificado**: que la opción `--compiler` exista en el `install.sh` del repo (la usaste con el del AppImage 0.3.3); (no tengo tu Ally ni la ISO aquí): que el `install.sh` del repo termine dentro de tu distrobox, ni cuánto tarda una actualización real. Tu instalación anterior (`~/Games/gow-pc-port`, hecha con el AppImage) no se toca y no se reaprovecha: la primera compilación desde el repo será completa.

Pruebas nuevas: `test_v204.py` (ficha, registro `git-build`, sin variables de Wayland).

## v2.05 — Tema Cristal, Explorar con buscador y Descargas sin escalones

**Tema Cristal** (AJUSTES → TEMA, o el botón de tema): barra lateral como el Prototipo, acento celeste y paneles translúcidos con un filo de luz sobre un fondo con tres resplandores (violeta, azul y turquesa). Se calcula una sola vez por tamaño de ventana y cada panel se guarda en caché. Con EFECTOS: RENDIMIENTO se vuelve opaco y plano. Entra en las pruebas de tamaño táctil, glifos y desbordes de todos los temas.

**Fondo corregido (también en Oscuro):** los resplandores se dibujaban sobre una misma capa y el borde transparente del segundo borraba parte del primero, dejando un corte duro. Ahora cada uno va en su capa. Las ampliaciones se hacen de dos en dos para que no salgan bloques.

**Descargas sin escalones:**
- Anillos de progreso con bordes suaves (se dibujan 4× más grandes y se reducen; extremos redondeados; se guardan por tamaño y porcentaje).
- Iconos ✓ ✕ ··· ↓ con el mismo suavizado, y el disco interior del anillo.
- **Todos los botones, paneles y tarjetas redondeados** de la interfaz tienen las esquinas suaves (se suavizan solo las cuatro esquinas, una vez por radio y color). En modo RENDIMIENTO no se aplica.

**Explorar:** buscador único arriba («Buscar juego o proyecto…», entiende nombre, alias y repo) y tres filtros rápidos con su recuento: Instalados, Con actualización y Build Linux (se desactivan si no hay ninguno).

**Pruebas (`test_v205.py`):** tema Cristal completo y que se apaga al cambiar de tema; paneles translúcidos pero acento opaco; opaco en rendimiento; fondo sin saltos bruscos entre píxeles vecinos; resplandor del tema Oscuro; buscador y filtros de Explorar; anillos y esquinas con tonos intermedios y caché reutilizada; capturas de Descargas en los cinco temas.

**No verificado:** cómo se ve en la pantalla real del Ally (solo capturas aquí) ni el coste en fotogramas de los paneles translúcidos con muchas tarjetas; si notas tirones en Cristal, usa EFECTOS: RENDIMIENTO y dime en qué pantalla.

## v2.45

- **«Pasar al escritorio» desde el modo juego.** Tu `session-select.log` decía `Cannot message SteamOS Manager from within a game`: Hub se abre como un «juego» de Steam y SteamOS Manager no atiende cambios de sesión de procesos que cuelgan de un juego. Ahora Hub pide el cambio primero como **unidad transitoria del usuario** (`systemd-run --user --wait steamos-session-select …`, fuera del entorno del juego y sin `LD_PRELOAD`/`SteamGame*`) y, si eso falla, hace la llamada directa de siempre. Si SteamOS sigue rechazándolo, el aviso lo explica y manda a Steam → Energía → Cambiar a escritorio. *Sin confirmar en la Ally: que el gestor de SteamOS acepte la petición desde la unidad (no sé si identifica «dentro de un juego» por el grupo de control o por otra vía).*
- Tests: `tests_pro/test_v240.py`.

## v2.44

- **Instalar otra versión («INSTALAR LIMPIA»)**: si la versión que vas a instalar no es la que tienes (sobre todo al bajar a una anterior), Hub pregunta: **LIMPIA** aparta tu copia a `<carpeta>.prev` (`.prev2`… si ya existe), extrae la versión en una carpeta vacía y recupera de la apartada lo que falte (partidas, ajustes, texturas…; sin pisar nada de lo nuevo; enlace duro, sin duplicar GB), o **POR ENCIMA** (como antes; puede mezclar archivos viejos y nuevos, y chocar si cambió la estructura de carpetas). Si la extracción falla, la carpeta anterior vuelve intacta.
- **Errores de instalación con nombre**: «Falló la instalación (NotADirectoryError): …» en el aviso, en la tarjeta de DESCARGAS y en `hub.log` (`[instalar] id versión: FALLÓ …`). Antes solo decía el texto.
- **Ajustes › actualizaciones**: **COMPROBAR AL ARRANCAR HUB** (por defecto NO; Hub no comprobaba nada por sí solo al arrancar) y **CONSULTAR GITHUB AL ABRIR UNA FICHA** (por defecto SÍ).
- **Fechas de releases**: la ficha dice «Última: v… · fecha · instalada: v… (fecha)» cuando la instalada está entre las 40 últimas.
- Tests: `tests_pro/test_v240.py` (22).

## v2.43

- **Congelar las actualizaciones de un juego** (ficha → MÁS OPCIONES → VERSIONES → *CONGELAR EN vX*): el `.toml` del launcher pasa a `[update] type = "none"` (no comprueba, no pregunta con cuenta atrás, no actualiza) y Hub deja de marcarlo con actualización (Inicio, Explorar, ficha, contador de Actualizaciones). Descongelar restaura el tipo original (`github-archive`…). Instalar a mano otra versión sigue funcionando. Se guarda en `settings › frozen`.
- **Volver a una versión anterior**: ya estaba en VERSIONES → **ELEGIR OTRA RELEASE** (lista las 7 últimas con sus builds de Linux/Windows); ahora, tras instalar la buena, congélala con el botón nuevo para que no vuelva a actualizarse.
- **ELEGIR OTRA RELEASE ya llega a versiones antiguas**: Hub pedía a GitHub solo las 15 últimas y listaba 7; en proyectos que publican cada pocas horas (Tenkaichi3Decomp) la versión buena quedaba fuera. Ahora pide 40 y las lista de 7 en 7 (**MÁS ANTIGUAS ▸ / ◂ MÁS NUEVAS**). Si la etiqueta elegida no está, lo dice en vez de quedarse en silencio con la última.
- **Fondo animado fluido**: en la v2.39 el fondo se redibujaba como mucho a ≈20 fps (≈1,6 fps mientras tocabas) para aliviar el lag; eso hacía ir a tirones a las figuras/cubos giratorios. Ahora solo los brillos grandes (aurora, drift) usan esa caché (≥30 fps en reposo, ≥5 fps al tocar); el resto se dibuja cada fotograma. *Sin confirmar en la Ally.*
- Tests: `tests_pro/test_v240.py`.

## v2.42

- **«Wine propio» para cualquier juego de Windows**, no solo God of War: el botón **WINE PROPIO** sale siempre en la ficha (Windows → *Abrir con*). Eliges tu Wine (**ELEGIR EL WINE**: el ejecutable `wine`) y Hub escribe `windows/hub-run.sh` para abrir el .exe del juego con él. Prefijo por defecto: el del juego (`proton-prefix`); overrides de DLL y variables, editando `hub-run.sh`. Sin Wine elegido, JUGAR lo dice.
- **God of War PSP: primero el launcher.** Por defecto abre `GoWLauncher.exe` con tu Wine; en la ficha, **Abrir: EL LAUNCHER / UN JUEGO DIRECTO**. En directo eliges Chains of Olympus o Ghost of Sparta y se lanza sin pasar por el launcher (con COMPILAR y el ISO USA de cada uno). Desde la terminal: `HUB_MODE=launcher|direct`, `HUB_GOW=coo|gos`.
- **Varios discos para cualquier port**: si el catálogo pide más de un `serial`, ARCHIVO muestra un panel «ESTE PORT PIDE N DISCOS» con un ISO por ID (✓ / falta, ELEGIR/CAMBIAR). Los discos se enlazan junto al juego en Linux **y** Windows.
- Lo guardado en v2.40/41 sigue abriendo el juego directo hasta que cambies el modo.
- Tests: `tests_pro/test_v240.py` (14).

## v2.41

Lo aprendido con God of War PSP en tu equipo (el registro mostró que Hub había enlazado el ISO **PSN**, no el USA, y el juego se cerraba sin decir nada).
- **Dos discos por port**: los ports con varios `serials` (God of War PSP: UCUS98653 y UCUS98737) guardan un ISO **por ID** (`links.json › _discs`). En «Wine propio» hay, por juego, **ELEGIR ISO USA (ID)**; Hub rechaza un ISO PSN/europeo diciendo cuál es. Al reconocer un archivo en ARCHIVO también se guarda para el disco que sea.
- **Aviso antes de lanzar**: con «Wine propio», JUGAR comprueba Wine, juego compilado e ISO y lo dice (toast + `hub.log`) en vez de dejar que `hub-run.sh` salga en silencio.
- **«Wine propio» en un checkout tuyo** (`~/Games/gow-psp-recomp`): al elegirlo, Hub crea `windows/hub-run.sh` y fija el `.toml` del launcher para que abra ese script (antes solo cambiaba si ya existía).
- **Vigía de la pantalla de carga**: tras detectar el juego, si su proceso desaparece mientras Hub tapa la pantalla, Hub **no** se cierra y avisa («el juego se cerró nada más abrir»). Antes daba por abierto un `hub-run.sh` que moría al instante.
- Verificado con tu `hub.log`: Steam **sí** abre el juego con Hub abierto (nfsmw 2,4 s, CTR 2,7 s).
- Tests: `tests_pro/test_v240.py`.

## v2.40

- **«Wine propio» (God of War PSP)**: en la ficha, Windows → *Abrir con*: **PROTON · WINE · WINE PROPIO** (aparece cuando la versión de Windows trae `GoWLauncher.exe`). Usa tu Wine compilado (`~/wine-11.21/loader/wine`), tu prefijo (`~/Games/gow-psp-prefix-staging`) y los `WINEDLLOVERRIDES` de DXVK/VKD3D; corre en el sistema, sin distrobox. Valores y rutas en `src/hub/ownwine.py` (`DEFAULT`) y en el propio `windows/hub-run.sh`, que puedes editar.
- **COMPILAR**: botón en la ficha → `GoWLauncher.exe --build coo|gos` (≈4 min; la primera vez baja el toolchain), con su registro en DESCARGAS.
- **JUGAR**: abre `gow_rt_UCUS…_full.exe --boot --disc Z:\… --fullscreen --fps 60 --renderer gpu --res-scale 2`, sin el diálogo de archivos del launcher. Elige juego en la ficha (Chains of Olympus / Ghost of Sparta) o con `HUB_GOW=gos ./hub-run.sh`.
- **ISO por ID**: al enlazar tu ISO, Hub lee su ID y apunta cuál es de cada juego (`windows/own-disc-coo|gos`). Si falta o no es USA, el lanzador lo dice.
- **Actualizar el proyecto**: la actualización de Windows ya no devuelve el juego a Proton/Wine propio→Proton (antes lo reescribía); con «Wine propio» borra solo `gen/`, `mingw_full/` y `eboot/` (deps, toolchain y mingw_tools se reutilizan) y avisa «hay que COMPILAR otra vez». Wine, DXVK/VKD3D y el toolchain no los toca Hub.
- Sin confirmar en el equipo: todo lo anterior solo está probado con un Wine falso; el comando de `--build` y de arranque salen de tu documento.
- Tests: `tests_pro/test_v240.py`.

## v2.39

- **Inicio «Cristal»/mosaico**: la fila «Más» (Mi biblioteca, Actualizaciones, Descargas, Añadir a Steam) ya no flota sobre los juegos; el mosaico devuelve su borde inferior en coordenadas de contenido.
- **Fondo animado en caché** (`draw_bg`): el brillo animado se recompone como mucho cada 50 ms (y no mientras haces tap o hay efectos), en lugar de en cada cuadro. Mitiga el tirón al pulsar «Descargas» con la barra arriba. *Causa en la Ally sin confirmar* (el sandbox no la reproduce).
- **Pantalla de carga al abrir por Steam**: si el juego tiene su acceso en Steam, Hub lo pide con 1 s de retardo y muestra «Abriendo…» hasta que el proceso del juego aparece; si no aparece en 5 s, Hub se cierra y se lo vuelve a pedir a Steam (como antes). Se puede apagar en Ajustes («Pantalla de carga al abrir por Steam»). Queda en el registro si Steam abrió el juego con Hub abierto.
- Tras detectar el juego, Hub sigue tapando la pantalla 3 s más (`STEAM_COVER`) para que no asome la interfaz de Steam.
- Tests: `tests_pro/test_v239.py`.

## v2.38
- **Temas = temáticas, con paletas y fondos** (`hub/themes_fam.py`). Los 17 temas pasan a **14 temáticas**; los que se parecían ahora son paletas de una misma: **Limpio** (Claro, Oscuro, Océano, Menta, Rosa, Grafito), **Cristal** (Celeste, Aurora, Atardecer, Esmeralda), **Píxel** (8 bits, 16 bits, Verde LCD, Ámbar). Cada tema ofrece 3-6 paletas y 3-4 fondos animados de su temática (Ajustes → Aspecto y control: tema, paleta, fondo). Se recuerda la paleta de cada tema; cambiar de paleta recupera el fondo propio de esa paleta. Los ajustes antiguos (`dark`, `light`, `aurora`, `retro16`…) se migran solos.
- **Inicio**: Limpio (claro y oscuro) comparten la cuadrícula de portadas verticales · **Cristal** estrena **mosaico** (el último juego en grande y teselas altas) · **Onda, Tarjeta, Interruptor y Píxel** usan portadas verticales (Interruptor las eleva al enfocarlas y añade ficha de plataforma) · **Neón** agrupa los juegos por plataforma con cabecera · todas las disposiciones muestran el **nombre del juego** (diccionario) y no el del proyecto; Neón deja el del proyecto en gris cuando se parecen dos juegos.
- **Pantalla de espera**: mientras un juego arranca, una tarjeta con su portada, el título y una barra que va y viene, con el estilo y el texto del tema («INSERT COIN…», «> LANZANDO_», «Leyendo la tarjeta…»).
- Pruebas: `test_v238.py` (contraste de las 50 paletas, migración, paleta/fondo por tema, inicios, espera).

## v2.37
- **Inicio con disposición propia por tema** (`hub/ui_homes.py`): cada tema representa «Tus juegos» a su manera: Oscuro = mosaicos (el de siempre) · Claro = portadas verticales · Quiver = lista con miniatura · Prototipo = héroe «Continuar» + tarjetas · Cristal = burbujas redondas · Aurora = burbujas con halo · Onda = fila que se desplaza (la enfocada crece y muestra su nombre) · Tarjeta = casillas «SLOT» con esquina cortada · Cubo = carrusel de carátulas · Interruptor = iconos grandes con sombra · Brasa = portadas sobre baldas · Píxel = casillas «NIVEL» · 16 bits = cartuchos numerados · Neón = marcador numerado · Fósforo = terminal con puntos guía · Tinta = índice con números romanos · Bloque = bloques con número gigante.
- **Orden de los temas**: primero los que se parecen (Oscuro, Claro, Quiver, Prototipo, Cristal, Aurora, Onda, Tarjeta, Cubo) y luego los más singulares (Interruptor, Brasa, Píxel, 16 bits, Neón, Fósforo, Tinta, Bloque).
- **Cinco timbres nuevos** (silk, click, marimba, arcade, blip) para Onda, Interruptor, Cubo, Neón y Fósforo; ya hay 9 timbres para 17 temas.
- Etiquetas de plataforma abreviadas (PS1, PS4, PSP…).

## v2.36
- **Cinco temas con aire de consolas** (solo imitan el estilo; sin logos, marcas ni imágenes): **Onda** (cintas de seda azules, cristal, barra superior), **Tarjeta** (cubos azules que suben sobre negro), **Interruptor** (claro, tarjetas muy redondeadas, rojo y azul cielo, luces suaves), **Cubo** (cubo de líneas que gira, violeta, barra lateral) y **16 bits** (bandas diagonales que desfilan, violeta de cartucho, letra de píxel). Ya son 17 temas en la cuadrícula.
- Fondos animados nuevos: `silk`, `cubes`, `spincube`, `diag` (se apagan con Efectos: Rendimiento).
- Pendiente (necesita disposición propia, no solo colores): menú en cruz de Onda y fila de mosaicos de Interruptor.

## v2.35
- **Avisos legibles en todos los temas**: el aviso de abajo usaba un fondo negro fijo; en los temas de texto oscuro (Claro, Tinta, Bloque) el texto no se veía. Ahora el fondo sale de la paleta del tema. Prueba nueva: contraste mínimo 4:1 del aviso en los 12 temas.

## v2.34
- **Temas en cuadrícula**: Ajustes → Aspecto y control muestra los 12 temas de una vez, cada uno como miniatura con sus colores reales (fondo, panel, acento, texto) y su nombre; un toque lo aplica, el actual va marcado y debajo se lee su descripción. Sustituye a las tres filas «Tema / anterior / siguiente» (ir atrás y adelante es ahora tocar cualquiera).
- **Fundido al cambiar de tema**: unos 0,35 s desde lo que había en pantalla hacia el tema nuevo. Con Efectos: Rendimiento no se hace.

## v2.33
- **«Pasar al escritorio»**: Hub ya no espera 20 s y da el cambio por fallido (`steamos-session-select` en Bazzite cierra Steam y puede tardar más). Ahora lo lanza aparte, si sigue trabajando a los 8 s lo da por bueno, y si falla prueba `desktop`, `plasma-wayland-persistent` y `plasma-x11-persistent`. La salida de la herramienta queda en `data/session-select.log` y el motivo sale en el aviso.
- **hub-run.sh de Proton** (juegos de Windows instalados por Hub): respeta `.proton-log`; con el registro activado, Proton escribe `proton-logs/steam-0.log` junto al juego. Antes solo lo hacían los juegos que ya tenías. Los `hub-run.sh` ya creados no se reescriben solos.

## v2.32
Efectos en TODOS los temas (se apagan con EFECTOS: RENDIMIENTO; nuevo archivo `hub/ui_fx.py`).
- **Fondo en movimiento en los doce temas:** motas que flotan (Oscuro, Claro, Quiver, Tinta), luces que derivan (Prototipo, Cristal, Aurora), la rejilla avanza hacia ti y el horizonte late (Neón), barrido de tubo (Fósforo), figuras que cruzan (Bloque), estrellas (Píxel) y ascuas (Brasa).
- **Destello al pulsar:** una onda que se abre desde el control y chispas del color del tema (táctil, mando y menús).
- **Halo del foco:** un resplandor difuminado que late alrededor de lo que tienes seleccionado.
- **El icono de la sección da un saltito** al elegirla en la barra lateral.
- **Sonidos por tema:** mismos seis sonidos con cuatro timbres — suave (Oscuro, Claro, Quiver), cristal (Prototipo, Cristal, Aurora), 8 bits (Neón, Fósforo, Píxel) y madera (Tinta, Bloque, Brasa). Tus archivos de `data/sounds/` siguen mandando.
- **Tema anterior / siguiente** en AJUSTES → Aspecto y control, con «tema 3 de 12».

## v2.31
- **Wine sin Wine en el sistema.** Bazzite no trae `wine`: ahora la opción WINE usa, por este orden, el del sistema, un runner de **Bottles**, uno de **Lutris** o el Wine que lleva dentro **GE-Proton**. El `hub-run.sh` lo busca al arrancar y, si no hay ninguno, lo dice (código 127). Vuelve a elegir WINE en la ficha para regenerar el lanzador de un juego que ya tenías.
- **«Preparar contenedor» para cualquier juego**, no solo los que tienen receta: Hub deduce la distribución de `linux-package.json` (build_os), del nombre del paquete («…ubuntu24.04…», «fedora43») o, si al sistema le faltan bibliotecas, propone Fedora. Dentro del contenedor busca e instala solo los paquetes que traen las bibliotecas que `ldd` echa en falta (`apt-file` en Ubuntu/Debian, `dnf install */lib…` en Fedora). El botón sale en MÁS OPCIONES → AVANZADO cuando hay algo que deducir.
- **Tres temas animados con tipografía propia:** **Aurora** (cristal sobre luces que derivan · Poppins), **Píxel** (8 bits, estrellas que parpadean · VT323) y **Brasa** (fragua con ascuas que suben · Chakra Petch). El fondo animado cuesta unas decenas de copias pequeñas por fotograma y se apaga con EFECTOS: RENDIMIENTO.
- **Tipografías descargables** (`hub/fonts.py`): la primera vez que eliges uno de esos temas, Hub baja su fuente de `google/fonts` en GitHub (licencia OFL) a `data/fonts/`; mientras tanto, y si no hay red, el tema usa la del sistema.

## v2.30
- **Vigía del arranque por Steam.** Cuando JUGAR pasa por el acceso de Steam, Hub se cierra y no veía nada: si el juego no abría, no quedaba ni un informe (así se escondió el fallo de BT4). Ahora deja un proceso aparte (`hub.launchwatch`, en una unidad de systemd del usuario) que mira un minuto: si el juego no llega a abrirse o se cierra antes de 25 s, escribe el informe de siempre en `launch-logs/` con el diagnóstico del `.toml`, las bibliotecas y el registro del launcher. En `hub.log`: `[jugar] vigía del arranque: …`.
- **Contenedores de ejecución con apt.** Las recetas admiten `[runtime]` (imagen, paquetes, gestor `apt`/`dnf`; se deduce de la imagen si no se dice) para releases compiladas para otra distribución. Primera receta: **God of War Native PC** → `ubuntu:26.04` con lo que pide su `docs/linux.md` (Qt Quick/QML, SDL2 y lo necesario para importar tu disco). Botón **PREPARAR CONTENEDOR…** en MÁS OPCIONES → AVANZADO: lo crea, instala y deja el juego abriéndose dentro. Un paquete que no exista en esa versión se avisa y no tumba el resto. No toca Bazzite.
- Las recetas de compilar también usan el gestor que corresponda a su imagen (antes solo `dnf`); la comprobación de dependencias entiende `apt install`.
- **Instaladores `.run`** (makeself o con destino por argumento, como el de gow-native-pc): se extraen a una carpeta temporal dentro del juego, sin root y sin pisar nada. Si la release trae también `.tar.gz`, se sigue prefiriendo ese.

## v2.29
Lo aprendido con BT4 Tag Team (JUGAR no hacía nada y no quedaba ni un mensaje).
- **JUGAR comprueba antes que el ejecutable existe.** Si el `.toml` del launcher apunta a un archivo que ya no está (una actualización cambió la carpeta), Hub lo dice y, si encuentra el ejecutable en otro sitio, ofrece **CORREGIR Y JUGAR** (corrige `exe`, `executables` y la carpeta de arranque; copia en `<id>.toml.bak`). Queda en `hub.log` como `[jugar] … el ejecutable del launcher no existe`.
- **Botón CONFIGURAR EL JUEGO** en MÁS OPCIONES → LANZAR cuando el port trae su propio configurador (`…-setup`, como `BT4decomp-setup`, que desempaqueta tu disco). Lo abre con tu ISO ya enlazada en su carpeta.
- Al corregir un `.toml`, si el juego arrancaba en la carpeta de su ejecutable, sigue haciéndolo (ahí busca sus datos).

## v2.28
- **Actualizar un juego cuya release cambió de estructura ya no lo deja sin arrancar.** Caso real: BT4 Tag Team pasó de `BT4decomp/BT4decomp` a `BT4decomp` en la raíz; el `.toml` del launcher seguía apuntando a la ruta vieja y JUGAR no abría nada, sin mensaje. Ahora, tras instalar por encima, si el ejecutable del `.toml` ya no existe y el recién detectado sí, Hub corrige `[run] exe`, `cwd` y `[update] executables` (deja copia en `<id>.toml.bak` y no toca el arte ni lo demás). Queda anotado en `hub.log` como `[instalar] … .toml del launcher corregido`.

## v2.27
Limpieza visual y temas nuevos (plan de usabilidad, pasos 2 y 3).
- **Cuatro temas con carácter propio** (AJUSTES → Aspecto y control → TEMA): **Neón** (recreativa: magenta y cian, rejilla en perspectiva, barra lateral), **Tinta** (papel crema, serif, un solo rojo; sin efectos), **Fósforo** (terminal verde, monoespaciada, líneas de barrido) y **Bloque** (brutalista: amarillo, tarjetas blancas con borde negro, esquinas rectas, barra lateral).
- **El motor de temas cambia más cosas:** tipografía (`FONT` serif/mono y `FONTK` para encoger la monoespaciada), trama del fondo (`PATTERN` rejilla/barrido, dibujada una sola vez) y la forma de las tarjetas de la lista (radio y contorno del tema).
- **Menos ruido:** en la lista de juegos ya no sale «NO INSTALADO» en cada tarjeta (la insignia solo aparece cuando dice algo: instalado, actualización, solo Windows…). En la biblioteca, la píldora naranja «SIN PORT CONOCIDO» de cada fila pasa a ser un discreto «Buscar port ›».
- El aviso «Más abajo» centrado (tapaba texto) es ahora una flecha pequeña en la esquina.
- Filtros de plataforma de la biblioteca en mayúsculas («PS2 · 70»). Error 403 de GitHub más corto y con qué hacer.

## v2.26
Primera pasada de orden y fluidez (plan de usabilidad, paso 1).
- **Inicio sin duplicados.** «Más» queda en una fila: Mi biblioteca · Actualizaciones · Descargas · Añadir a Steam. Se va la tarjeta repetida «Explorar juegos» (ya es una pestaña) y las dos de GitHub pasan a AJUSTES → GitHub y navegador («Abrir GitHub con tu sesión», «Abrir un proyecto de GitHub»).
- **Mi biblioteca a un toque** desde Inicio (antes estaba al final de Explorar).
- **Explorar:** los filtros vacíos ya no se dibujan; «Build Linux» se llama «Con versión de Linux»; «Todos los juegos» dice cuántos hay «en el catálogo».
- **Rendimiento:** el arte de cada juego se guarda mientras no cambie su carpeta `art/` (antes Inicio recorría el disco en cada fotograma: 120 ms en el registro del Ally).

## v2.25
- **El enlace a tu ISO/ROM también para la versión de Linux.** Al pulsar JUGAR (y antes de abrir el juego, también si pasa por su acceso de Steam), Hub deja el enlace en la carpeta del juego, en su carpeta de trabajo (`[run] cwd`, donde está p. ej. `start-linux.sh`) y en `linux/` si la instalación está separada, además de donde el catálogo pida (`requires.place`). Así el selector de archivos del lanzador la muestra a primera vista. Nunca pisa un archivo real; respeta el ajuste «enlazar en la carpeta del proyecto».

## v2.24
- **«AÑADIR A STEAM» desde la ficha de un juego (modo juego) ya pasa al escritorio.** Antes solo mostraba una instrucción de terminal y, si cambiabas tú de sesión, Hub no se reabría. Ahora usa el mismo camino que «Pasar al escritorio» del apartado Steam: escribe el autoarranque y Hub se abre allí en «Preparar Steam».

## v2.23
- **Aviso de región/ID del disco.** Hub lee el ID real del ISO (PSP: `PSP_GAME/PARAM.SFO` → `DISC_ID`; PS2/PS1: `SYSTEM.CNF`) recorriendo el sistema de archivos ISO 9660, sin depender de dónde caiga el texto (en un UMD de 1,7 GB el ID está muy dentro). Si el archivo no coincide con lo que pide el port, el aviso dice los dos: «Tu archivo es NPUG80325 (digital (PSN)); el port pide UCUS98653, UCUS98737». También sale en ARCHIVO («· ID …»). No lee `.chd`/`.cso`: ahí sigue el reconocimiento de antes.
- **Qué pide cada port** se completa con `catalog/requirements.json` (por repositorio; no pisa lo que ya traiga la tarjeta): GoW PSP → UCUS98653 / UCUS98737 (solo USA), GTA VCS → SLUS-21590. Añade ahí otros ports.
- `scan_serial` ya encuentra el ID aunque esté fuera de los primeros 4 MB (antes un UMD correcto podía salir «No coincide»).
- **El juego a primera vista en el selector de archivos de Windows:** además del enlace en `windows/`, Hub enlaza tu ISO/ROM en el **Escritorio y Documentos del «C:» de Proton/Wine** del juego (`proton-prefix/…/drive_c/users/<usuario>/`). Si el prefijo aún no existe (primer arranque) lo hace en cuanto Proton lo crea (hasta ~2 min, con Hub abierto). Nunca pisa un archivo.
- Sin confirmar en el equipo: que el diálogo de abrir del launcher de Windows enseñe esas carpetas al abrirse.

## v2.22
- **Las descargas del servicio de catálogo sobreviven al cierre de Hub.** El servicio sigue descargando aunque cierres Hub; antes Hub guardaba los trabajos solo en memoria y al reabrir DESCARGAS salía vacía. Ahora se guardan en `data/catalog_jobs.json`, y al arrancar Hub retoma la consulta de las que seguían vivas. Las que terminaron con Hub cerrado se procesan al volver (enlazado/hash como siempre) y no se avisan dos veces. Si el servicio ya no conoce un trabajo, sale el error normal de conexión perdida. Hub no usa el «picture in picture» del servicio: solo consulta `job_status` (sin confirmar en el equipo qué muestra esa ventana).
- **«Más opciones» en 5 pestañas** (antes una lista larguísima): **ARCHIVO** (tu disco/ROM, vigilar descargas, carpeta de ROMs) · **VERSIONES** (repositorio, release, elegir otra, ver qué trae el archivo, Quiver) · **LANZAR** (partidas, carpeta de arranque, Steam y arte) · **COMPILAR** (compilar y portar con IA) · **AVANZADO** (dónde está cada cosa, registro de Proton, distrobox, BORRAR). Se abre la que toca según el paso (archivo → versiones → lanzar) y se recuerda por juego. «AVANZADO» ya no está en el árbol de la ficha y el botón «CONTENEDOR» se llama «CONTENEDOR PARA COMPILAR» (el de AVANZADO es el que abre el juego). Se quitó un método `toggle_adv` duplicado que chocaba con el de Ajustes.
- **Archivos comprimidos dentro de archivos comprimidos:** si lo extraído es solo otro zip/tar (más papeles sueltos como txt/sha), Hub lo abre también (hasta 2 niveles) y borra el intermedio. Si hay más archivos al lado, se considera un dato del juego y no se toca. En una actualización por encima solo mira lo recién extraído.
- **.7z** se extrae con `7z`, `7zz`, `7za`, `bsdtar` o `unar` si alguno está instalado; si no, dice cómo instalarlo.
- **VER QUÉ TRAE EL ARCHIVO** (VERSIONES): lista el contenido de un `.zip` de la release leyendo solo su índice con peticiones HTTP Range (unos KB, sin bajarlo). Solo `.zip`; probado con un servidor local, no con GitHub real.

## v2.21
- **Releases de «solo Windows» sin la palabra «windows» en el nombre** (God of War PSP publica `GoW_PSP_Launcher-v1.5.0.zip`): si la release no trae nada marcado como Linux, los zip/7z/tar con nombre ambiguo se ofrecen también como versión de Windows (etiqueta «¿windows?», puntuación menor), la ficha arranca en WINDOWS · PROTON y la etiqueta pasa a «SOLO WINDOWS · PROTON» en vez de «BUILD (¿LINUX?)». Con un build de Linux claro, lo ambiguo no se toca. Se excluyen nombres con setup/install/source/src/symbols/pdb/debug.
- Es una heurística: si el zip ambiguo no es de Windows, el paquete no tendrá `.exe` y Hub lo dirá al instalar.

## v2.20
- **ELEGIR OTRA RELEASE** (ficha → MÁS OPCIONES → VERSIÓN): lista las últimas 7 releases con cuántos builds de Linux y de Windows trae cada una, y lo que descargas/instalas es la elegida. Si la release actual no trae lo que miras (p. ej. Windows) y otra sí, la ficha lo avisa. La «actualización disponible» sigue comparando con la última, no con la elegida; REFRESCAR vuelve a la última.

## v2.19
- **El binario compilado en el contenedor arranca sin `LD_LIBRARY_PATH`.** Tras traer las `.so` que faltan, la receta fija el RPATH del binario (`$ORIGIN/lib`) y de las bibliotecas (`$ORIGIN`) con `patchelf` del contenedor (el sistema no se toca; se instala en el contenedor si falta). Probado a mano en el equipo con GTA VCS: `readelf` muestra `RPATH [$ORIGIN/lib]` y `ldd` ya no marca nada como «not found». Sin confirmar todavía: que el AppImage abra el juego así desde JUGAR.
- Se desactiva por receta con `[output] rpath = false`.

## v2.18
- **La ficha es un árbol de decisiones.** 1) «¿Dónde quieres jugar?» LINUX | WINDOWS. 2) Solo se abren las opciones de la rama elegida:
  - **LINUX → Método:** RELEASE (AppImage/binario) | COMPILAR (contenedor) → **Abrir en:** EL SISTEMA | CONTENEDOR (solo para el método activo).
  - **WINDOWS → Abrir con:** PROTON | WINE → elegir un .exe que ya tengas.
  - Lo técnico (registro de Proton, elegir distrobox) sigue en «AVANZADO».
- **Los métodos de Linux ya no se pisan:** registrar un build compilado guarda la release (y su modo contenedor se deshace antes), y se puede volver a ella con un toque (`linux_release` / `linux_built` en `.hub-versions.json`). `[update] type` se restaura/anula según el método.
- **Proton o Wine con un toque** para una versión de Windows ya instalada: Hub reescribe `windows/hub-run.sh` (también para builds descargados, que antes solo tenían Proton) sin tocar `proton-prefix`.
- El resumen de arriba dice qué abre JUGAR: «LINUX · compilado por Hub · dentro del contenedor «x»», «WINDOWS con Wine»…

## v2.17
- **El envoltorio «abrir en el contenedor» limpia `LD_PRELOAD` y `LD_LIBRARY_PATH` antes de entrar al distrobox** (también `hub-run.sh` de los builds de Hub). Hipótesis (sin confirmar en el equipo): desde Hub/Steam el AppImage heredaba el overlay de 32 bits y el runtime de Steam, y dentro del contenedor `clang`/`lld` fallaban al configurar CMake («Linker does not support -Wl,--version-script»), mientras que desde una terminal limpia compilaba bien.
- El envoltorio `hub-container.sh` se **reescribe cada vez** que eliges CONTENEDOR (una versión nueva de Hub arregla los ya creados) y recuerda el ejecutable original, sin apuntarse a sí mismo.

## v2.16
- **Sección de versiones más clara.** Ahora la ficha dice primero «VERSIÓN DE ESTE JUEGO» y qué abren JUGAR y Steam («WINDOWS con Proton», «LINUX en el sistema», «LINUX dentro del contenedor «x»»), con los botones LINUX · listo/compilado aquí/sin instalar y WINDOWS · listo/descargar.
- Dos bloques con su explicación: **WINDOWS** (un .exe se abre con Proton; si es instalador/lanzador, la primera vez prepara el juego y luego deja jugar) y **LINUX** (compilar en un contenedor, usar el juego ya compilado, y «Abrir Linux en: EL SISTEMA | CONTENEDOR» como dos botones, no un interruptor con estado en el texto).
- Lo técnico (registro de Proton, elegir distrobox) pasa a «AVANZADO ▾».
- Textos renombrados: «USAR EL JUEGO YA COMPILADO», «COMPILAR EL JUEGO EN UN CONTENEDOR», «RECOMPILAR EN EL CONTENEDOR».
- **Arreglo: pulsar «Abrir Linux en: CONTENEDOR» ya no congela la interfaz ~1 s.** El log real mostró fotogramas de 900-1000 ms: `distrobox list` se ejecutaba en el hilo principal. Ahora va en un hilo (y `have_distrobox` se cachea).
- **El «error» del AppImage en el contenedor era ruido de Steam/gamescope**, no un fallo: `gameoverlayrenderer.so … ELFCLASS32: ignored`, `ATTENTION: default value of option …`, `pid N != M, skipping destruction`, `[Gamescope WSI]`. Hub ya no crea un «informe de arranque fallido» por ellas y los informes las omiten (indicando cuántas) para que se vea lo importante.
- **Arreglo:** al envolver el AppImage para abrirlo en el contenedor, la lista `executables` del `.toml` conserva el AppImage (antes solo quedaba `hub-container.sh`, y una actualización lo dejaba sin permiso de ejecución).

## v2.15
- **Compilar para Linux en un contenedor (distrobox), sin instalar nada en Bazzite.** Ficha → opciones de versión: «COMPILAR PARA LINUX EN CONTENEDOR» para los juegos con *receta* (`hub/recipes/*.toml`; hoy GTA: Vice City Stories). Hub crea el contenedor del juego (`hub-<id>`, Fedora 43: igual o más antigua que Bazzite), deja el código en `<juego>/linux` (clona el repo, no usa el zip de Windows) y enlaza tu ISO con el nombre que exige el proyecto.
- **Antes de instalar nada, ves la lista.** Fase 1: contenedor + la comprobación de dependencias del propio proyecto (`--check-deps`); Hub descarta lo marcado «(launcher)». Fase 2 (tras aceptar): paquetes DENTRO del contenedor, `deps.py fetch` (la release de Windows trae `deps/` solo de Windows), región del ISO, compilación, y trae del contenedor las `.so` que el sistema no tenga (FFmpeg…) a `build/lib`. Todo se ve por etapas en DESCARGAS.
- **«USAR EL BUILD YA COMPILADO»:** si ya compilaste a mano (`linux/build/vcs`), solo trae las bibliotecas y lo registra, sin recompilar.
- **Versión de Linux registrada de verdad:** `linux/hub-run.sh`, `[update] type = "none"` mientras esté activa (no se le superpone el archivo de Windows de la release) y se restaura al volver a Windows. No se borra ni se mueve nada.
- **«EJECUTAR EN: SISTEMA / CONTENEDOR» + «DISTROBOX»** para cualquier versión de Linux. Un build de Hub usa el marcador `linux/.run-in-container`; cualquier otra (p. ej. el AppImage del lanzador) se envuelve con `linux/hub-container.sh` (`distrobox enter … -- <exe>`, con `APPIMAGE_EXTRACT_AND_RUN=1` para AppImage) y se deshace con un toque. JUGAR y Steam abren lo mismo.
- Para añadir otro juego así basta una receta nueva (imagen, comprobación, preparación, compilación, salida).
- Verificado con pruebas automáticas (análisis de dependencias con la salida real, fases, registro de la versión, modo contenedor, flujo de botones). **No verificado en tu equipo:** compilar desde el botón, la ventana del juego en gamescope y que `distrobox enter` con un AppImage abra bien la pantalla.

## v2.14
- **CANCELAR descarga funciona al momento.** Antes una descarga activa seguía «activa» hasta que el servidor soltaba la conexión (hasta 20 s); ahora pasa a «Cancelada» al pulsar, el hilo borra el parcial y un error de red posterior ya no la convierte en «error». Tiempo de lectura bloqueada 20 s → 8 s.
- **Sin descargas duplicadas:** si la versión de Windows (o la de Linux) del mismo juego ya está en cola, activa o *pausada*, no se añade otra.
- **Versión de Windows con tu ROM/ISO:** al instalarla y al pulsar JUGAR, Hub deja en `windows/` un enlace a tu archivo reconocido (el selector del lanzador de Windows empieza ahí). No escribe dentro de la carpeta de tu juego.
- **Botón claro:** «INSTALAR / AÑADIR / REINSTALAR / ACTUALIZAR WINDOWS · PROTON». Esa acción solo toca `windows/`. Además, reinstalar la versión de Linux con Windows activa ya no extrae Linux dentro de `windows/` (primero reactiva `linux/`).
- **JUGAR con Windows (Proton) no cierra Hub a los 6 s:** la primera vez Proton crea el prefijo y descarga archivos (DLSS), la ventana tarda y por eso «aparecía al reabrir Hub». Ahora Hub se queda abierto.

## v2.13 — La ficha muestra los builds de Windows de cada release

- **Antes:** la ficha solo listaba los builds de Linux y, de Windows, únicamente el primero y solo si no había de Linux.
- **Ahora:** en la ficha, panel VERSIÓN (dentro de MÁS OPCIONES), si la release trae builds de las dos plataformas aparece un selector **LINUX (n) / WINDOWS · PROTON (n)**. Cada lista muestra hasta 5 archivos; eliges uno y el botón del paso 2 descarga ese: el de Linux se instala como siempre, el de Windows se coloca en `windows/` y se abre con Proton (umu-run). Si solo hay builds de Windows, se ve directamente su lista.
- Por defecto se muestra Linux; Windows si es el único o es la versión activa del juego. Los instaladores `.exe` y los `.msi` siguen sin ofrecerse (solo builds empaquetados zip/7z/tar).
- Pruebas: `test_v212.py` ampliado (selector, elección del segundo build, solo Windows).

## v2.12 — Usar un .exe de Windows que ya tienes (Proton / Wine) desde la ficha

- **Dónde:** ficha del juego → MÁS OPCIONES → «USAR UN .EXE DE WINDOWS QUE YA TENGO (PROTON / WINE)». El juego debe estar en tu biblioteca (tener su `.toml` en el launcher). Elige el `.exe` y luego «Proton» (GE-Proton con `umu-run`) o «Wine del sistema».
- **Qué hace:** reorganiza la carpeta del juego como ya hacía la versión de Windows (lo que había pasa a `linux/`), crea `windows/game` como **enlace** a la carpeta del `.exe` (no copia ni toca tus archivos) y escribe `windows/hub-run.sh`, que entra en la carpeta del juego y ejecuta el `.exe` con el «disco C:» propio `proton-prefix/`. El `.toml` del launcher apunta a ese script, así que **JUGAR y Steam abren lo mismo**. Puedes volver a Linux con el selector de versión.
- **Registro de Proton:** en la misma ficha, «REGISTRO DE PROTON: SÍ/NO». Con SÍ el script exporta `PROTON_LOG=1` y deja `proton-logs/steam-0.log` dentro de la carpeta del juego; además el informe del arranque fallido sigue en `data/launch-logs`.
- **Sin verificar con Proton real:** las pruebas usan un `umu-run` simulado (comprueban carpeta de trabajo, argumentos, enlace, `.toml` y prefijo). Que un juego concreto arranque depende de Proton: pásame el registro si falla.

## v2.11 — Hub ya no depende de MiniTube

MiniTube es otra aplicación y solo fue inspiración para el navegador de Hub; ahora el código no la usa.
- Quitado: el puente `hub/minitube.py`, la fila «MINITUBE» de Ajustes, la opción de navegador «MiniTube» y el ajuste `minitube_dir`. Un ajuste guardado como `minitube` pasa solo a AUTOMÁTICO.
- AUTOMÁTICO ahora: en Big Picture, el navegador táctil de Hub (Qt) si está instalado; si no, el de Steam o el del sistema.
- Las cookies de GitHub importadas se siguen guardando (`data/github-cookies.json` y `.env` del launcher), pero ya no se cargan en ningún navegador de Steam. «Sesión de GitHub» abre github.com en el navegador elegido.

## v2.10 — Actualizar ya no puede dejar Hub roto ni sin reiniciar

- **Qué pasó (verificado):** tras actualizar y reiniciar la máquina, `hub/downloads.py` quedó con **0 bytes** y Hub no arrancaba («no tiene atributo Manager»). Lo más probable es que el reinicio llegó antes de que el disco guardara los archivos recién instalados (hipótesis). `hub-update --force` lo reparó.
- `hub-update` ahora fuerza la escritura a disco (`sync`) y, si algún `.py` queda vacío, da la instalación por fallida y restaura la copia anterior.
- `bin/hub` comprueba al arrancar si hay `.py` vacíos y, si los hay, se reinstala solo desde el zip.
- **Reinicio tras ACTUALIZAR:** antes Hub lanzaba una copia fuera de Steam; al cerrarse el Hub viejo, Steam podía dar por terminado el «juego» y matarla (hipótesis, coincide con lo visto). Ahora deja una marca y el propio `bin/hub` relanza dentro del mismo proceso.

## v2.09 — Menos procesos hacia Steam: el portapapeles ya no se lee cada segundo

- Tras v2.08 tu journal seguía mostrando ~58 `Adding process` por minuto (antes ~180). El resto venía del vigilante del portapapeles, que lanzaba `wl-paste`/`xclip` cada 1 s.
- Ahora solo lee con Hub delante (si otra ventana o el menú de Steam tiene el foco, no lo hace) y cada 2,5 s.
- Para comprobarlo: `journalctl --user --since "-1min" | grep -c "Adding process"` con Hub abierto, quieto en Inicio; debería bajar a unos pocos por minuto. Si no baja, mándame el recuento y `pgrep -af "wl-paste|xclip|xsel|xprop"`.

## v2.08 — Hub deja de crear ~3 procesos por segundo (Steam los contaba como parte del juego)

- **Causa (verificada en tu journal):** con Hub abierto, Steam escribía `Adding process N for gameID …` unas 3 veces por segundo. Era el vigilante de foco de Gamescope, que lanzaba un `xprop` nuevo cada 0,4 s.
- Ahora usa **un único** `xprop -spy` que avisa solo cuando cambia el foco, y muere con Hub. Si no está disponible, consulta cada 1 s; `HUB_FOCUS_POLL=1` fuerza el modo antiguo.
- **Sin verificar en tu Ally:** que esto arregle el QAM/menú tras actualizar; es una hipótesis (menos ruido de procesos hacia Steam). Probado con un `xprop` simulado, no con el real.

## v2.07 — Ajustes sin lag al hacer scroll (el log lo delató)

- **Causa (verificada en tu hub.log):** la fila «DESCARGAR CARÁTULAS FALTANTES» contaba las carátulas en *cada fotograma*: 2431 juegos × 4 extensiones ≈ 9.700 consultas de disco por fotograma (≈200 ms → 8 fps). Ahora se lista la carpeta una sola vez y el número se refresca como mucho cada 5 s.
- Nota: en ese log no aparece el lanzamiento de «crash» ni el reinicio de Steam; ver la respuesta en el chat.

## v2.06 — Arrancar Hub desde una terminal ya no deja un Hub invisible, bordes suaves 10× más baratos y efectos que se notan

**Arrancar `bin/hub` desde una terminal sin pantalla (SSH u otra sesión).** Antes el script cerraba el Hub que estaba abierto en la pantalla (por diseño: si queda vivo, Steam cree que el juego sigue abierto) y arrancaba otro **sin ventana** («driver=offscreen»), que además moría después: parecía que Hub se cerraba solo y no dejaba hacer nada (es lo que salió en tu `hub-perf.txt`: «ventana 1024x768 driver=offscreen» y código 137). Ahora, si la terminal no tiene `DISPLAY`/`WAYLAND_DISPLAY`/gamescope y hay un Hub abierto, el nuevo toma la pantalla de ese Hub (`WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `DISPLAY`, `XAUTHORITY`, gamescope y Steam) y se abre en el mismo sitio. Si no hay pantalla de ningún tipo, lo dice en el registro (`AVISO: no hay pantalla…`).

**Bordes suaves (v2.05) 10× más baratos.** Los 58 paneles de una pantalla tardaban 3,6 ms por fotograma (antes del suavizado, 0,45 ms); en el Ally, más lento, se notaba. Ahora cada panel es una copia ya preparada (una por tamaño, radio y color): 0,32 ms. Límite de ~80 MB de caché, que se vacía sola. Las cachés nuevas de v2.05 no son la causa de ningún cierre por memoria: unos 12 MB en total.

**EFECTOS (cristal / rendimiento) ahora cambian algo en Prototipo.** Antes solo afectaba al tema Oscuro (y a los menús esmerilados): en Prototipo, Claro y Quiver el fondo era liso en los dos modos. Ahora Prototipo con «cristal» tiene un degradado con resplandor naranja y azul; con «rendimiento» sigue liso. Claro y Quiver siguen planos a propósito. Cada tema declara su fondo con `GRAD` y `ORBS`.

**Pruebas:** `test_hub_tests_cli.py::test_ejecuta_y_escribe_informe` y `test_v203.py::test_un_archivo_que_no_importa_no_corta_la_bateria` fallaban en tu Ally: lanzaban `hub-tests` con casa temporal y sin `PYTHONUSERBASE`, así que el Python de miniforge no veía pygame (instalado con `pip --user`). Era un fallo de las pruebas, no de `hub-tests`. Nuevas en `test_v206.py`: herencia de pantalla, aviso sin pantalla, y que los paneles suavizados son una copia cacheada (menos de 2 ms para 58 paneles).

**Lag al desplazarse por «todos los ajustes»:** las pruebas miden el coste de CPU de cada fotograma, no `display.flip` ni el compositor, así que no lo ven. Para medirlo en el equipo real, **dentro de Hub** (no desde otra terminal): AJUSTES → «Registrar rendimiento», desplázate un rato y mira `grep rendimiento ~/Games/recomp-hub/data/hub.log`. En tu primer registro, «inicio» tardaba 20–34 ms por fotograma (objetivo 22 ms) y `flip` solo 1–2 ms: el coste está en dibujar, no en presentar.

## v2.46
- Corregido: pulsar REGISTRO en una tarjeta de DESCARGAS de tipo trabajo (Wine propio, contenedor…) cerraba la app, porque ese visor pedía un `logfile` que esos trabajos no tienen. Ahora muestra el registro igual.

## v2.47
- Corregido: `UnboundLocalError: every` en el vigía de foco de Gamescope (gsfocus) que aparecía en hub.log.
- Las descargas reintentan hasta 3 veces ante cortes de red (SSL EOF, conexión reiniciada, tiempo agotado) antes de marcar error.

## v2.48
- Nuevo ajuste global «EL LAUNCHER COMPRUEBA ACTUALIZACIONES AL ABRIR CADA JUEGO» (Ajustes › Actualizaciones): en NO pone `[update] type = "none"` en todos los juegos (recuerda el tipo de cada uno y lo restaura con SÍ). Se reaplica al arrancar Hub.
- El contador de GitHub (ghstats) ahora desglosa las llamadas por tipo; sale en hub.log tras comprobar.

## v2.49
- La pantalla de carga de Hub ahora espera a que OTRA ventana (la del launcher/juego) tenga el foco de Gamescope antes de cerrarse (margen 1,5 s, tope 12 s); el fragmento de la interfaz de Steam no cuenta. Sin datos de Gamescope sigue el tiempo fijo (4 s).
- Congelar un juego con el interruptor global apagado conserva su tipo de actualización original.

## v2.50
- La pantalla de carga al abrir un juego por su acceso de Steam es opaca del todo y entra en 0,12 s (antes translúcida: se veía el botón pulsado y la ficha), y se mantiene también mientras Hub espera a que salga la ventana del launcher (antes desaparecía en esa fase).

## v2.51
- Los assets cuyo nombre trae «pc» a secas (SilentHillPC-….zip) se clasifican como Windows: antes caían en «?» y Hub no ofrecía versión de Windows para Silent Hill (SlickAmogus/silent-hill-decomp). Linux sigue mandando si el nombre también lo dice.

## v2.52
- «Ejecutar desde .exe»: si el .exe estaba dentro de la carpeta del juego (Silent Hill), Hub reorganizaba la carpeta (todo pasa a `linux/`) pero el enlace `windows/game` seguía apuntando a la raíz, ya vacía, y el juego nunca encontraba el .exe. Ahora el enlace sigue al archivo a `linux/`.

## v2.53
- `hub-run.sh` con Wine (los que genera Hub desde ahora) guarda la salida y los errores de Wine en `<juego>/hub-wine.log` (WINEDEBUG=err+fixme), para ver por qué un juego se cierra al darle Play.

## v2.54
- `hub-run.sh` con Wine: si no hay `$DISPLAY` (lanzado por SSH o terminal remota) usa `:0` y el `XAUTHORITY` del escritorio (`/run/user/<uid>/xauth_*`), para que la ventana salga en la pantalla de Bazzite en modo escritorio.

## v2.55
- `hub-run.sh` con Wine: además de `DISPLAY`, ahora también busca el `XAUTHORITY` del escritorio aunque `DISPLAY` ya esté puesto (si no, X contesta «Authorization required» y Wine no encuentra driver gráfico).

## v2.56
- `hub-run.sh` con Wine quita `LD_PRELOAD` (superposición de Steam) y un `LD_LIBRARY_PATH` de Steam antes de lanzar: en la versión de Windows de Silent Hill el juego se cerraba con «Unhandled page fault … address 0x0» solo cuando lo abría Steam.

## v2.57
- `hub-run.sh` con Wine también quita `WINEDLLOVERRIDES` y `mesa_glthread`: el modo juego de Bazzite exporta `WINEDLLOVERRIDES=dxgi=n` (dxgi nativo obligatorio, que Wine no tiene) y `mesa_glthread=true`; sospechosos del `page fault 0x0` de Silent Hill solo en modo juego (v2.56 quitaba además LD_PRELOAD).

## v2.58
- Al elegir el .exe de una versión de Windows, si junto al del juego hay un «<nombre>_Launcher.exe» se prefiere el launcher (Silent Hill: antes se elegía `SilentHillPC.exe`, que solo cae con «a serious problem»; funciona desde `SilentHillPC_Launcher.exe`).

## v2.59
- El botón VER de una descarga terminada ahora abre la ficha del juego también en instalaciones Windows/Wine (`install_win`) y sale de cualquier vista previa.
- Al abrir una ficha sin datos de releases en caché (tras reinstalar) se consulta ese único juego aunque `fetch_on_open` esté apagado.

## v2.60
- Silent Hill con Proton: `proton_path()` prefiere UMU-Proton (si existe) antes que GE-Proton, porque GE-Proton11-11 aborta con `win32u.NtGdiCreateColorSpace` sin implementar. Se puede forzar con `HUB_PROTON=<carpeta>`.
- Los `hub-run.sh` de Proton ahora también fijan DISPLAY/XAUTHORITY y limpian el entorno de Steam (igual que los de Wine).
- Selector de Proton por juego (ficha → MÁS OPCIONES → LANZAR → rama WINDOWS, runner Proton): «VERSIÓN DE PROTON». Lista los Proton de `compatibilitytools.d`, guarda la elección en `.hub-versions.json` (`windows.proton`) y reescribe `hub-run.sh`. «Automático» = UMU-Proton más nuevo, luego GE-Proton. No toca el prefijo.

## v2.61
- «SALTAR EL LAUNCHER» (ficha → LANZAR → WINDOWS): si el .exe de Windows es un lanzador con un .exe hermano (Silent Hill: `SilentHillPC_Launcher.exe` + `SilentHillPC.exe`), `hub-run.sh` abre el juego directo. Pensado para modo juego, donde el launcher (WinForms) no se maneja con mando. Se guarda en `.hub-versions.json` (`windows.skip_launcher`) y se puede deshacer.

## v2.62
- `hub-run.sh` de Proton hace `cd` a la carpeta del .exe antes de lanzar (Steam lo arrancaba desde otra carpeta y el juego no encontraba config.cfg ni gamedata/).

## v2.63
- Los hub-run.sh de Wine y Proton hacen `unset SDL_VIDEODRIVER SDL_AUDIODRIVER`: el modo juego exporta SDL_VIDEODRIVER=x11 y el SDL2.dll de Windows no lo tiene («[Psy-X] Failed to initialise SDL» → puntero GL nulo → page fault 0x0 en Silent Hill).

## v2.64
- Ficha → VERSIONES: texto claro de qué se va a instalar («Se instalará: X · ELEGIDA por ti / la última publicada», comparado con la instalada), antigüedad de los datos («datos de hace 3 h») y los dos interruptores globales (consultar GitHub al abrir una ficha; el launcher comprueba al jugar) sin salir de la ficha.
- Abrir una ficha lee primero lo guardado en disco (`github.from_cache`, 0 llamadas). Solo se consulta GitHub si no hay nada guardado de ese juego, o si «consultar al abrir» está en SÍ (con la caché de 6 h y el ETag casi nunca gasta cuota).

## v2.65
- Ajustes reorganizados: «GitHub y actualizaciones» reúne todo lo que gasta cuota (contador de consultas de la sesión, comprobar ahora, comprobar al arrancar, consultar al abrir una ficha, el launcher comprueba al jugar) y la sesión/token/cookies; «Mis juegos y archivos» queda solo con ROMs, descargas y carátulas.
- Ajustes → Al jugar → «Proton por defecto (juegos de Windows)»: elige UMU-Proton/GE-Proton para los juegos nuevos (`proton_default`); cada juego sigue pudiendo fijar el suyo en su ficha.

## v2.66
- God of War PSP (y cualquier port de varios discos): el **paso 1 de la ficha** ya no depende de un solo archivo. Muestra «2 de 2 discos · ✓ Chains of Olympus (UCUS98653)  ✓ Ghost of Sparta (UCUS98737)» y solo se marca hecho cuando están todos enlazados (✗ en los que faltan).
- Registro de mandos y entrada para el Wine propio: con «REGISTRO DE PROTON» activado (ficha → AVANZADO), `hub-run.sh` guarda en `hub-own.log` (junto a la carpeta del juego) la fecha, DISPLAY/XAUTHORITY/SDL_VIDEODRIVER/LD_PRELOAD, los `/dev/input/js*` y `/dev/hidraw*` que ve y los canales de Wine `winebus, hid, hidraw, dinput, xinput, joystick`. Para diagnosticar «el juego corre pero no reconoce el mando en modo juego».

## v2.67
- Actualizar la versión de Windows de un juego conserva ahora el Proton elegido en su ficha y «saltar el launcher» (antes el `.hub-versions.json` se reescribía y el `hub-run.sh` volvía al Proton automático y al launcher). El runner (Wine / Wine propio) y el prefijo ya se conservaban desde la v2.40.

## v2.68 — Actualizar GoW PSP conserva los ajustes del launcher
- `install_windows` respalda `GoW_PSP_data/build/launcher*` (launcher.json, input, perf) antes de extraer y los restaura después, por si el paquete nuevo los trae.
- Steam Input: para GoW PSP se recomienda dejarlo desactivado (con él activo el mando no llega al juego en Wine).

### v2.68 (añadidos)
- **Descargas:** el contador nunca pasa de 100 % y «reintentar» sobre una descarga con hilo vivo ya no arranca un segundo hilo (antes sumaban bytes los dos).
- **Compilar GoW PSP:** barra de avance REAL (ninja: `.ninja_log` / `build.ninja`), tiempo transcurrido, y la tarjeta de DESCARGAS la enseña. La compilación ya no hereda `LD_PRELOAD` de Steam (quita el ruido «ld.so … ELFCLASS32»).
- **Discos:** `note_disc` también lee `launcher.json` y busca los «God of War» junto al ISO enlazado: aparece Ghost of Sparta aunque no lo hubieras enlazado.
- **Ficha Wine propio:** bloques «CÓMO SE ABRE» y «JUEGOS» (juego 1 y 2 con su estado, ISO y COMPILAR/RECOMPILAR cada uno).
- Símbolos `≈ … ⚠ ⚙` con sustituto ASCII si la fuente no los trae.

## v2.69
- God of War PSP: panel de juegos rediseñado en tarjetas (número/✓, estado con puntos de color compilado/disco, botones de ISO y compilar dentro de cada tarjeta; en modo directo, botón «▶ SE ABRE ESTE»).

## v2.70
- Cuadrados (tofu): flechas, formas y dingbats se sustituyen siempre por ASCII; además se detecta el glifo ausente comparándolo con el «cuadrado» de la fuente.
- «Elegir un .exe» pasa a MÁS OPCIONES → ARCHIVO; el registro del último arranque fallido pasa a AVANZADO → REGISTROS (en la ficha queda un aviso corto).

## v2.71
- MÁS OPCIONES → ARCHIVO rediseñada en dos columnas: carátula a la izquierda (con insignia de disco o cartucho según los formatos que pide el port) y a la derecha lo que pide el juego, una tarjeta de estado con icono grande y ✓ verde cuando el archivo está reconocido, y los botones.
- Varios discos: cada uno con su icono de disco, ✓ y nombre del archivo.

## v2.72
- MÁS OPCIONES → VERSIONES rediseñada: tarjetas «instalada → disponible» (insignia ACTUALIZACIÓN / AL DÍA), builds con icono de sistema y ✓ en el elegido, paneles aparte para ACCIONES y REPOSITORIO.

## v2.73
- Ficha del juego: nueva cabecera con carátula grande, título, chips (plataforma, juego, repositorio), descripción y estado (archivo reconocido, instalado, actualización).
- God of War PSP: cada juego en una tarjeta con su carátula, número, icono de disco con ✓ y estado/botones a la derecha.

## v2.74
- Ficha reorganizada: cabecera con carátula, SOLO el paso que toca (archivo, instalar o jugar), fila «Se abre así» con CAMBIAR y un botón AJUSTES DEL JUEGO.
- AJUSTES DEL JUEGO es una pantalla aparte con menú lateral: Archivo y discos · Cómo se juega · Versiones · Steam y arte · Compilar (si aplica) · Avanzado. B vuelve a la ficha.
- Quitado el botón PÁGINA DEL PROYECTO de Versiones (ya está en Y).

## v2.75
- Ficha: el botón principal (JUGAR / INSTALAR / ACTUALIZAR) va dentro de la cabecera; el panel de pasos solo sale para el archivo o una descarga en curso.
- God of War PSP: los dos juegos (modo, estado, ISO, compilar) están en la ficha, no en Ajustes.
- Si el último arranque falló, «VER EL REGISTRO» es un botón de la ficha.

## v2.76
- **Actualizar ya no anida la carpeta del zip** (BT4, BT3): si la release trae todo dentro de una carpeta y se actualiza por encima, se sube un nivel. Antes quedaba «BT4decomp/BT4decomp» y el juego no arrancaba (o seguía en la versión vieja). También se corrige el caso de carpeta nueva y primer instalado cuando la carpeta se llama igual que el ejecutable.
- Actualizar ya no escribe «a través» de los enlaces duros: la copia `.prev` queda intacta.
- **REPARAR CARPETA**: aviso en la ficha si una instalación quedó anidada; la repara sin tocar `gamedata/`, `saves/`, `mods/`… y lo sustituido queda en `.hub-replaced/`.
- **CAMBIAR ARCHIVO** (ISO/ROM) en la cabecera de la ficha y en Ajustes → Archivo: reenlaza los enlaces de `linux/` y `windows/` al archivo nuevo, conservando su nombre.
- **Selector de archivos con abecedario**: orden A–Z (botón A–Z/RECIENTES), índice de letras al borde derecho (solo las que existen) y L1/R1 saltan de letra.
- **Wine propio**: si tu `hub-run.sh` está editado a mano, Hub ya no lo pisa (escribe `hub-run.sh.hub` al lado) y la ficha avisa de que el Wine elegido no se aplica; botón USAR EL SCRIPT DEL HUB (tu script queda como `hub-run.sh.mio`).

## v2.77
- **Indicador de trabajo:** mientras algo tarda (reparar una carpeta, buscar/descargar arte, probar la conexión…) sale una pastilla con una rueda que gira y los segundos transcurridos; así no parece que Hub se haya congelado. REPARAR CARPETA ya corre en segundo plano.
- **Arte:** la clave ya no se cambia por error: el botón vive en un panel «CUENTA Y CONEXIÓN» al final de la pantalla, pide confirmación y guarda la clave anterior (`~/Games/launcher/state/.sgdb_key.prev`). Arriba solo aparece PEGAR CLAVE cuando falta.
- **SteamGridDB con VPN:** las descargas de arte (SteamGridDB, libretro, TheGamesDB, ScreenScraper) intentan normal → solo IPv4 → normal, con tiempos más cortos, y el error dice la causa real (tiempo agotado, DNS, certificado, reset, Cloudflare bloqueando la IP de la VPN) en vez de «URLError». Nuevo botón PROBAR CONEXIÓN que comprueba DNS, TCP (IPv4/IPv6), TLS y HTTP.

## v2.78
- **Actualizar por encima ahora es por etapas:** el paquete se extrae a una carpeta temporal, se comprueba (que traiga ejecutable) y solo entonces se mueve archivo a archivo. Lo reemplazado queda en `.hub-replaced/upd-<fecha>/` y, si algo falla a mitad, todo vuelve a su sitio. Vale para Linux y para las versiones de Windows.
- **Se instala en la carpeta real del juego:** antes la versión nueva se extraía en la raíz aunque el juego estuviera en `linux/` (GTA VCS: la 0.3.0 quedó fuera y seguía en «ACTUALIZAR»). Ahora se usa el `install_dir` del `.toml` o la subcarpeta activa, y `.hub-versions.json` se mantiene al día con el ejecutable nuevo.
- **AppImage con otra versión en el nombre** (`…0.2.4…` → `…0.3.0…`): la antigua se aparta para que el juego abra la nueva.
- **Respeta lo que no es del paquete:** tus datos (`gamedata`, `saves`, `mods`…), enlaces a tu ISO, `hub-run.sh` y `.hub-versions.json`; y NO toca el actualizador propio del juego (`update/`, `updater.py`, `trg-updater.exe`, `update-*.sh`). El diálogo de actualizar avisa si el juego trae uno.
- La versión también se escribe en el `version_file` del `.toml` cuando no es `.release_version` (p. ej. `.installed_tag`); los nombres de asset del `.toml` llevan «*» en lugar de la versión (`toystory2-*-linux-x64.zip`).
- **SteamGridDB/arte:** si la red corta el saludo TLS («EOF occurred in violation of protocol»), se prueba también TLS 1.2 y IPv4 + TLS 1.2; PROBAR CONEXIÓN muestra cada intento.

## v2.79
- **Historial por juego** (ficha → AJUSTES DEL JUEGO → Avanzado → HISTORIAL): cada vez que juegas, instalas/actualizas o compilas se guarda una línea en `data/history/<id>.jsonl` con una foto del entorno de ese momento: versión del juego, distribución (linux/windows), runner (Proton/Wine/propio) y su versión, contenedor, lista de distrobox, sistema y versión de Hub. La pantalla agrupa por configuración y dice cuáles funcionaron (✓), cuáles fallaron (✗) y el error. Los arranques por Steam quedan «pendientes» hasta que se sabe si abrieron.
- Los arranques fallidos y las compilaciones (con su contenedor) alimentan el historial solos.
- **Arte:** cuando fallan las miniaturas, la pantalla dice cuántas y por qué (antes solo «sin miniatura» y la causa iba al terminal).

## v2.80
- **Un solo selector de contenedor por juego** (antes había tres sitios distintos): ficha → Linux → «CONTENEDOR: …», Ajustes → Compilar y Ajustes → Avanzado abren el mismo cuadro. Lista TODOS los distrobox que existen (antes se cortaba en 8) con ✓ en el actual, más «EL SISTEMA» y «CREAR UN CONTENEDOR NUEVO (Fedora)». Sirve para abrir el juego y para compilarlo.
- **Arreglado el «glitch» al abrirlo:** el botón del contenedor consultaba `distrobox list` en el hilo de la interfaz (1 s, hasta 20 s) y la pantalla se quedaba congelada; ahora se busca en segundo plano con la rueda de trabajo. El contenedor por defecto (Ajustes) también es una lista, ya no hay que teclear el nombre.
- **Compilar usa el contenedor DEL JUEGO** (antes siempre el global «fedora», aunque el juego tuviera otro). Si el contenedor no existe, Hub lo dice en rojo y ofrece elegir o crear uno, en vez de fallar a mitad.
- Juegos sin carpeta dividida (`linux/`+`windows/`) recuerdan su contenedor en los ajustes de Hub.
- En la rama Linux, el aviso explica para qué sirve abrir en contenedor (paquetes de compilación que Bazzite no deja instalar en el sistema).

## v2.81
- **CANCELAR compilación funciona:** antes solo se paraba el proceso directo (bash/distrobox) y sus hijos (cmake, ninja…) seguían con la tubería abierta, así que el trabajo no terminaba nunca. Ahora se detiene todo el grupo de procesos (SIGTERM y, a los 3 s, SIGKILL) y el trabajo pasa a «Cancelado» al instante. En la ficha, mientras compila, el botón pasa a «PULSA AQUÍ PARA CANCELAR». Si el contenedor sigue ocupado: REINICIAR.
- **Herramientas del contenedor** (ficha → Linux): PROBAR (dice si de verdad estás dentro de un contenedor, con qué sistema/usuario, si `sudo` va sin clave y qué herramientas hay), COMANDO… (ejecuta lo que escribas con el teclado en pantalla dentro del contenedor, p. ej. `sudo dnf install -y clang`, con salida y cancelación en DESCARGAS) y REINICIAR (detiene el contenedor y todo lo que tenga en marcha; se arranca solo después).
- **EXPORTAR DIAGNÓSTICO** (Ajustes del juego → Avanzado): un solo archivo `~/diag-<id>.md` con el historial y el entorno, carpetas, `.hub-versions.json`, `hub-run.sh`/`hub-container.sh`, registros de Proton/Wine/launcher, informes de arranque, `distrobox list` y las líneas de `hub.log` del juego. Tapa tokens y claves. Solo lee.
- **Versiones por sistema:** la ficha muestra «Linux v0.3.0 ✓ · Windows v0.2.4 (antigua) · última v0.3.0» y avisa de que Proton, Wine y Wine propio usan la misma carpeta `windows/` (cambiar de uno a otro no descarga nada).
- **Carpeta de Wine propios:** `~/wines/<versión>/bin/wine` (también `~/Games/wines` y `~/wine-*`). «ELEGIR EL WINE» ahora lista los que encuentra y deja buscar otro archivo.

## v2.82
- **Corrección del error `libGL.so.1: cannot open shared object file` (código 127) dentro del contenedor.** En el modo juego de Steam el Hub hereda `LD_PRELOAD` (overlay de Steam) y `LD_LIBRARY_PATH`; `distrobox` los pasaba al contenedor y cualquier programa de dentro (hasta `bash`) fallaba antes de ejecutar nada, por lo que `dnf`, el compilado y el launcher del port nunca llegaban a correr. Ahora COMANDO…, COMPILAR, PROBAR y la preparación del contenedor lanzan con el entorno limpio (`proctree.clean_env`). Los envoltorios `hub-container.sh` ya lo hacían desde v2.56/2.75.

## v2.83
- Tras v2.82 el contenedor ya arranca: sale «Container Setup Complete». Esta versión limpia lo que quedaba: las funciones `BASH_FUNC_*` de Bazzite/gamescope (daban «post_gamescope_start: syntax error») ya no se pasan al contenedor.
- COMANDO… viene con `sudo dnf install -y ` escrito y corrige solo `sudo install -y …` (sin `dnf`) a `sudo dnf install -y …`.

## v2.84
- **Con qué contenedor se lanza el juego.** Hay dos ajustes distintos: el contenedor del juego (el que eliges con CONTENEDOR) y «Ejecutar en: sistema / contenedor». El juego solo se lanza dentro del distrobox si «Ejecutar en» está en contenedor. Corregido: en un build compilado por el Hub, el nombre del contenedor estaba escrito dentro de `hub-run.sh` desde la compilación, así que elegir otro después no cambiaba dónde se lanzaba. Ahora, al activar «Ejecutar en: contenedor», se reescribe ese nombre. En los AppImage (`hub-container.sh`) ya se reescribía.

## v2.85
- **Mantener pulsado un juego (como en el teléfono).** En Inicio, si dejas el dedo ~0,45 s sobre la tarjeta de un juego (o el «Continuar» grande), sale un menú pequeño junto al dedo: JUGAR (o INSTALAR), ABRIR LA FICHA, HISTORIAL, EXPORTAR DIAGNÓSTICO y PÁGINA DEL PROYECTO. Mientras mantienes, aparece un arco que se completa. Al soltar no se lanza el juego ni se elige nada por error. Si arrastras el dedo, se cancela (sigue siendo desplazar).
- **Sonido y vibración.** Al salir el menú suena el sonido «open» del tema y el mando vibra un instante (ajuste en Ajustes → aspecto: «VIBRACIÓN AL MANTENER PULSADO UN JUEGO»). La pantalla táctil de Linux no vibra por sí sola: se usa la vibración del mando que Hub ya tiene abierto; si no hay, no pasa nada. Sin verificar en el Ally.
- Ajuste oculto en `settings.json`: `long_press` (segundos, por defecto 0.45).

## v2.86
- **«Ajustes del juego» en 5 pestañas por objetivo** (antes 6, ordenadas por de dónde salía cada ajuste): JUGAR · ARCHIVOS Y VERSIONES · COMPILAR Y CONTENEDOR · STEAM Y ARTE · DIAGNÓSTICO Y BORRAR. «Archivo y discos» y «Versiones» comparten pestaña (primero el archivo, luego VERSIONES); «Cómo se juega» pasa a JUGAR; «Avanzado» pasa a DIAGNÓSTICO Y BORRAR (historial, exportar diagnóstico y, abajo, borrar). Los nombres antiguos de pestaña siguen valiendo por dentro.
- La pestaña abierta se marca con relleno, ya no con ✓ (un ✓ suele significar «hecho»).
- Pendiente (v2.87): el contenedor y «Ejecutar en» en un solo sitio, textos largos a una línea y filas plegables (ARCHIVOS Y VERSIONES tiene ahora 23 controles; el presupuesto es 12 antes del primer plegable).

## v2.87
- **El contenedor, en un solo sitio.** La pestaña COMPILAR Y CONTENEDOR abre con una tarjeta: cuál es el contenedor del juego, si está listo / no existe, y CAMBIAR O CREAR · PROBAR · COMANDO… · REINICIAR. Se quitaron los botones repetidos de JUGAR y de DIAGNÓSTICO Y BORRAR: JUGAR conserva «Abrir en: el sistema / contenedor», una línea con el estado y ADMINISTRAR (te lleva a esa tarjeta).
- La pestaña COMPILAR Y CONTENEDOR también sale en juegos sin repositorio si hay distrobox.
- **Textos de ayuda de una línea** en JUGAR y COMPILAR; «Clona el repositorio…» y los avisos de compilar/release se acortaron. El comando se edita con un botón a todo el ancho.

## v2.88
- **Visor de registros con barra de herramientas:** COPIAR (lo que ves, al portapapeles) · GUARDAR (el registro completo, sin colores, en `~/hub-log-<título>.txt` para adjuntarlo) · RUIDO: OCULTO/VISIBLE · AL PRINCIPIO · AL FINAL. Antes solo había CERRAR y se veían las últimas 250 líneas; ahora hasta 1500 (y 3000 en el registro de Hub).
- **Sin códigos de color ni ruido:** `ESC[32m` ya no sale como cuadrados, y por defecto se ocultan «skipping destruction (fork without exec?)», los avisos del overlay de Steam (`LD_PRELOAD … ELFCLASS32`) y el diario interno (`[tecla]`, `[rendimiento]`, `[vivo]`, `[foco]`, `[ventana]`). El visor dice cuántas líneas oculta.
- **Desde la terminal:** `bin/hub-logs --trabajo [N]` imprime las últimas N (80) líneas de los trabajos (COMANDO…, COMPILAR…) sin ruido; `--seguir` las muestra en vivo; `--ruido` no filtra.

## v2.89
Ficha > AJUSTES DEL JUEGO: en ARCHIVOS Y VERSIONES, «VERSIONES» y «¿YA TIENES EL JUEGO DE WINDOWS?» son ahora secciones plegables (escriben «abierto/cerrado»); VERSIONES se abre sola si falta instalar o hay actualización. Un solo nombre: «VER PLAN DE COMPILAR» y «COMPILAR». Cabecera de la ficha más baja (miniatura y título más pequeños). Se corrige un solape de botones en 1920×1080.

## v2.90 · Motor de temas, fase A (integración)
Nuevo paquete `hub/themes` (Python puro). El Hub ahora lee los temas del motor: `apply_theme` usa `hub.themes.legacy.build`, idéntico a `themes_fam.build` para los 14 temas × 58 paletas × fondos (prueba `test_v290`). Cada cambio de tema/paleta/fondo publica `data/appearance.json` (colores, tipografía, sonido, fondo, forma del Inicio). Incluye `check_contrast` (mismas reglas que test_v238) para validar colores propios y `legacy.catalog()` para pintar la futura sección «Apariencia». Contrato para quien haga esa sección: `src/hub/themes/CONTRATO.md`. No cambia nada de lo que se ve.

## v2.91 · Peticiones de apariencia
`data/appearance-request.json` (id, versión de esquema, cambios): el Hub la valida (tema, paleta del tema, fondo, contraste), aplica y confirma en `appearance.json` (`request.status`). Rechazo = no cambia nada; el mismo id no se repite ni tras reiniciar. Los fallos de publicación ya no se esconden: van a `hub.log` con `[apariencia]`. `CONTRATO.md` documenta los dos formatos (v2 del Hub, v1 del motor nuevo) y el protocolo.

## v2.92 · Pulsación larga en Explorar, Biblioteca y Descargas
El menú pequeño (con sonido y vibración) de Inicio funciona ahora también en: **Explorar** (la tarjeta de juego: JUGAR/INSTALAR, ACTUALIZAR A x.y si hay versión nueva, ABRIR LA FICHA, HISTORIAL, DIAGNÓSTICO, PÁGINA), **Biblioteca** (ABRIR o BUSCAR UN PORT, BUSCAR EN GITHUB) y **Descargas** (las mismas acciones de la tarjeta: PAUSAR/REANUDAR/REINTENTAR/VER y CANCELAR/QUITAR). Un toque corto sigue haciendo lo de siempre. «Quitar de Inicio» no existe: Inicio muestra los juegos instalados y no hay lista de fijados.

## v2.93 · Tema Obsidian
Nuevo tema (15.º) **Obsidian**: oscuro uniforme, portadas verticales (`HOME=posters`), sin transparencias, sin desenfoque, sin animación de fondo, tipografía del sistema y sonido discreto (`soft`). Una sola paleta con los 13 colores pedidos (BG #101114 … FOCUS #E1E2E6). Se añadió a `themes_fam.py` como familia nueva —las 14 anteriores no se tocan— y a `catalog_data.py` (regenerado). Aparece en el selector de Ajustes > Apariencia, se guarda en ajustes y sobrevive al reinicio. Contraste: TXT/BG 16,7 · DIM/PANEL 6,9 · ACC/BG 10,9 · LINE/BG 2,2.
Limitaciones: es un tema de una sola paleta y de un solo fondo (liso); no hay «preset minimal» ni «material solid» como piezas del modelo nuevo porque el Hub aún no las renderiza: Obsidian usa el modelo de familias, el único que el Hub dibuja hoy.

## v2.94 · Instaladores de Windows (Setup.exe)
Proyectos que solo publican un instalador (ReStreet / FIFA Street: `FifaStreetSetup.exe`) ya no se quedan sin la opción «WINDOWS · PROTON». `win_assets` ahora ofrece los `.exe` llamados *Setup/Install* (no desinstaladores, símbolos, depuración, servidores ni ARM64) **al final de la lista** y marcados «INSTALADOR». Al elegirlo: Hub explica los pasos (elige tu ISO y una carpeta de destino VACÍA que él sugiere, `~/Games/<juego>-windows`, fuera de la carpeta del juego), descarga el instalador a DESCARGAS y, al terminar, ofrece **ABRIR EL INSTALADOR (PROTON)** —`umu-run` con el `proton-prefix` del juego, el mismo que usará JUGAR— y **ELEGIR EL .EXE INSTALADO**, que usa el flujo ya existente de «ya tengo el juego de Windows». Escribe `hub-installer.sh` y `hub-installer.log` en la carpeta del juego. Limitación: el juego debe estar ya registrado en Hub (cualquier versión instalada); para juegos aún no instalados, primero hay que registrar uno.

## v2.95 · Corrección de la v2.94: el instalador respeta `<juego>/windows/`
La v2.94 sugería instalar en una carpeta hermana (`~/Games/<juego>-windows`), fuera de la estructura `<juego>/linux` y `<juego>/windows`. Ahora todo va dentro: destino **`<juego>/windows/instalado/`** (vacío), `hub-installer.sh` y `hub-installer.log` en `<juego>/windows/`, y el «C:» de Proton es `<juego>/proton-prefix`, el mismo que usa JUGAR. Al reorganizar la carpeta del juego, lo de Linux pasa a `linux/` y `windows/` se queda donde está (prueba incluida). Si con la v2.94 se creó `~/Games/<juego>-windows`, está vacía y no se usa: bórrala tú cuando quieras (Hub no borra nada).

## v2.96 · Correcciones de la revisión de código
- **Apariencia (fallo de la v2.91):** al arrancar, el Hub reescribía `appearance.json` sin la confirmación de la última petición; una petición vieja que siguiera en `appearance-request.json` se volvía a aplicar en cada reinicio y deshacía los cambios hechos a mano. Ahora se lee la confirmación antes de publicar.
- **Instalador de Windows (v2.94/95):** si cerrabas el menú del instalador, solo se podía volver descargándolo otra vez. Ahora «VER» en DESCARGAS vuelve a abrirlo.
- **Contenedor:** el aviso «No pude cambiarlo: …» al cambiar «Abrir en: sistema/contenedor» nunca se mostraba (la variable del error ya no existía cuando se pintaba el aviso).
- `CONTRATO.md` del motor de temas al día (15 temas, protocolo de peticiones ya existente).

## v2.97 · Estudio de temas (implementación de prueba)
Ajustes → Aspecto: debajo de los 15 temas, **«Estudio de temas · prueba»** con las 8 identidades del documento de diseño (Minimal, Showcase, Glass, Flow, Arcade, Terminal, Editorial, Brutalist). Salen del motor nuevo (`resolve`) a través de un adaptador (`hub/themes/studio.py`) y cambian colores, forma de Inicio, material (cristal/contorno), radio, tipografía, timbre y fondo animado. Para cada una se elige **paleta, fondo e Inicio** entre los que su preset declara compatibles. Se guarda en ajustes (`theme = "v3:…"`, `layouts`) y se publica en `appearance.json`. LB/RB desde una de ellas vuelve a los temas heredados. Los 15 temas anteriores no cambian (prueba incluida).
Aún no: Explorar, Descargas y Ajustes con organización propia por tema; peso «medium», espaciado, intensidad/velocidad del fondo, volumen por tema, niveles de calidad.

## v2.98 · Instalador de Windows: ISO a mano, unidad G:, registro automático; vuelve «PÁGINA DEL PROYECTO»
- **ISO a mano (como en v2.44):** al abrir un instalador de Windows, Hub enlaza tu ISO reconocida en `<juego>/windows/` y en Escritorio/Documentos del «C:». Antes solo se hacía cuando la versión de Windows ya estaba registrada, que con un instalador aún no ocurre.
- **Unidad G: (posible arreglo del «necesita 15 GB»):** antes del instalador se crea el prefijo y una unidad `G:` (o la siguiente libre) que apunta a `<juego>/windows/`. En Bazzite la unidad `Z:` es `/`, de solo lectura y casi sin espacio libre; un instalador que mida la raíz de la unidad cree que no caben los 15 GB. Elige la ISO y el destino en `G:` (`G:\instalado`). Nunca pisa una unidad que ya existiera. **Sin verificar con ReStreet.**
- **FIFA Street volvía a pedir «descargar Windows»:** el instalador abría el juego, pero Hub no lo registraba hasta que elegías el .exe a mano. Ahora, al cerrarse el instalador, si hay juego en `windows/instalado` Hub abre el selector para elegir su .exe; la ficha dice «WINDOWS · elegir .exe» (en vez de «descargar») y ese botón abre el selector.
- **PÁGINA DEL PROYECTO** vuelve a la ficha (panel de builds, junto a REFRESCAR); en v2.44 estaba y se había perdido.

## v2.99 · «¿Dónde quieres jugar? LINUX | WINDOWS» vuelve a la ficha
En v2.44 el selector estaba en la vista principal de la ficha; desde v2.74 solo quedaba dentro de AJUSTES DEL JUEGO › JUGAR y parecía que no se podía cambiar. Vuelve a la vista principal (encima de AJUSTES DEL JUEGO), con los mismos estados: «listo», «elegir .exe» (el instalador ya dejó el juego en windows/instalado) o «descargar».
Confirmado en el equipo: `df -h /` → `composefs 45M 45M 0 100% /`. La raíz del sistema no tiene espacio libre; un programa que mida el espacio de «/» (o de la unidad Z: en Wine) cree que no caben los 15 GB.

## v3.00 · La versión de Windows ya no se vuelve a descargar en cada arranque
Al elegir un .exe de Windows a mano (un juego que ya tenías, o el que dejó un instalador como el de ReStreet), Hub apuntaba el .toml del launcher a `windows/` pero dejaba su `[update]` activo; ahí no hay `.release_version`, así que el launcher creía que faltaba la versión y la bajaba otra vez cada vez que se abría el juego. Ahora, con esa versión activa, `[update] type = "none"` (como con los builds compilados aquí) y al volver a Linux se restaura el que había. El menú del instalador descargado se abre en el hilo de la interfaz (antes desde el hilo de la descarga).

## v3.01 · ReStreet: no volver a bajar el instalador y buscar el juego en el «C:»
Con el `hub.log` real: el `.toml` ya tenía `[update] type = "none"` (la v3.00 no era la causa aquí). Lo que pasaba: cada «WINDOWS · descargar» bajaba otra vez `ReStreet-2.1.5-Setup.exe` (453 MB); el instalador se cerraba y Hub no veía el juego en `windows/instalado` («0 .exe»), así que nunca quedaba registrado y la ficha seguía en «descargar».
- Si el instalador ya está descargado (en DESCARGAS o en la carpeta de descargas con el mismo tamaño), se abre su menú directamente, sin bajarlo.
- Al cerrarse el instalador, si no hay nada en `windows/instalado`, Hub busca .exe nuevos dentro del «C:» del prefijo (Program Files, AppData, C:\Games…; sin los de Windows ni desinstaladores) y abre el selector ahí.

## v3.02 · Tarjeta VERSIONES, instalador sin menú y la ISO visible dentro del instalador
- **VERSIONES DE ESTE JUEGO** (vista principal de la ficha): una fila por sistema (LINUX · nativo, WINDOWS · con Proton/Wine) con su estado escrito —sin instalar (y qué se bajaría), descargando N %, instalador descargado, instalada · falta elegir su .exe, instalada, compilada aquí— y UNA acción: INSTALAR, ABRIR INSTALADOR, ELEGIR .EXE, USAR o ACTIVA. Arriba dice qué abre JUGAR. Sustituye al «¿Dónde quieres jugar?» (ya no se repite en la pestaña JUGAR, que queda para CÓMO se abre: Proton/Wine, contenedor…).
- **Instalador sin menú intermedio:** al terminar la descarga se abre directamente; al cerrarlo, Hub busca el juego (windows/instalado y el «C:» del prefijo). Si ya estaba descargado, no se vuelve a bajar.
- **La ISO no se veía en el instalador:** se enlazaba en `users/bazzite`, pero Proton usa `users/steamuser`. Ahora el propio `hub-installer.sh` la enlaza en Escritorio y Documentos de todos los usuarios del prefijo justo antes de abrirlo (y sigue en `G:\`).
- **«WINDOWS · descargar» aunque el juego estuviera instalado:** si el instalador lo dejó en su ruta por defecto del «C:», ahora cuenta como instalado («falta elegir su .exe»).
- Xalia (ayuda de mando de Proton) desactivada en el instalador: se caía con el de ReStreet.

## v3.03 · La ISO, como enlace duro (Wine no mostraba el simbólico)
En el selector de archivos del instalador de ReStreet (bajo Proton) el Escritorio solo mostraba carpetas: la ISO, enlazada con un enlace simbólico, no aparecía aunque estaba ahí. Ahora Hub pone tu ISO como **enlace duro** en `windows/` (unidad G:) y en Escritorio/Documentos del «C:»: es el mismo archivo, sin copiar nada, y Wine lo ve como un archivo normal. Si la ISO está en otro disco, sigue poniendo un enlace simbólico. Los enlaces simbólicos que dejaron versiones anteriores se sustituyen; nunca se pisa un archivo real. Vale para todos los juegos de Windows (también lo que hace JUGAR).
Nota: con un enlace duro, si borras la ISO original, el espacio no se libera hasta borrar también esos enlaces (el prefijo del juego).
El instalador usa el Proton elegido para el juego (si hay uno), no siempre el general.

## v3.04 · Upgrade de temas, fase A: el material se dibuja
Las 8 identidades del Estudio llevan ya el **material** del registro del motor hasta el dibujo de paneles, tarjetas y botones (`rr`): **sombra** suave bajo cada superficie (Solid 0,18, Glass 0,30, Arcade 0,24…), **borde** con su grosor (Outline 2,0 en Terminal y Brutalist, Arcade 1,5, Paper 0,5, Solid 1,0) y **opacidad** (Soft 0,94; Glass sigue translúcido con su filo de luz). En EFECTOS: RENDIMIENTO no hay sombras ni transparencias. Las sombras se preparan una vez por tamaño (un blit por panel).
Los 15 temas heredados no cambian: comparación píxel a píxel de Inicio, Explorar, Descargas y Ajustes en los 15 temas — en modo rendimiento 60/60 capturas idénticas; en modo cristal las únicas diferencias son las de los fondos animados (las mismas que da la versión anterior comparada consigo misma).
Arreglado: con letra grande (Arcade, Editorial, Brutalist) el título «Estudio de temas · prueba» se montaba sobre su subtítulo.

## v3.05 · Upgrade de temas, fase B: Minimal y Showcase con Explorar y Descargas propios
- **Minimal**: Explorar es un catálogo de **portadas verticales con el nombre debajo** (4–7 columnas según el ancho; estado en una línea: instalado/actualizar/consola). Descargas en **filas limpias a todo el ancho**.
- **Showcase**: Explorar con **portadas grandes** (3–5 columnas). En Descargas la descarga activa es un **panel protagonista** a todo el ancho y el resto va debajo en dos columnas.
- Mismas claves de foco que antes (`card:…`, `dl:…`): mando, teclado, toque y pulsación larga no cambian.
- El resto de identidades y los 15 temas heredados mantienen la organización de siempre. Comparación píxel a píxel (modo rendimiento) de Inicio, Explorar (consolas y lista), Descargas y Ajustes en los 15: idénticos salvo la franja del subtítulo «Estudio de temas» de Ajustes, cambiada a propósito en v3.04.
Pendiente de pulir: el panel protagonista de Showcase tiene mucho espacio libre (falta una barra de progreso grande).

## v3.06 · Upgrade de temas, fase C: Flow y Glass (y Showcase con estantes)
- **Flow**: Explorar en **estantes**, una fila de portadas por consola (las de más juegos primero); si no caben, la última casilla es **VER TODOS (n)** y abre esa consola. Descargas en **filas amplias con barra de progreso grande**.
- **Showcase**: Explorar pasa también a estantes, con portadas grandes (era cuadrícula en v3.05); su descarga protagonista lleva la barra grande.
- **Glass**: Explorar como **mosaico** de portadas de tamaños distintos (una de cada seis, al doble) con el nombre sobre la imagen; Descargas, la de siempre con el material cristal.
- Con un filtro o una búsqueda, los estantes se convierten en el catálogo de portadas (una sola lista).
- Los 15 temas heredados: comparación píxel a píxel (modo rendimiento) de Inicio, Explorar (consolas y lista) y Descargas, idénticos.

## v3.07 · Upgrade de temas, fase D: Arcade y Terminal
- **Arcade**: Explorar con **portadas numeradas** (01, 02, 03… como las casillas de su Inicio). Descargas en la rejilla de dos columnas con **barra por bloques** de estilo recreativa.
- **Terminal**: Explorar como **catálogo de texto**: una línea por juego (nº · nombre · consola · estado) agrupada por consola (`== PLAYSTATION 2 (3) ==`), filas de 72 px (≥ 7,2 mm). Descargas como **procesos**: una fila por descarga con la barra en texto `[#####.....]  42%`.
- Las tarjetas de descarga siguen el radio de esquina de la identidad (Arcade y Terminal casi cuadradas); los temas heredados, el de siempre.
- Los 15 temas heredados: comparación píxel a píxel (modo rendimiento) de Inicio, Explorar (consolas y lista) y Descargas, idénticos.

## v3.08 · Upgrade de temas, fase E: Editorial y Brutalist
- **Editorial**: Explorar como **índice de revista**: título de sección grande (serifa) por consola con su número de juegos y una raya; filas con portada pequeña, nombre en grande y una línea de datos, separadas por una línea fina (sin cajas). Descargas como **tabla sobria**: filas a todo el ancho con barra fina.
- **Brutalist**: Explorar en **bloques geométricos** con número gigante (01, 02…), uno de cada cinco a doble ancho y relleno de acento, portada pequeña a la derecha, nombre en mayúsculas. Descargas en bloques más altos con **indicador grueso** y el porcentaje dentro.
- Con esto las 8 identidades del Estudio tienen Explorar y Descargas propios (Glass: Descargas con su material, sin organización distinta). Ajustes sigue igual en todas.
- Los 15 temas heredados: comparación píxel a píxel (modo rendimiento) de Inicio, Explorar (consolas y lista) y Descargas, idénticos.

## v3.09 · Temas, tanda 1: parámetros globales ligeros
- **Accesibilidad para todos los temas** (Ajustes › Aspecto y control): **Movimiento reducido** (sin fondo animado, entradas escalonadas, fundidos, destellos, latido del foco ni salto de iconos; desplazamiento directo), **Alto contraste** (texto ≥ 7:1, texto secundario ≥ 4,5:1, bordes/acento/foco ≥ 3:1, paneles opacos con contorno, sin brillos ni tramas) y **Texto grande** (toda la letra ×1,2). Apagadas, los temas se dibujan exactamente como antes.
- **Calidad en tres niveles** (EFECTOS): Cristal (todo) → **Equilibrado** (fondo quieto y sin destellos; conserva materiales y el desenfoque de los menús) → Rendimiento.
- **Fondo animado con velocidad, intensidad y densidad** por identidad del Estudio (los temas heredados, 1/1/1).
- **Glass**: su material desenfoca más el fondo de los diálogos; sigue calculándose una sola vez al abrir el menú (no en cada fotograma).
- **Declarados, sin aplicar todavía**: 7 niveles tipográficos (display, heading, title, body, secondary, caption, numeric) y densidad (compact/comfortable/spacious) por identidad; peso **medium real** para Poppins y Chakra Petch (se baja con la fuente; si falta, negrita), VT323 con su único peso y las del sistema con el Medium instalado si lo hay (fuentes no variables). Para los diseños nuevos: `UI.type_font(nivel)`.
- `radius_scale` del material se aplica respecto al del material por defecto de cada preset (con el de siempre no cambia nada).
- **Círculo de progreso** de Descargas legible en los temas claros (antes el disco quedaba gris medio bajo el porcentaje). Solo cambia ese indicador; en los oscuros, igual.
- Arreglado: los textos recortados («…») se guardaban sin tener en cuenta la letra del tema; tras cambiar de tema (o con texto grande) podía salir un recorte de la letra anterior.
- appearance.json publica `quality` y `accessibility`.

## v3.10 · Repos solo de Windows, arranque directo y revisión de la lógica
- **God of War II HD** (y cualquier proyecto que publique solo un `.exe` suelto o un `.rar` de Windows): ahora se ofrece como versión de Windows con Proton. Antes la release no tenía «nada compatible». Un `.exe` que no es instalador se guarda tal cual en `windows/`; los `.rar` se abren con 7z/unar/bsdtar.
- **INSTALAR / ACTUALIZAR** desde cualquier sitio (botón X, Inicio, menú de pulsación larga) sigue a la versión que toca: si la release solo trae Windows, o en la ficha elegiste Windows, instala la de Windows (antes: «No hay un build compatible»).
- **Arranque directo** (Ajustes › Al jugar, activado): los juegos se abren sin la pantalla previa del launcher (comprobación, novedades y cuenta atrás), porque Hub ya los actualiza. Funciona al jugar desde Hub y por el acceso de Steam: el `shortcuts/<id>.sh` generado por el launcher se guarda como `<id>.sh.launcher` y se sustituye por uno que llama a `hub/playdirect.py`; al desactivar la opción se restaura. Los accesos hechos a mano no se tocan. Si algo falla antes de abrir el juego, se usa `bin/play` como siempre.
- **Revisión de la lógica**:
  - Soltar el dedo ya no pulsa un botón que apareció debajo mientras tocabas (por ejemplo, un menú que se abre al terminar una descarga).
  - La rueda del ratón o del touchpad no desplaza una página corta.
  - Si una pantalla falla 5 fotogramas seguidos, Hub vuelve a Inicio en vez de cerrarse a los 30.
  - La fuente Medium se intenta bajar una sola vez por sesión.
- **Obsidian**: se mantiene como tema heredado y queda declarado como «Minimal + paleta obsidian» para la migración; una prueba impide que sus colores diverjan.

## v3.11 · Craftinador: preparado para publicarse en GitHub
- **Nuevo nombre visible: Craftinador** (ventana, cabecera, navegador y textos de Steam). Las carpetas no cambian (`~/Games/recomp-hub`, `~/.config/recomp-hub`), ni los nombres de los zips de actualización.
- La autoactualización reconoce las dos marcas (`✓ Recomp Hub` y `✓ Craftinador`): las versiones anteriores se siguen actualizando solas.
- **Licencia GPL-3.0** (`LICENSE`), material de terceros en `THIRD_PARTY.md`, README nuevo en inglés y en español, este historial pasa a `CHANGELOG.md`, `CONTRIBUTING.md` y `SECURITY.md`.
- `.gitignore` completo: datos, credenciales, cookies, registros, temporales y artefactos de entrega nunca entran en el repositorio.
- `tools/make_release.py`: construye `install-hub-vX.sh` y `recomp-hub-update-vX.zip` desde el repositorio; lo usa GitHub Actions al publicar una etiqueta `vX`.
- Repositorio: plantillas de issues (fallo, sugerencia, pedir un juego), pruebas automáticas en cada cambio y release automática.

## v3.12 · Forgeinator 3000
- **Nombre definitivo: Forgeinator 3000** («Forgeinator» en la cabecera; «Forgeinator 3000» en la ventana). Lema: *«¡Contempla el Forgeinator 3000! Forja ports sueltos en juegos jugables»*.
- Repositorio: `github.com/pascaltll/Forgeinator`.
- La autoactualización acepta las tres marcas (`✓ Recomp Hub`, `✓ Craftinador`, `✓ Forgeinator`). Las carpetas siguen igual (`~/Games/recomp-hub`).
- Arreglado (visto en las pruebas de GitHub, con fuentes Noto como las de Bazzite):
  - «MAYÚS», «PÁG. ANTERIOR / SIGUIENTE», «MÁS ANTIGUAS…» y los pliegues de la ficha (+ / –) ya no usan símbolos que Noto Sans no trae (⇧ ▲ ▼ ▸), que salían como «^» o «>».
  - En la ficha, a 1920×1080, el panel «Archivo del juego» medía en unidades sin escalar y sus botones de abajo pisaban «VERSIONES».

## v3.13 · Logo e identidad de Forgeinator 3000
- **Logo original:** un yunque de acero con un cartucho al rojo vivo, chispas y la placa amarilla «3000». La palabra «FORGEINATOR» va en Chakra Petch.
- **Piezas en `assets/brand/`:**
  - icono (512, 256, 128; versión sin placa para 64 y 32);
  - arte de Steam y del QAM: cápsula 600×900, cabecera 920×430 y 460×215, fondo 1920×620 y logo transparente;
  - vista previa para GitHub 1280×640 y banner del README.
  Todo se genera desde SVG con `tools/brand/make_brand.py`.
- **La ventana** lleva el icono de Forgeinator.
- **`qam-app.json`:** el QAM Rail reconoce Forgeinator con su nombre, `bin/hub` y su arte (al instalar desde un zip conserva `data/`).
- El README abre con el banner.

## v3.14 · Rendimiento medido
Medido en 17 pantallas × 6 temas × calidad alta/rendimiento, a 1280×800 y 1920×1080, con un perfilador y un contador de accesos a disco y red en el hilo de la interfaz.
- **Sin lecturas de disco en cada fotograma.** Algunas pantallas volvían a leer archivos 45 veces por segundo:
  - Ajustes: 7 archivos y 3 carpetas por fotograma (`update.json`, claves, `credentials.json`, `buildlog.jsonl`, `launch-logs/`, Proton…). `buildlog.jsonl` y `launch-logs/` crecen con el uso.
  - Ficha: `links.json`.
  - Ajustes y Buscar, sin la variable `GITHUB_TOKEN`: `credentials.json` (la sesión de GitHub).
  - Explorador de archivos: `settings.json`.

  Ahora esos datos se leen una vez y se vuelven a leer tras cada pulsación, cuando cambia el archivo (`links.json`, `credentials.json`, `update.json`, el resumen de pruebas) o, como mucho, cada 2–10 s si otro proceso cambia lo demás. Resultado: 0 lecturas por fotograma.
- **30 fps en reposo.** Tras 5 s sin tocar nada y sin fondo animado (calidad «rendimiento», «equilibrado» o menos movimiento), Hub dibuja a 30 fps en vez de 45. La primera pulsación vuelve a 45. Con fondo animado no cambia nada.
- **PEGAR** en el teclado en pantalla abre un solo proceso del portapapeles (antes, dos).
- **hub.log con tope durante la sesión:** al pasar de 8 MB, lo anterior se mueve a `hub.log.old`. Antes solo se rotaba al arrancar (> 1 MB).
- **Comprobado sin cambios necesarios:**
  - memoria estable al recorrer todos los temas, calidades y paletas (deja de crecer en la 2.ª vuelta);
  - cachés con tope;
  - ninguna conexión de red en el hilo de la interfaz;
  - la petición de apariencia se mira como mucho 1 vez por segundo con un `stat`;
  - recalcular un tema cuesta 0,016 ms;
  - hilos acotados.

## v3.15 · Canales estable y dev, app del QAM y logo pixel art
- **Estable y dev a la vez.** Cada copia del programa sabe su canal por el archivo `CHANNEL`:
  - estable en `~/homebrew/qam-apps/forgeinator`; se actualiza desde el QAM con las releases de GitHub;
  - dev en `~/homebrew/qam-apps/forgeinator-dev`; se actualiza como siempre, con los zip de `~/Games/actualizaciones`.
- **Qué comparten y qué no:**
  - biblioteca común (juegos, descargas, ROMs enlazadas, arte, cachés) en `~/.local/share/forgeinator`;
  - claves comunes en `~/.config/forgeinator`;
  - ajustes de cada canal en `~/.config/forgeinator/<canal>`;
  - registros de cada canal en `~/.local/state/forgeinator/<canal>`.

  El programa ya no escribe dentro de su carpeta.
- **Canal activo:** solo esa copia ajusta los atajos de los juegos en Steam y la apariencia que leen el lanzador y el QAM. Se elige en Ajustes › Mantenimiento › Canal o con `bin/forgeinator --canal estable|dev|estado`.
- **Red de seguridad:** si dev no llega a funcionar 20 s en dos arranques seguidos y la estable está instalada, la activa vuelve a ser la estable, con un aviso.
- **Migración desde `~/Games/recomp-hub`:**
  - la primera vez que se abre una copia del QAM, `data/` se copia a la biblioteca común; las carpetas pesadas van con enlaces duros, así que no ocupan más disco;
  - los .json se reescriben con las rutas nuevas y las claves pasan a `~/.config/forgeinator` con permisos 600;
  - no se borra ni se mueve nada del origen;
  - el atajo antiguo abre la copia activa del QAM (`HUB_LEGACY=1` abre la vieja).
- **`bin/forgeinator`** es el nuevo punto de entrada:
  - `--active` abre la copia activa;
  - `--qam-status` da una línea JSON en menos de 2 s (versión, canal y avisos);
  - `--where` muestra las carpetas de la copia.
- **Paquetes:** `tools/make_release.py` genera además:
  - `forgeinator-X.zip`: app del QAM, con `qam-app.json` esquema 1, `install.sh` y `CHANNEL`;
  - `SHA256SUMS` con las sumas de todo;
  - con `--dev`, `forgeinator-dev-X.zip`.

  La release de GitHub publica también el zip estable y las sumas. El zip de actualización de siempre respeta el canal de la copia (conserva su `CHANNEL` y regenera su `qam-app.json`).
- **Logo:**
  - el cartucho pixel art con un martillo golpeando el yunque (`tools/brand/pixel_logo.py` → `cartucho.svg`);
  - toda la identidad (iconos, arte de Steam, GitHub, README) se ha regenerado con él, sobre fondo morado noche.

## v3.16 · Juegos visibles cuando el Hub se abre desde el QAM
- **El problema:** abierto desde el QAM, el Hub no es un «juego de Steam» (no tiene `SteamGameId`). Por eso lanzaba los juegos directamente, sin pasar por Steam, y en el Modo Juego gamescope no los mostraba. El juego seguía en marcha, invisible, y el Hub se cerraba.
- **Ahora:** en el Modo Juego (gamescope en marcha) los juegos se lanzan siempre por su atajo de Steam, venga de donde venga el Hub.
- **Si el juego no tiene atajo:** el Hub pregunta antes de lanzarlo a pelo. Desde la ficha se puede añadir a Steam, y queda la opción «Lanzar de todos modos».

## v3.17 · Atajos de Steam automáticos con QAM Rail
- **Objetivo:** al pulsar JUGAR en el Modo Juego, un juego sin atajo de Steam queda reconocido por Steam como cualquier otro, con su nombre y su arte en la barra lateral, su perfil de TDP y su tiempo de juego.
- **Cómo:** el Hub pide a QAM Rail, por el socket local `$XDG_RUNTIME_DIR/qam-rail.sock`, que cree el atajo en caliente con el arte del juego y lo lance. No hay que cerrar Steam ni pasar al escritorio. El contrato está en el proyecto: `claude/forgeinator-qam-atajos.md`.
- **Qué hace el Hub:**
  - escribe `launcher/shortcuts/<id>.sh` si el launcher no lo generó;
  - recuerda el appid de cada atajo en la biblioteca común (`steam-appids.json`).
- **Sin QAM Rail** (o con una versión que aún no lo sabe hacer), todo sigue como en v3.16.
- **Arreglo · el botón del QAM abría un juego.**
  - **Qué pasaba:** el botón del QAM le llega al Hub como «guía + A» (el atajo de Steam para abrir el QAM). Dentro de un mismo informe del mando, la A va antes que la guía, así que se procesaba primero y pulsaba lo que tuviera el foco: JUGAR abría el juego, sin verse, detrás del QAM.
  - **Ahora:** cada botón espera 0,12 s antes de procesarse. Si la guía llega dentro de ese margen, el botón se descarta y queda anotado en hub.log como `[foco] A junto al botón Steam/guía`. Las direcciones no esperan.

## v3.18 · El botón del QAM ya no pulsa lo que hay en pantalla
- **Qué pasaba:** en el Modo Juego, el botón del QAM también le llega al Hub como un clic en la pantalla, que pulsaba lo que hubiera debajo. Si debajo estaba JUGAR, el juego se abría detrás del QAM.
- **Clics de ratón instantáneos** (pulsar y soltar en menos de 30 ms, como los que genera el sistema): ahora esperan 0,25 s. Si en ese tiempo se abre un menú de Steam, se pierde el foco o llega el botón guía, el clic se descarta.
- **Clics con un menú de Steam encima, sin foco o justo después del botón guía:** no se cuentan.
- **Lo que no cambia:** el dedo en la pantalla táctil y el escritorio funcionan igual que antes.
- **Registro:** cada caso queda en hub.log con la etiqueta `[toque]`.

## v3.19 · Un mismo zip de actualización sirve para todas las copias
- **Qué pasaba:** el primero que aplicaba `recomp-hub-update-vX.zip` lo movía a `~/Games/actualizaciones/aplicadas/`, y las demás copias dejaban de verlo. Así, si la instalación antigua se actualizaba primero, la copia dev se quedaba sin la versión nueva.
- **Ahora:** las copias con canal (dev) también buscan en `aplicadas/` y nunca mueven el zip. Solo lo aparta la instalación antigua.
