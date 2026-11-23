"""v3.22 · Bibliotecas remotas (WebDAV, SMB, SFTP, FTP, remotos de rclone, carpetas montadas): añadir, explorar por sistema y bajar
juegos a tu biblioteca ES-DE. Parte de la clase UI (ver _adopt en hub/ui.py): usa sus nombres globales. La lógica está en hub/remote.py."""
# flake8: noqa: F821


class RemoteMixin:
    def _svc_list(self):
        """Descargas del servicio (forgeinatord), sin arrancarlo si no está en marcha."""
        try:
            return service.call("downloads.list", start=False, timeout=2.0)
        except (OSError, ValueError):
            return []

    def _remote_txt(self):
        st = getattr(self, "_rdl", None)
        if st and st.get("busy"):                       # descarga en este proceso (sin servicio)
            tot = st.get("total") or 0
            pct = f"{100 * st['done'] / tot:.0f} %" if tot else "…"
            eta = f" · faltan {int(st['eta'])} s" if st.get("eta") else ""
            return f"bajando «{st['name']}» {pct}{eta}"
        ds = self.memo("svc_dl", self._svc_list, 2.0)
        act = [d for d in ds if d["state"] == "active"]
        cola = sum(1 for d in ds if d["state"] == "queued")
        if act:
            d = act[0]
            pct = f"{100 * d['done'] / d['total']:.0f} %" if d.get("total") else "…"
            eta = f" · faltan {int(d['eta'])} s" if d.get("eta") else ""
            return f"bajando «{d['name']}» {pct}{eta}" + (f" (+{len(act) - 1 + cola} en cola)" if len(act) - 1 + cola else "")
        n = len(self.memo("remotes", remote.sources, 5.0))
        if not remote.rclone_bin() and not self.memo("plug_conn", plugins.connectors, 5.0):
            return "falta rclone"
        return f"{n} configurada{'s' if n != 1 else ''}" if n else "ninguna"

    def _choice(self, title, msg, options):
        self.modal = {"kind": "choice", "title": title, "prev": None, "msg": msg, "options": options}
        self.focus = None

    def remotes_menu(self):
        if not remote.rclone_bin() and not plugins.connectors() and not remote.sources():
            self._choice("Falta rclone", "Las bibliotecas remotas usan rclone (un solo programa, libre). En Bazzite: «brew install rclone» "
                         "o «rpm-ostree install rclone». También vale dejar el ejecutable de rclone.org en ~/.local/bin.",
                         [("ENTENDIDO", lambda: None)])
            return
        opts = [(f"{s['name'].upper()}  ·  {remote.kind_label(s)}", lambda s=s: self.remote_open(s)) for s in remote.sources()]
        ds = self._svc_list()
        if ds:
            vivas = sum(1 for d in ds if d["state"] in ("queued", "active", "paused"))
            opts.insert(0, (f"DESCARGAS ({vivas} en marcha · {len(ds)} en la lista)", self.remote_downloads))
        opts.append(("+ AÑADIR UNA BIBLIOTECA", self.remote_add))
        opts.append(("CERRAR", lambda: None))
        self._choice("Bibliotecas remotas", "Servidores con tus juegos en carpetas por sistema (roms/psx, roms/ps2…, como ES-DE). "
                     "Lo que bajes va a tu carpeta de ROMs.", opts)

    # ---------------------------------------------------------------- añadir
    def remote_add(self):
        rc = bool(remote.rclone_bin())
        opts = [(remote.KINDS[k][0].upper(), lambda k=k: self._remote_ask(k, {}, 0)) for k in remote.KINDS if k != "plugin" and (rc or k == "local")]
        opts += [(f"COMPLEMENTO · {p['name'].upper()}", lambda p=p: self._plugin_ask(p, {}, 0)) for p in plugins.connectors()]
        self._choice("¿Qué tipo de servidor?", "" if rc else "Sin rclone solo salen las carpetas locales y los complementos instalados.",
                     opts + [("COMPLEMENTOS…", self.plugins_menu), ("CANCELAR", lambda: None)])

    def _plugin_ask(self, p, vals, i):
        """Pide los campos que declara el manifiesto del complemento y guarda la fuente (los secretos van aparte, 600)."""
        fs = p.get("fields") or []
        if i < len(fs):
            f = fs[i]
            hint = "Se guarda aparte, solo para ti" if f.get("secret") else ""

            def got(t, f=f):
                if f.get("required") and not t.strip():
                    self.toast(f"«{f['label']}» es obligatorio")
                    return self._plugin_ask(p, vals, i)
                self._plugin_ask(p, dict(vals, **{f["key"]: t.strip()}), i + 1)
            self.osk(f["label"], got, vals.get(f["key"], f.get("default", "")), hint=hint)
            return
        self.osk("Nombre para reconocerla", lambda t: self._remote_save("plugin", dict(vals, plugin=p["id"], _root=""), t.strip() or p["name"]),
                 p["name"][:30])

    _ASK = {"url": ("Dirección (p. ej. https://nas.local/remote.php/dav/files/carlos)", "https://"), "host": ("Servidor (nombre o IP)", ""),
            "user": ("Usuario", ""), "pass": ("Contraseña (se guarda cifrada, solo para ti)", ""), "share": ("Carpeta compartida (p. ej. juegos)", ""),
            "port": ("Puerto (vacío = el normal)", ""), "remote": ("Nombre del remoto de rclone (p. ej. gdrive)", ""), "path": ("Ruta (p. ej. /run/media/usb)", "/")}

    def _remote_ask(self, kind, vals, i):
        fields = list(remote.KINDS[kind][2]) + (["path"] if kind == "local" else [])
        if i < len(fields):
            f = fields[i]
            title, pre = self._ASK[f]
            self.osk(title, lambda t, f=f: self._remote_ask(kind, dict(vals, **{f: t.strip()}), i + 1), vals.get(f, pre))
            return
        if i == len(fields):
            self.osk("Carpeta de los sistemas dentro del servidor (vacío = la raíz)", lambda t: self._remote_ask(kind, dict(vals, _root=t.strip()), i + 1), "roms")
            return
        default = vals.get("url") or vals.get("host") or vals.get("remote") or vals.get("path") or kind
        self.osk("Nombre para reconocerla", lambda t: self._remote_save(kind, vals, t.strip() or default), default.split("//")[-1][:30])

    def _remote_save(self, kind, vals, name):
        def job():
            s = remote.add(kind, name, {k: v for k, v in vals.items() if not k.startswith("_")}, vals.get("_root", "roms"))
            self.memo_clear()
            try:
                info = remote.test(s)
            except remote.RemoteError as ex:
                return f"Guardada «{name}», pero no conecta: {ex}"
            return f"«{name}» guardada · {info}"
        self.run_bg("Probando la conexión…", job, lambda msg: self.toast(msg))

    # ---------------------------------------------------------------- explorar
    def remote_open(self, s):
        def job():
            return remote.systems(s)

        def done(sy):
            if not sy:
                self._choice(s["name"], "No hay carpetas de sistema (psx, ps2, n64…) en «" + (s.get("root") or "/") + "».",
                             [("BORRAR ESTA BIBLIOTECA", lambda: self._remote_del(s)), ("VOLVER", self.remotes_menu)])
                return
            opts = [(f"{x['system'].upper()}  ·  {x['dir']}", lambda x=x: self._remote_games(s, x)) for x in sy]
            opts += [("BORRAR ESTA BIBLIOTECA", lambda: self._remote_del(s)), ("VOLVER", self.remotes_menu)]
            self._choice(s["name"], f"{len(sy)} sistemas", opts)
        self.run_bg(f"Conectando con «{s['name']}»…", job, done)

    def _remote_games(self, s, x):
        def done(gs):
            have = {p.name for p in remote.target(x["system"], "x", self.cfg).parent.glob("*")} if self.roms_roots() else set()
            opts = []
            for g in gs:
                size = f"  ·  {g['size'] / 1e9:.1f} GB" if g.get("size") and g["size"] > 5e8 else (f"  ·  {g['size'] / 1e6:.0f} MB" if g.get("size") else "")
                mark = "✓ " if g["name"] in have else ""
                opts.append((mark + g["name"] + size, lambda g=g: self._remote_get(s, g, x["system"])))
            opts.append(("VOLVER", lambda: self.remote_open(s)))
            self._choice(f"{s['name']} · {x['system']}", f"{len(gs)} juegos. ✓ = ya está en tu biblioteca.", opts)
        self.run_bg("Leyendo la lista…", lambda: remote.games(s, x["dir"], x["system"]), done)

    def _remote_get(self, s, g, system):
        """v3.23: la descarga la hace forgeinatord (sigue aunque se cierre el Hub); si el servicio no arranca, la hace el Hub."""
        try:
            service.call("downloads.add", {"source": s["id"], "game": g, "system": system})
            self.memo_clear()
            self.toast(f"«{g['name']}» en cola. Sigue aunque cierres Forgeinator (Ajustes › Archivos › Bibliotecas remotas › Descargas)")
            return
        except (OSError, ValueError) as ex:
            print(f"[remota] el servicio de descargas no responde ({ex}): la descarga la hace el Hub", file=sys.stderr, flush=True)
        if getattr(self, "_rdl", None) and self._rdl.get("busy"):
            self.toast("Ya hay una descarga remota en marcha")
            return
        st = self._rdl = {"busy": True, "name": g["name"], "done": 0, "total": g.get("size") or 0, "eta": None, "stop": False}

        def prog(b, tot, eta, spd):
            st.update(done=b, total=tot or st["total"], eta=eta)

        def job():
            t0 = time.time()
            try:
                d = remote.download(s, g, system, prog, stop=lambda: st["stop"], cfg=self.cfg)
                self.lib_loaded = False
                print(f"[remota] «{g['name']}» de «{s['name']}» → {d} en {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
                self.toast(f"«{g['name']}» ya está en tu biblioteca ({system})")
            except remote.RemoteError as ex:
                print(f"[remota] «{g['name']}» de «{s['name']}»: {ex}", file=sys.stderr, flush=True)
                self.toast(f"No se pudo bajar «{g['name']}»: {ex}")
            finally:
                st["busy"] = False
        threading.Thread(target=job, daemon=True).start()
        self.toast(f"Bajando «{g['name']}»… (el avance, en Ajustes › Archivos)")

    def remote_downloads(self):
        ds = self._svc_list()
        lab = {"queued": "en cola", "active": "bajando", "paused": "en pausa", "done": "hecha", "error": "error", "cancelled": "cancelada"}
        opts = []
        for d in ds:
            pct = f" {100 * d['done'] / d['total']:.0f} %" if d.get("total") and d["state"] == "active" else ""
            opts.append((f"{d['name']}  ·  {d['system']}  ·  {lab.get(d['state'], d['state'])}{pct}", lambda d=d: self._remote_dl_actions(d)))
        opts += [("QUITAR LAS TERMINADAS DE LA LISTA", lambda: (service.call("downloads.clear", start=False), self.memo_clear(), self.remote_downloads())),
                 ("VOLVER", self.remotes_menu)]
        self._choice("Descargas remotas", "Las hace el servicio de Forgeinator: siguen con el Hub cerrado o con un juego abierto.", opts)

    def _remote_dl_actions(self, d):
        def act(m):
            try:
                service.call(f"downloads.{m}", {"id": d["id"]}, start=False)
            except (OSError, ValueError) as ex:
                self.toast(str(ex))
            self.memo_clear()
            self.remote_downloads()
        opts = []
        if d["state"] in ("queued", "active"):
            opts.append(("PAUSAR", lambda: act("pause")))
        if d["state"] in ("paused", "error", "cancelled"):
            opts.append(("REINTENTAR" if d["state"] != "paused" else "SEGUIR", lambda: act("resume")))
        if d["state"] in ("queued", "active", "paused"):
            opts.append(("CANCELAR", lambda: act("cancel")))
        opts.append(("VOLVER", self.remote_downloads))
        self._choice(d["name"], (d.get("error") or d.get("dest") or "") + ("\nAl pausar, la descarga empieza de nuevo al seguir." if d["state"] == "active" else ""), opts)

    def remote_cancel(self):
        st = getattr(self, "_rdl", None)
        if st and st.get("busy"):
            st["stop"] = True
            self.toast("Cancelando la descarga remota…")
        else:
            self.remotes_menu()

    def _remote_del(self, s):
        self.confirm(f"¿Quitar «{s['name']}»?", "Solo se olvida la conexión (y su contraseña guardada). No se borra nada del servidor ni de tu biblioteca.",
                     lambda: (remote.remove(s["id"]), self.memo_clear(), self.toast(f"«{s['name']}» quitada")))

    def run_bg(self, msg, job, done):
        """Trabajo de red en un hilo con aviso; el resultado vuelve al hilo de la interfaz (_uiq)."""
        self.toast(msg)

        def run():
            try:
                r = job()
                self.__dict__.setdefault("_uiq", []).append(lambda: done(r))
            except remote.RemoteError as ex:
                self.__dict__.setdefault("_uiq", []).append(lambda: self.toast(str(ex)))
            except Exception as ex:  # noqa: BLE001
                print(f"[remota] fallo inesperado: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
                self.__dict__.setdefault("_uiq", []).append(lambda: self.toast(f"Error: {ex}"))
        threading.Thread(target=run, daemon=True).start()
