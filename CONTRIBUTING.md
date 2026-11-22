# Contributing / Contribuir

Thanks for helping! / ¡Gracias por ayudar! (Spanish or English are both fine / Español o inglés, como prefieras.)

## Reporting a bug / Informar de un fallo
Open an issue with the **Bug report** template. Attach `data/hub.log` (Settings › Maintenance › Logs). **Before attaching anything, check it contains no tokens, cookies or passwords.**
Abre un issue con la plantilla **Bug report** y adjunta `data/hub.log`. **Revisa antes que no lleve tokens, cookies ni contraseñas.**

## Asking for a game / Pedir un juego
Use the **Game request** template with the project repository. Forgeinator only lists projects that do not distribute copyrighted game files.
Usa la plantilla **Game request** con el repositorio del proyecto. Solo se listan proyectos que no distribuyen archivos de juegos con copyright.

## Code / Código
- Python 3.11+, `pygame-ce`. No other runtime dependencies on purpose: keep it that way unless discussed first.
- Run the tests before a pull request / Pasa las pruebas antes de un pull request:
  ```bash
  python3 -m pytest tests -q
  ```
- New behaviour comes with a test in `tests/` (one file per version, `test_vXYZ.py`, is the current convention).
- The 15 classic themes must stay pixel-identical unless the change is about them (there is a pixel comparison workflow in the changelog notes).
- Never delete user files: move them aside or back them up (`.prev`, `.bak`, `data/backups/`).
- User-facing text is in Spanish today; translations are welcome (roadmap: translatable strings).

By contributing you agree that your contribution is licensed under the GPL v3.0.
Al contribuir aceptas que tu aportación se publica bajo la GPL v3.0.
