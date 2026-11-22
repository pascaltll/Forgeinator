"""Navegador de Hub (Qt WebEngine): pensado para Big Picture/Gamescope en una consola portátil.
Pantalla completa, botones grandes, arrastrar para desplazarse (táctil), zoom, teclado de Steam al tocar un campo de texto,
bloqueo de pop-ups y DESCARGAS NATIVAS a la carpeta de Hub. Se ejecuta como proceso aparte (bin/hub-browser) con un python que tenga PyQt6.
Habla con Hub por stdout, una línea por mensaje:  HUB repo owner/repo   ·   HUB done /ruta/archivo   ·   HUB start /ruta/archivo."""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

T0 = time.perf_counter()


def log(*a):
    print(f"[browser] +{time.perf_counter() - T0:.1f}s", *a, file=sys.stderr, flush=True)


def say(kind, val=""):
    print(f"HUB {kind} {val}".rstrip(), flush=True)


def repo_of(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?github\.com/([^/\s?#]+)/([^/\s?#]+)", url or "")
    if not m or m.group(1) in ("settings", "login", "orgs", "topics", "search", "marketplace", "sponsors", "features", "about", "pricing", "explore"):
        return ""
    return f"{m.group(1)}/{re.sub(r'[.]git$', '', m.group(2))}"


def unique(dirp: Path, name: str) -> Path:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name) or "descarga"
    p = dirp / name
    n = 1
    while p.exists() or Path(str(p) + ".part").exists():
        p = dirp / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hub-browser")
    ap.add_argument("url", nargs="?", default="https://www.google.com")
    ap.add_argument("--zoom", type=float, default=1.5)
    ap.add_argument("--download-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--profile", default=str(Path.home() / ".local/share/recomp-hub-browser"))
    ap.add_argument("--window", default="", help="WxH en vez de pantalla completa (pruebas)")
    ap.add_argument("--check", action="store_true", help="comprobación rápida: ¿está instalado PyQt6 con WebEngine?")
    ap.add_argument("--check-full", action="store_true", help="comprobación completa (importa Qt WebEngine)")
    a = ap.parse_args(argv)

    if a.check:
        import importlib.util
        try:
            ok = importlib.util.find_spec("PyQt6.QtWebEngineWidgets") is not None
        except (ImportError, ValueError):
            ok = False
        print("ok" if ok else "falta")
        return 0 if ok else 3
    # contadores/temporizadores de páginas de descarga: Chromium los frena si cree que la ventana está en segundo plano (pasa en Gamescope)
    extra = "--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows " + os.environ.get("HUB_BROWSER_FLAGS", "")   # p. ej. --disable-gpu si la aceleración da problemas
    if os.geteuid() == 0:
        extra += " --no-sandbox"
    if extra.strip():
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + " " + extra).strip()
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb" if os.environ.get("DISPLAY") else "wayland")
    try:
        from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer, QUrl
        from PyQt6.QtGui import QKeySequence, QMouseEvent, QShortcut, QWheelEvent
        from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineSettings
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget
    except ImportError as ex:
        print(f"Falta PyQt6 con WebEngine: {ex}", file=sys.stderr)
        return 3
    log("Qt importado")
    if a.check_full:
        print("ok")
        return 0

    try:   # si Hub desaparece, este navegador también (evita ventanas a pantalla completa huérfanas que bloquean la consola)
        import ctypes
        import signal
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)
        if os.getppid() == 1:
            os._exit(0)
    except Exception:  # noqa: BLE001
        pass
    def _hook(t, v, tb):
        import traceback
        log("excepción ignorada:", "".join(traceback.format_exception(t, v, tb))[-400:])
    sys.excepthook = _hook   # sin esto PyQt6 aborta el proceso (SIGABRT, código -6) ante cualquier error en un slot
    app = QApplication(sys.argv[:1])
    log("QApplication creada")
    app.setApplicationName("Forgeinator Browser")
    scr = app.primaryScreen().size()
    ui = max(0.8, min(1.8, scr.height() / 1080.0))

    def px(n):
        return int(n * ui)

    dl_dir = Path(a.download_dir).expanduser()
    dl_dir.mkdir(parents=True, exist_ok=True)
    prof_dir = Path(a.profile).expanduser()
    prof_dir.mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile("hub", app)
    profile.setPersistentStoragePath(str(prof_dir / "storage"))
    profile.setCachePath(str(prof_dir / "cache"))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
    ua = re.sub(r"\s*QtWebEngine/\S+", "", profile.httpUserAgent())
    profile.setHttpUserAgent(ua)
    profile.setDownloadPath(str(dl_dir))

    VISIBLE_JS = """(function(){try{
      Object.defineProperty(document,'hidden',{get:function(){return false;},configurable:true});
      Object.defineProperty(document,'visibilityState',{get:function(){return 'visible';},configurable:true});
      document.hasFocus=function(){return true;};
      window.addEventListener('visibilitychange',function(e){e.stopImmediatePropagation();},true);
      document.addEventListener('visibilitychange',function(e){e.stopImmediatePropagation();},true);
      window.addEventListener('blur',function(e){e.stopImmediatePropagation();},true);
    }catch(e){}})();"""
    sc = QWebEngineScript()
    sc.setName("hub-visible")
    sc.setSourceCode(VISIBLE_JS)
    sc.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    sc.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    sc.setRunsOnSubFrames(True)
    profile.scripts().insert(sc)

    class Page(QWebEnginePage):
        def __init__(self, parent=None):
            super().__init__(profile, parent)
            s = self.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)   # sin pop-ups de scripts
            s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            self.fullScreenRequested.connect(lambda r: r.accept())

        def createWindow(self, _type):
            # enlaces target=_blank: se abren en la misma pestaña, sin ventanas nuevas
            tmp = QWebEnginePage(profile, self)
            tmp.urlChanged.connect(lambda u: (win.view.setUrl(u), tmp.deleteLater()))
            return tmp

        nconsole = 0

        def javaScriptConsoleMessage(self, level, msg, line, src):
            # solo avisos/errores, máximo 40 líneas: ayuda a ver por qué una página (contador, botón) no funciona
            if int(getattr(level, "value", level)) >= 1 and Page.nconsole < 40:
                Page.nconsole += 1
                log(f"js: {msg[:160]} ({str(src)[-60:]}:{line})")

    class DragScroll(QObject):
        """Arrastrar con el dedo/ratón = desplazar (como un móvil). Un toque corto se reenvía como clic."""
        def __init__(self):
            super().__init__()
            self.on = True
            self.down = None
            self.last = None
            self.moved = False
            self.synth = False

        def eventFilter(self, obj, ev):
            if self.synth or not self.on:
                return False
            t = ev.type()
            if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                self.down, self.last, self.moved = ev.position(), ev.position(), False
                return True
            if t == QEvent.Type.MouseMove and self.down is not None and ev.buttons() & Qt.MouseButton.LeftButton:
                p = ev.position()
                if not self.moved and (abs(p.x() - self.down.x()) > px(10) or abs(p.y() - self.down.y()) > px(10)):
                    self.moved = True
                if self.moved:
                    dx, dy = int(p.x() - self.last.x()), int(p.y() - self.last.y())
                    self.last = p
                    if dx or dy:
                        w = QWheelEvent(p, ev.globalPosition(), QPoint(dx, dy), QPoint(dx * 3, dy * 3), Qt.MouseButton.NoButton,
                                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.ScrollUpdate, False)
                        self.synth = True
                        try:
                            QApplication.sendEvent(obj, w)
                        finally:
                            self.synth = False
                return True
            if t == QEvent.Type.MouseButtonRelease and ev.button() == Qt.MouseButton.LeftButton and self.down is not None:
                d, moved = self.down, self.moved
                self.down = None
                if not moved:
                    self.synth = True
                    try:
                        for tp, bt in ((QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton), (QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton)):
                            QApplication.sendEvent(obj, QMouseEvent(tp, d, ev.globalPosition(), Qt.MouseButton.LeftButton, bt if tp == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
                    finally:
                        self.synth = False
                return True
            return False

    class View(QWebEngineView):
        def __init__(self):
            super().__init__()
            self.drag = DragScroll()

        def event(self, e):
            if e.type() == QEvent.Type.ChildAdded:
                ch = e.child()
                if isinstance(ch, QWidget):
                    ch.installEventFilter(self.drag)
            return super().event(e)

    def steam_keyboard():
        for cmd in (["steam", "-ifrunning", "steam://open/keyboard"], ["xdg-open", "steam://open/keyboard"]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    log("teclado:", " ".join(cmd))
                    return
                except OSError:
                    pass

    class Url(QLineEdit):
        def mousePressEvent(self, e):   # solo al tocar la barra (no al arrancar): selecciona todo y pide el teclado de Steam
            super().mousePressEvent(e)
            QTimer.singleShot(0, self.selectAll)
            steam_keyboard()

    class Win(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Forgeinator — navegador")
            self.setStyleSheet(f"""
                QWidget {{ background:#0f1722; color:#e7eefc; font-size:{px(22)}px; }}
                QPushButton {{ background:#1d2a3d; border:2px solid #2b3d57; border-radius:{px(12)}px; padding:{px(10)}px {px(18)}px; min-height:{px(44)}px; }}
                QPushButton:pressed {{ background:#2f6fd6; }}
                QPushButton:disabled {{ color:#5d6b82; border-color:#1d2a3d; }}
                QPushButton#ok {{ background:#1f7a4a; border-color:#2fa066; }}
                QPushButton#bye {{ background:#7a2a2a; border-color:#a04040; }}
                QLineEdit {{ background:#0a1019; border:2px solid #2f6fd6; border-radius:{px(12)}px; padding:{px(8)}px {px(14)}px; min-height:{px(44)}px; }}
                QProgressBar {{ border:none; background:#1d2a3d; height:{px(8)}px; text-align:center; }}
                QProgressBar::chunk {{ background:#2f6fd6; }}
            """)
            self.view = View()
            self.page = Page(self.view)
            self.view.setPage(self.page)
            self.view.setZoomFactor(a.zoom)
            self.zoom = a.zoom
            lay = QVBoxLayout(self)
            lay.setContentsMargins(px(8), px(8), px(8), px(4))
            lay.setSpacing(px(6))
            bar = QHBoxLayout()
            bar.setSpacing(px(6))
            self.btn = {}

            def add(key, label, fn, name="", w=None):
                b = QPushButton(label)
                if name:
                    b.setObjectName(name)
                if w:
                    b.setMinimumWidth(px(w))
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(fn)
                bar.addWidget(b)
                self.btn[key] = b
                return b

            add("back", "◀", self.view.back, w=70)
            add("fwd", "▶", self.view.forward, w=70)
            add("reload", "⟳", self.view.reload, w=70)
            self.url = Url()
            self.url.returnPressed.connect(self.go)
            bar.addWidget(self.url, 1)
            add("kb", "⌨", steam_keyboard, w=70)
            add("zm", "−", lambda: self.setzoom(-0.25), w=60)
            add("zp", "+", lambda: self.setzoom(+0.25), w=60)
            add("drag", "✋", self.toggle_drag, w=70)
            add("repo", "ANALIZAR EN HUB", self.send_repo, "ok")
            add("bye", "VOLVER A HUB", self.leave, "bye")
            lay.addLayout(bar)
            self.prog = QProgressBar()
            self.prog.setTextVisible(False)
            self.prog.setMaximum(100)
            lay.addWidget(self.prog)
            lay.addWidget(self.view, 1)
            self.status = QLabel("")
            self.status.setStyleSheet(f"color:#8fa3c4; font-size:{px(18)}px;")
            lay.addWidget(self.status)
            self.view.urlChanged.connect(self.on_url)
            self.view.loadProgress.connect(lambda v: (self.prog.setValue(v), self.prog.setVisible(v < 100)))
            self.view.titleChanged.connect(lambda t: self.setWindowTitle(t or "Forgeinator"))
            profile.downloadRequested.connect(self.on_download)
            self.editable = False
            self.downloads = {}   # descargas en curso: dest -> petición
            self._bye_t = 0.0
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.poll_focus)
            self.timer.start(700)
            self.view.setUrl(QUrl.fromUserInput(a.url))
            self.btn["repo"].setEnabled(False)
            self.view.setFocus()
            self.view.loadFinished.connect(self._first_load)
            self._told = False
            for k in ("Escape", "Ctrl+Q", "Alt+F4"):   # salidas de emergencia
                QShortcut(QKeySequence(k), self, activated=self.leave)
            self.page.renderProcessTerminated.connect(self._render_died)
            self._deaths = 0

        def _render_died(self, status, code):
            # si el proceso de la página muere, una ventana a pantalla completa se queda congelada: se recarga o se sale
            self._deaths += 1
            log(f"el proceso de la página terminó (estado {int(status.value) if hasattr(status, 'value') else status}, código {code}); n.º {self._deaths}")
            if self._deaths >= 3:
                log("demasiados fallos: cierro el navegador")
                QTimer.singleShot(0, self.close)
            else:
                QTimer.singleShot(500, self.view.reload)

        def _first_load(self, ok):
            if not self._told:
                self._told = True
                log("primera página cargada" if ok else "primera página falló")
            self.page.runJavaScript("[document.visibilityState, document.hasFocus(), navigator.webdriver, navigator.userAgent].join(' | ')",
                                    lambda v: log("página:", self.view.url().host(), "→", v))

        def leave(self):
            """Salir. Con una descarga en curso avisa primero: salir ahora la dejaría a medias."""
            now = time.time()
            if self.downloads and now - self._bye_t > 6:
                self._bye_t = now
                self.status.setText(f"⚠ Hay {len(self.downloads)} descarga(s) en curso. Espera a que terminen, o pulsa VOLVER A HUB otra vez para cancelarlas y salir.")
                return
            self.close()

        def go(self):
            t = self.url.text().strip()
            if not t:
                return
            if " " in t or ("." not in t and "://" not in t and not t.startswith("localhost")):
                from urllib.parse import quote_plus
                t = "https://www.google.com/search?q=" + quote_plus(t)
            self.view.setUrl(QUrl.fromUserInput(t))
            self.view.setFocus()

        def on_url(self, u):
            s = u.toString()
            if not self.url.hasFocus():
                self.url.setText(s)
            self.btn["repo"].setEnabled(bool(repo_of(s)))
            self.btn["repo"].setText("ANALIZAR EN HUB: " + repo_of(s)[:34] if repo_of(s) else "ANALIZAR EN HUB")
            self.btn["back"].setEnabled(self.view.history().canGoBack())
            self.btn["fwd"].setEnabled(self.view.history().canGoForward())

        def setzoom(self, d):
            self.zoom = max(0.5, min(3.0, round(self.zoom + d, 2)))
            self.view.setZoomFactor(self.zoom)
            self.status.setText(f"Zoom {self.zoom:.2f}")

        def toggle_drag(self):
            self.view.drag.on = not self.view.drag.on
            self.btn["drag"].setText("✋" if self.view.drag.on else "T")
            self.status.setText("Arrastrar = desplazar" if self.view.drag.on else "Arrastrar = seleccionar texto")

        def send_repo(self):
            r = repo_of(self.view.url().toString())
            if r:
                say("repo", r)
                self.close()

        def poll_focus(self):
            js = ("(function(){var e=document.activeElement;if(!e)return false;var t=(e.tagName||'').toLowerCase();"
                  "if(t==='textarea')return true;if(e.isContentEditable)return true;"
                  "if(t==='input'){var k=(e.type||'text').toLowerCase();return ['text','search','url','email','password','number','tel',''].indexOf(k)>=0;}return false;})()")

            def cb(v):
                v = bool(v)
                if v and not self.editable:
                    steam_keyboard()
                self.editable = v
            self.page.runJavaScript(js, cb)

        def on_download(self, d):
            name = d.downloadFileName() or "descarga"
            dest = unique(dl_dir, name)
            d.setDownloadDirectory(str(dest.parent))
            d.setDownloadFileName(dest.name)
            d.accept()
            self.downloads[str(dest)] = d
            say("start", dest)
            self.status.setText(f"Descargando {dest.name}…")
            log("descarga:", d.url().toString(), "->", dest)

            def prog():
                tot = d.totalBytes()
                if not self.isVisible():
                    return
                self.status.setText(f"Descargando {dest.name}: {d.receivedBytes() / 1e6:.1f}" + (f" / {tot / 1e6:.1f} MB" if tot > 0 else " MB"))

            def st(state):
                from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest as R
                if state != R.DownloadState.DownloadInProgress:
                    self.downloads.pop(str(dest), None)
                if state == R.DownloadState.DownloadCompleted:
                    say("done", dest)
                    self.status.setText(f"✓ Descargado: {dest}   —   pulsa VOLVER A HUB")
                elif state in (R.DownloadState.DownloadCancelled, R.DownloadState.DownloadInterrupted):
                    self.status.setText(f"✗ Descarga interrumpida: {dest.name} ({d.interruptReasonString()})")
                    log("descarga interrumpida:", d.interruptReasonString())
            d.receivedBytesChanged.connect(prog)
            d.stateChanged.connect(st)

    win = Win()
    if a.window:
        w, h = (int(v) for v in a.window.lower().split("x"))
        win.resize(w, h)
        win.show()
    else:
        win.showFullScreen()
    app._hub_win = win
    globals()["win"] = win
    log("ventana mostrada; zoom", a.zoom, "descargas en", dl_dir)
    say("ready")
    if os.environ.get("HUB_BROWSER_TEST"):
        return win, app
    rc = app.exec()
    say("exit")
    return rc


if __name__ == "__main__":
    sys.exit(main())
