"""v3.25 · Zona de complementos (Ajustes › Archivos › Complementos): instalar desde un zip, activar, desactivar, ver detalles y quitar
(quitar no borra: va a la papelera de complementos). Parte de la clase UI (ver _adopt en hub/ui.py). La lógica está en hub/plugins.py."""
# flake8: noqa: F821


class PluginsMixin:
    def _plugins_txt(self):
        ps = self.memo("plugins", plugins.installed, 5.0)
        if not ps:
            return "ninguno instalado"
        on = sum(1 for p in ps.values() if p.get("enabled") and not p.get("error"))
        return f"{len(ps)} instalado{'s' if len(ps) != 1 else ''} · {on} activo{'s' if on != 1 else ''}"

    def plugins_menu(self):
        self.memo_clear()
        opts = []
        for p in plugins.installed().values():
            st = "ROTO" if p.get("error") else ("ACTIVO" if p.get("enabled") else "DESACTIVADO")
            opts.append((f"{p['name'].upper()}  {p['version']}  ·  {st}", lambda p=p: self.plugin_open(p)))
        opts += [("+ INSTALAR UN COMPLEMENTO (ZIP)", self.plugin_install_menu), ("CERRAR", lambda: None)]
        self._choice("Complementos", "Conectores extra para tus bibliotecas (servidores con API propia, servicios nuevos…). "
                     "Un complemento es un programa: instala solo los de fuentes en las que confíes. Guía: docs/PLUGINS.md", opts)

    def plugin_open(self, p):
        if p.get("error"):
            self._choice(p["name"], f"Este complemento no se puede usar: {p['error']}",
                         [("QUITAR (A LA PAPELERA DE COMPLEMENTOS)", lambda: self._plugin_remove(p)), ("VOLVER", self.plugins_menu)])
            return
        perms = ", ".join(plugins.PERMS[x] for x in p.get("permissions") or []) or "ninguno declarado"
        n = sum(1 for s in remote.sources() if s.get("kind") == "plugin" and (s.get("fields") or {}).get("plugin") == p["id"])
        msg = (f"{p.get('description') or 'Sin descripción.'}\nVersión {p['version']}" + (f" · {p['author']}" if p.get("author") else "")
               + f" · tipo {p['type']} · protocolo {p['protocol']}\nPermisos: {perms}\nBibliotecas que lo usan: {n}")
        opts = [("DESACTIVAR" if p.get("enabled") else "ACTIVAR", lambda: self._plugin_toggle(p))]
        if p.get("enabled") and p.get("type") == "connector":
            opts.append(("AÑADIR UNA BIBLIOTECA CON ÉL", lambda: self._plugin_ask(p, {}, 0)))
        opts += [("QUITAR (A LA PAPELERA DE COMPLEMENTOS)", lambda: self._plugin_remove(p)), ("VOLVER", self.plugins_menu)]
        self._choice(p["name"], msg, opts)

    def _plugin_toggle(self, p):
        try:
            plugins.set_enabled(p["id"], not p.get("enabled"))
        except plugins.PluginError as ex:
            self.toast(str(ex))
        self.memo_clear()
        self.plugin_open(plugins.installed().get(p["id"], p))

    def _plugin_remove(self, p):
        def go():
            try:
                dst = plugins.remove(p["id"])
                self.toast(f"«{p['name']}» quitado. Sigue guardado en {dst}")
            except plugins.PluginError as ex:
                self.toast(str(ex))
            self.memo_clear()
            self.plugins_menu()
        self.confirm(f"¿Quitar «{p['name']}»?", "No se borra: la carpeta va a la papelera de complementos. "
                     "Las bibliotecas que lo usan dejan de funcionar hasta que lo vuelvas a instalar.", go)

    def plugin_install_menu(self):
        zs = plugins.candidates()
        opts = [(f"{z.name}  ·  {z.parent.name}", lambda z=z: self.plugin_install_ask(z)) for z in zs]
        opts += [("BUSCAR EL ZIP…", lambda: self.open_picker("Elige el zip del complemento", Path("~/Downloads").expanduser()
                                                            if Path("~/Downloads").expanduser().is_dir() else Path.home(), (".zip",), self.plugin_install_ask)),
                 ("VOLVER", self.plugins_menu)]
        self._choice("Instalar un complemento", ("Encontrados en ~/Games/actualizaciones, ~/Downloads y ~/Descargas." if zs else
                     "No hay zips de complementos en ~/Games/actualizaciones, ~/Downloads ni ~/Descargas.") , opts)

    def plugin_install_ask(self, z):
        z = Path(z)
        try:
            m = plugins.inspect(z)
        except (plugins.PluginError, OSError) as ex:
            self._choice("No es un complemento válido", str(ex), [("VOLVER", self.plugin_install_menu)])
            return
        perms = "\n".join("• " + plugins.PERMS[x] for x in m["permissions"]) or "• ninguno declarado"
        act = {"instalar": "INSTALAR", "actualizar": f"ACTUALIZAR (tienes la {m['installed_version']})",
               "reinstalar": f"REINSTALAR (tienes la {m['installed_version']})"}[m["action"]]
        msg = (f"{m['name']} {m['version']}" + (f" · {m['author']}" if m.get("author") else "") + f"\n{m.get('description') or ''}\n"
               f"Pide estos permisos:\n{perms}\nEs un programa que se ejecuta en tu equipo: instálalo solo si confías en quien lo hizo.")

        def go():
            def job():
                return plugins.install(z)

            def done(r):
                self.memo_clear()
                self.toast(f"«{r['name']}» {r['version']} instalado y activo")
                self.plugin_open(r)
            self.run_bg("Instalando el complemento…", job, done)
        self._choice(f"¿{act.split(' ')[0].capitalize()} «{m['name']}»?", msg, [(act, go), ("CANCELAR", self.plugin_install_menu)])
