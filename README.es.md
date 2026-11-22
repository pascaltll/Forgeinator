# Forgeinator 3000

> *¡Contempla el Forgeinator 3000! Forja ports sueltos en juegos jugables.*

**Una herrería de recompilaciones de consola y ports de PC para portátiles con Linux.** Forgeinator reúne ports y recompilaciones hechos por la comunidad desde muchas fuentes (releases de GitHub, catálogos, tus propios servidores) y los convierte en juegos que se abren desde el Modo Juego de Steam. Los descarga, los compila si hace falta, los instala, los mantiene al día y los lanza, con **táctil y mando**, sin teclado ni ratón.

> Antes se llamaba **Recomp Hub** (y por poco tiempo, Craftinador). [Read in English](README.md)

Forgeinator **nunca descarga juegos**. Cada port necesita tu propia copia legal del juego original. Forgeinator te dice qué archivo pide el port (serial, formato, hash), lo reconoce cuando se lo das y lo coloca donde el port lo busca.

## Qué hace

- **Catálogo** de ports y recompilaciones, cada uno enlazado al repositorio de su proyecto. Importa listas en formato `apps.json` o añade repositorios a mano.
- **Ficha del juego**: última release, builds disponibles para Linux y Windows, qué necesita el port de tu juego y el README del proyecto resumido.
- **Descargas**: gestor propio con cola, varias conexiones por archivo, pausa y reanudar (también tras reiniciar), reintentos y verificación SHA-256.
- **Instalación**: abre zip, 7z, rar, tar, AppImage, instaladores `.run` y builds de Windows de un solo `.exe`, encuentra el ejecutable y registra el juego en el launcher unificado.
- **Builds de Windows con Proton** (`umu-run`), también instaladores Setup, con un prefijo por juego y tus imágenes de disco como unidades.
- **Compilar desde el código** dentro de un contenedor distrobox (CMake, Meson, Cargo, Makefile o tu comando) cuando el proyecto no publica build.
- **Arranque directo**: los juegos se abren al momento, sin la pantalla de actualización del launcher, también desde sus accesos de Steam.
- **Steam**: accesos con arte (SteamGridDB) para que cada juego salga con su nombre en Big Picture.
- **Tus archivos del juego**: se reconocen por hash o serial desde un selector o vigilando tu carpeta de descargas, y se enlazan en una biblioteca con estructura ES-DE.
- **Temas**: 15 temas clásicos con 59 paletas y 8 identidades experimentales del «Estudio». Accesibilidad: movimiento reducido, alto contraste, texto grande; tres niveles de calidad.

## Requisitos

- Linux con el Modo Juego de Steam / Gamescope (desarrollado y probado en **Bazzite**, ROG Ally). El modo escritorio también funciona.
- Python **3.11+** y [`pygame-ce`](https://pyga.me/): `pip install --user --break-system-packages pygame-ce`
- Opcional: `umu-run` (builds de Windows con Proton; viene en Bazzite), `distrobox` (compilar), `7z`/`unar` (archivos 7z y rar).

## Instalar

Descarga `install-hub-vX.sh` de la [última release](../../releases/latest) y ejecuta:

```bash
bash install-hub-vX.sh            # instala en ~/Games/recomp-hub
FORCE=1 bash install-hub-vX.sh    # reinstala el código; tu data/ se conserva
~/Games/recomp-hub/bin/hub        # abre la interfaz
```

Añade `~/Games/recomp-hub/bin/hub` a Steam como juego no-Steam para usarlo desde el Modo Juego. Las versiones siguientes se aplican solas: deja el `recomp-hub-update-vX.zip` en `~/Games/actualizaciones`. La instalación desde el QAM y las actualizaciones desde las releases de GitHub están en camino (ver la hoja de ruta).

## Controles

| | Mando | Táctil |
|---|---|---|
| Moverse | cruceta / stick izquierdo | tocar |
| Abrir / pulsar | A | tocar |
| Atrás | B | botón ‹ ATRÁS |
| Acciones extra | X / Y (se ven abajo) | botones |
| Pestañas | LB / RB | pestañas arriba |
| Desplazar | cruceta | arrastrar (con inercia) |
| Menú del juego | Y (sobre un juego) | mantener pulsado |

## Tus datos y tu privacidad

Tus ajustes, descargas, registros y copias viven en `data/`, dentro de la carpeta de instalación. El token de GitHub se guarda en `~/.config/recomp-hub/credentials.json`, fuera del proyecto. Nada de eso forma parte de este repositorio ni se envía a ningún sitio. Forgeinator solo habla con GitHub y con los servicios que configures (SteamGridDB, ScreenScraper, tu propio servidor de catálogo).

## Desarrollo

```bash
git clone https://github.com/pascaltll/Forgeinator && cd Forgeinator
python3 -m pip install --user pygame-ce pytest
python3 -m pytest tests -q          # ~1400 pruebas, sin pantalla (driver SDL dummy)
python3 main.py                     # ejecutar desde el código
```

Estructura: `hub/` (la aplicación), `bin/` (arranque, actualización, doctor y pruebas), `catalog/` (catálogo base y sistemas de ES-DE), `browser/` (navegador integrado opcional), `assets/` (iconos y logos de consola), `tests/`.

Mira [CONTRIBUTING.md](CONTRIBUTING.md). Historial de versiones: [CHANGELOG.md](CHANGELOG.md).

## Hoja de ruta

1. Repositorio público (este paso).
2. App instalable: programa y datos separados, instalación desde el QAM, actualizaciones desde las releases de GitHub.
3. Informes de error con los secretos tapados y un toque para abrir un issue de GitHub ya rellenado.
4. **Forgeinator Link**: vincula tu teléfono con un QR en tu red local para enviar claves, cookies y archivos grandes (ISO) a tu biblioteca.
5. Bibliotecas remotas (WebDAV, SMB, SFTP, nubes) con estructura ES-DE y un protocolo documentado para servidores de catálogo.

## Licencia

Forgeinator es software libre bajo la **GNU General Public License v3.0**. Ver [LICENSE](LICENSE). El material de terceros y sus licencias están en [THIRD_PARTY.md](THIRD_PARTY.md).

No está afiliado a Valve, Sony, Nintendo, Microsoft, Sega ni a ninguna otra empresa. Los nombres y logos de consolas son marcas de sus dueños y solo se muestran para identificar plataformas.
