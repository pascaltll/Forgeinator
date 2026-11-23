#!/usr/bin/env python3
"""Forgeinator (antes Recomp Hub): catálogo de ports/recomps + gestor de descargas + instalador → launcher unificado."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub import catalog, config, github  # noqa: E402


def main():
    ap = argparse.ArgumentParser(prog="hub", description=__doc__)
    ap.add_argument("--list", action="store_true", help="lista el catálogo")
    ap.add_argument("--import", dest="imp", metavar="URL|ARCHIVO", help="importa una lista apps.json")
    ap.add_argument("--update-awesome", action="store_true", help="actualiza la lista de proyectos de awesome-decomp-games (data/imports/00-awesome-decomp.json)")
    ap.add_argument("--import-community", action="store_true", help="importa el catálogo comunitario de Quiver (~230 juegos)")
    ap.add_argument("--add", metavar="owner/repo", help="añade un repositorio a tu catálogo")
    ap.add_argument("--status", action="store_true", help="muestra qué juegos detecta como instalados y dónde")
    ap.add_argument("--latest", metavar="ID", help="muestra la última release y el asset elegido")
    ap.add_argument("--fetch", metavar="ID", help="descarga e instala por terminal (sin interfaz)")
    ap.add_argument("--steam-setup", action="store_true", help="abre directamente la pantalla «Preparar Steam» (la usa el cambio al escritorio)")
    a = ap.parse_args()
    if config.CHANNEL and not os.environ.get("HUB_DATA"):
        # v3.15: primera vez como app del QAM: copia (sin borrar ni mover nada) lo de ~/Games/recomp-hub/data a la biblioteca común
        # y da a este canal sus ajustes. Pasa una sola vez; el informe queda en ~/.local/share/forgeinator/.migrado
        from hub import channel
        try:
            rep = channel.migrate()
            if rep.get("hecho"):
                print(f"[canal] biblioteca común preparada desde {rep.get('origen') or 'cero'}: {len(rep['copiado'])} copiados, "
                      f"pesados {rep['pesado'] or '—'}, omitidos {len(rep['omitido'])}", file=sys.stderr, flush=True)
            src = channel.seed_settings()
            if src not in ("propios", ""):
                print(f"[canal] ajustes de {channel.LABEL[channel.CHANNEL]} tomados de {src}", file=sys.stderr, flush=True)
        except Exception as ex:  # noqa: BLE001
            print(f"[canal] no se pudo preparar la biblioteca común: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
    config.load_env()
    if a.steam_setup:
        os.environ["HUB_START"] = "steam"
    if a.update_awesome:
        from hub import indexers
        try:
            r = indexers.update()
        except Exception as ex:  # noqa: BLE001
            sys.exit(f"No pude actualizar: {type(ex).__name__}: {ex}")
        print(f"{r['listos']} listos para usar + {r['solo_codigo']} solo código ({r['sin_mantenimiento']} sin mantenimiento) → {r['path']}")
        return
    if a.import_community:
        dest, n = catalog.import_source(catalog.COMMUNITY_INDEX)
        print(f"{n} juegos importados del catálogo comunitario")
    elif a.imp:
        if a.imp.upper() in ("URL_RAW", "URL", "ARCHIVO") or a.imp.startswith("<"):
            sys.exit("Sustituye eso por una URL real (https://…/apps.json) o la ruta de un archivo .json")
        try:
            dest, n = catalog.import_source(a.imp)
        except FileNotFoundError:
            sys.exit(f"No existe el archivo: {a.imp}")
        except Exception as ex:  # noqa: BLE001
            sys.exit(f"No pude importar: {type(ex).__name__}: {ex}")
        print(f"{n} juegos → {dest}")
    elif a.add:
        repo = catalog.repo_of(a.add)
        if not repo:
            sys.exit("repositorio no válido")
        e = catalog.add_local({"name": repo.split("/")[1], "repo": repo, "folder": repo.split("/")[1]})
        print("añadido:", e["id"], e["repo"])
    elif a.status:
        from hub import install
        lg = install.launcher_games()
        print(f"launcher: {config.LAUNCHER}  ({len(lg)} juegos registrados)")
        for e in catalog.load():
            i = install.installed_info(e, lg)
            print(f"{'SI' if i['installed'] else '--'}  {e['id']:<22} v={i['version'] or '-':<12} {i['dir']}  (launcher id: {i['launcher_id']})")
    elif a.list:
        for e in catalog.load():
            print(f"{e['id']:<24} {e['platform'][:14]:<14} {e['repo']:<44} {e['name']}")
    elif a.latest or a.fetch:
        e = next((x for x in catalog.load() if x["id"] == (a.latest or a.fetch)), None)
        if not e:
            sys.exit("id no encontrado (usa --list)")
        r = github.latest(e["repo"], config.settings()["arch"], force=True, filt=e.get("asset_filter", ""))
        if r.get("error") and not r.get("tag"):
            sys.exit("GitHub: " + r["error"])
        print(f"{e['name']}: {r['tag']} ({r['published']})")
        for i, x in enumerate(r["assets"]):
            print(f"  {'*' if i == 0 else ' '} {x['name']}  {x['size'] / 1e6:.1f} MB  {x['class']}")
        if a.fetch:
            if not r["assets"]:
                sys.exit("sin build compatible")
            import time
            from hub import downloads, install
            m = downloads.Manager(max_active=1)
            s = r["assets"][0]
            d = m.add(s["url"], config.path("downloads_dir"), name=s["name"], sha256=s.get("sha256"))
            while d.state in ("queued", "active"):
                print(f"\r{d.progress * 100:5.1f}%  {d.speed / 1e6:5.1f} MB/s", end="", flush=True)
                time.sleep(0.5)
            print()
            if d.state != "done":
                sys.exit(d.error or d.state)
            res = install.install(e, d.path, s["name"], r["tag"])
            print("instalado en", res["dir"], "| exe:", res["exe"] or "(no detectado)", "| toml:", res["toml"])
            m.shutdown()
    else:
        import faulthandler
        import logging
        faulthandler.enable()
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
        log = logging.getLogger("hub")
        sys.excepthook = lambda t, v, tb: log.error("excepcion no controlada", exc_info=(t, v, tb))
        log.info("python %s | args UI | datos %s | launcher %s", sys.version.split()[0], config.DATA, config.LAUNCHER)
        if config.CHANNEL:
            from hub import channel
            if channel.safety_check():
                log.warning("dev falló %d arranques seguidos: el canal activo vuelve a ser Estable", channel.BOOT_LIMIT)
            n = channel.boot_begin()
            if n:
                log.info("canal dev: arranque %d (se confirma a los %.0f s con la interfaz funcionando)", n, channel.BOOT_OK_AFTER)
        try:
            import pygame
            log.info("pygame %s SDL %s", pygame.version.ver, pygame.version.SDL)
            from hub.ui import UI
            drv = os.environ.get("SDL_VIDEODRIVER")
            ui = None
            # Big Picture/Gamescope: si el driver elegido falla, prueba los demas
            for d in ([drv] if drv else []) + [None, "x11", "wayland"]:
                try:
                    if d:
                        os.environ["SDL_VIDEODRIVER"] = d
                    elif d is None and drv:
                        os.environ.pop("SDL_VIDEODRIVER", None)
                    pygame.display.quit()
                    ui = UI()
                    log.info("ventana %dx%d driver=%s", ui.W, ui.H, pygame.display.get_driver())
                    break
                except Exception:  # noqa: BLE001
                    log.exception("fallo al abrir ventana con driver=%s", d or "auto")
            if ui is None:
                sys.exit("no se pudo abrir ninguna ventana (mira data/hub.log)")
            ui.run()
            log.info("cierre normal")
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001
            log.exception("error fatal")
            sys.exit(1)


if __name__ == "__main__":
    main()
