![Forgeinator 3000 — Behold, the Forgeinator 3000! It forges scattered ports into playable games.](assets/brand/readme-banner.png)

# Forgeinator 3000

> *Behold, the Forgeinator 3000! It forges scattered ports into playable games.*

**A forge for console recompilations and PC ports on Linux handhelds.** Forgeinator gathers fan-made ports and recompilations from many sources (GitHub releases, catalogs, your own servers) and turns them into games you can play from Steam's Game Mode. It downloads them, builds them if needed, installs them, keeps them updated and launches them, with **touch and gamepad** controls, no keyboard or mouse needed.

> Formerly **Recomp Hub** (and briefly Craftinador). [Leer en español](README.es.md)

Forgeinator **never downloads games**. Every port needs your own legally obtained copy of the original game. Forgeinator tells you which file a port expects (serial, format, hash), recognizes it when you provide it, and places it where the port looks for it.

## Features

- **Catalog** of ports and recompilations, each linked to its project repository. Import lists in `apps.json` format or add repositories by hand.
- **Game page**: latest release, the available builds for Linux and Windows, what the port needs from your game, the project README summarized.
- **Downloads**: its own download manager with queue, several connections per file, pause/resume (also after a restart), retries and SHA-256 verification.
- **Install**: unpacks zip, 7z, rar, tar, AppImage, `.run` installers and single Windows `.exe` builds, finds the executable and registers the game in the unified launcher.
- **Windows builds through Proton** (`umu-run`), including Setup installers, with a per-game prefix and your disc images linked as drives.
- **Build from source** inside a distrobox container (CMake, Meson, Cargo, Makefile or your own command) when a project publishes no build.
- **Direct start**: games open straight away, without the launcher's update screen, also from their Steam shortcuts.
- **Steam**: shortcuts with artwork (SteamGridDB) so each game shows with its own name in Big Picture.
- **Your game files**: recognized by hash or serial from a file picker or a watched downloads folder, linked into an ES-DE style library.
- **Remote libraries**: WebDAV, Samba, SFTP, FTP, any rclone remote or a mounted folder, browsed by system (ES-DE layout) and downloaded by a background service (`forgeinatord`) that keeps going after you close the Hub.
- **Plugins**: extra connectors installed from a zip (Settings › Files › Plugins), for servers with their own API. Includes "Catálogo HTTP v1". How to write one: [docs/PLUGINS.md](docs/PLUGINS.md); connections and APIs: [docs/PROTOCOL.md](docs/PROTOCOL.md).
- **Error reports and suggestions**: preview with tokens, cookies and your user name redacted; save as a zip or open a prefilled GitHub issue.
- **Themes**: 15 classic themes with 59 palettes, plus 8 experimental "Studio" identities. Accessibility options: reduced motion, high contrast, large text; three quality levels.

## Requirements

- Linux with Steam Game Mode / Gamescope (developed and tested on **Bazzite**, ROG Ally). Desktop mode also works.
- Python **3.11+** and [`pygame-ce`](https://pyga.me/): `pip install --user --break-system-packages pygame-ce`
- Optional: `umu-run` (Windows builds through Proton, preinstalled on Bazzite), `distrobox` (building from source), `7z`/`unar` (7z and rar archives).

## Install

**As a QAM app (recommended, with [QAM Rail](https://github.com/pascaltll/qam-rail) 0.51 or later):** Apps › Install app › From GitHub › `pascaltll/Forgeinator`. QAM Rail downloads `forgeinator-X.zip` from the [latest release](../../releases/latest), checks its SHA-256, installs it into `~/homebrew/qam-apps/forgeinator` and tells you when a new version is out.

**By hand** (without QAM Rail): unzip `forgeinator-X.zip` into `~/homebrew/qam-apps/` and run `~/homebrew/qam-apps/forgeinator/install.sh`. To open it: `~/homebrew/qam-apps/forgeinator/bin/forgeinator` (add it to Steam as a non-Steam game for Game Mode).

### Channels: stable and dev side by side
| | Stable | Dev |
|---|---|---|
| Folder | `~/homebrew/qam-apps/forgeinator` | `~/homebrew/qam-apps/forgeinator-dev` |
| Updated by | the QAM (GitHub releases) | `recomp-hub-update-vX.zip` in `~/Games/actualizaciones` |
| Settings | `~/.config/forgeinator/stable` | `~/.config/forgeinator/dev` |

Both share the library (`~/.local/share/forgeinator`: games, downloads, linked ROMs, art) and the keys (`~/.config/forgeinator`). Only the **active** copy updates the games' Steam shortcuts and the appearance read by the launcher and the QAM. Pick it in Settings › Maintenance › Channel, or with `bin/forgeinator --canal estable|dev|estado`. If dev fails to start twice in a row, stable becomes active again on its own.

`bin/forgeinator --active` always opens the active copy (handy for a single Steam shortcut).

**Old install** (`~/Games/recomp-hub`, from `install-hub-vX.sh`): still works. If you also have Forgeinator in the QAM, the first time a QAM copy opens it copies your `data/` into the shared library (nothing is deleted or moved; big folders are hard-linked), and the old shortcut opens the active QAM copy. `HUB_LEGACY=1` opens the old one anyway.

## Controls

| | Gamepad | Touch |
|---|---|---|
| Move | D-pad / left stick | tap |
| Open / press | A | tap |
| Back | B | ‹ BACK button |
| Extra actions | X / Y (shown at the bottom) | buttons |
| Tabs | LB / RB | tabs at the top |
| Scroll | D-pad | drag (with inertia) |
| Game menu | Y (on a game) | long press |

## Your data and privacy

Your library lives in `~/.local/share/forgeinator`, your settings in `~/.config/forgeinator/<channel>` and logs in `~/.local/state/forgeinator/<channel>` (on an old install, everything is in `data/`). Your GitHub token is stored in `~/.config/forgeinator/credentials.json` with 600 permissions, outside the program. None of it is part of this repository and none of it is sent anywhere. Forgeinator only talks to GitHub and the services you configure (SteamGridDB, ScreenScraper, your remote libraries and the servers your plugins connect to).

## Development

```bash
git clone https://github.com/pascaltll/Forgeinator && cd Forgeinator
python3 -m pip install --user pygame-ce pytest
python3 -m pytest tests -q          # ~1400 tests, headless (SDL dummy driver)
python3 main.py                     # run from the source tree
```

Layout: `hub/` (application), `bin/` (launch, update, doctor and test scripts; `forgeinatord` is the background service, `forgeinator-ctl` the headless control), `plugins/` (example plugins), `docs/` (protocols and plugin guide), `catalog/` (base catalog and ES-DE systems), `browser/` (optional embedded browser), `assets/` (icons and console logos), `tests/`.

See [CONTRIBUTING.md](CONTRIBUTING.md). Version history: [CHANGELOG.md](CHANGELOG.md) (in Spanish).

## Roadmap

1. ~~Public repository.~~ Done (3.12).
2. ~~Installable app: program and user data separated, stable and dev channels, install from the QAM, updates from GitHub releases.~~ Done (3.15–3.19).
3. ~~Error reports with secrets redacted, one tap to open a prefilled GitHub issue.~~ Done (3.24).
4. **Forgeinator Link**: pair your phone through a QR code on your local network to send API keys, cookies and large files (ISOs) into your library.
5. ~~Remote libraries with an ES-DE folder layout, a background download service, plugins and documented protocols.~~ Done (3.22–3.25); next: the QAM "Downloads" card.

## License

Forgeinator is free software under the **GNU General Public License v3.0**. See [LICENSE](LICENSE). Third-party material and its licenses are listed in [THIRD_PARTY.md](THIRD_PARTY.md).

Not affiliated with Valve, Sony, Nintendo, Microsoft, Sega or any other company. Console names and logos are trademarks of their owners, shown only to identify platforms.
