"""v3.10 · Arranque directo: abre un juego del launcher SIN su pantalla (comprobación de actualizaciones, novedades, cuenta atrás).
Las actualizaciones ya las gestiona Hub. Usa el propio código del launcher para construir el comando (exe, argumentos, carpeta,
entorno y registro de [run] del .toml), así que el juego arranca igual que con `bin/play <id>`, solo que sin la ventana previa.

Uso:  python3 playdirect.py [--root <carpeta del launcher>] <id> [argumentos del juego…]
Si algo falla ANTES de arrancar el juego (launcher distinto, .toml con error, faltan archivos de [run].require…), se cede a
`bin/play <id>`, que muestra su pantalla con el motivo: nunca deja al usuario sin juego.
No importa nada de Hub (arranca en milisegundos y no depende de pygame)."""
import os
import sys
from pathlib import Path

LAUNCHER = Path(os.environ.get("LAUNCHER_DIR") or Path.home() / "Games" / "launcher")


def _fallback(lid, extra, why):
    play = LAUNCHER / "bin" / "play"
    print(f"[arranque directo] {lid}: {why} → se usa {play}", file=sys.stderr, flush=True)
    if play.exists():
        os.execv(str(play), [str(play), lid, *extra])
    return 3


def main(argv):
    global LAUNCHER
    if argv[:1] == ["--root"] and len(argv) >= 2:
        LAUNCHER, argv = Path(argv[1]), argv[2:]
    if not argv:
        print("uso: playdirect.py <id> [argumentos]", file=sys.stderr)
        return 2
    lid, extra = argv[0], argv[1:]
    # el mismo trato que bin/play: el juego recupera el LD_LIBRARY_PATH original de la sesión
    if "LAUNCHER_ORIG_LD_LIBRARY_PATH" not in os.environ:
        os.environ["LAUNCHER_ORIG_LD_LIBRARY_PATH"] = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ.pop("LD_LIBRARY_PATH", None)
    try:
        sys.path.insert(0, str(LAUNCHER))
        from core import config, runner          # noqa: E402  (código del launcher instalado)
        game = config.load_game(lid)
        miss = runner.missing(game) if hasattr(runner, "missing") else []
        if miss:
            return _fallback(lid, extra, f"faltan archivos del juego ({miss[0]})")
        launch = runner.build(game, extra)
        try:
            from core.log import setup             # mismo registro que el launcher: state/<id>.log
            setup(game.id).info("arranque directo desde Recomp Hub (sin pantalla del launcher): %s", launch.cmd)
        except Exception:  # noqa: BLE001
            pass
    except Exception as ex:  # noqa: BLE001
        return _fallback(lid, extra, f"{type(ex).__name__}: {ex}")
    print(f"[arranque directo] {lid}: {launch.cmd}", file=sys.stderr, flush=True)
    launch.exec()                                  # no vuelve
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
