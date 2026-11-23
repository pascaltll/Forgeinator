"""v3.24 · E3: «Informe de error» y «Sugerencia» desde Ajustes › Mantenimiento. Vista previa (ya con los secretos tapados) en el visor de
registros, y dos salidas: guardar un zip en tu carpeta personal o abrir un issue de GitHub ya rellenado (por enlace, sin token).
Parte de la clase UI (ver _adopt en hub/ui.py): usa sus nombres globales. La lógica está en hub/report.py."""
# flake8: noqa: F821


class ReportMixin:
    def _report_txt(self):
        cs = self.memo("crashes", report.crashes, 5.0)
        if not cs:
            return "ningún error guardado"
        last = time.strftime("%d-%m %H:%M", time.localtime(cs[0].get("ts", 0)))
        return f"{len(cs)} error{'es' if len(cs) != 1 else ''} guardado{'s' if len(cs) != 1 else ''} · último {last}"

    def report_error(self, crash=None):
        self.osk("¿Qué estabas haciendo y qué pasó? (puedes dejarlo vacío)", lambda t: self._report_make("error", t, crash),
                 hint="El informe se revisa antes de enviarlo: los tokens, cookies y tu usuario van tapados")

    def report_idea(self):
        def go(t):
            if not t.strip():
                self.toast("Escribe la idea para poder enviarla")
                return
            self._report_make("idea", t)
        self.osk("Tu sugerencia: ¿qué te gustaría y para qué?", go)

    def report_menu(self):
        cs = report.crashes()
        opts = [("INFORMAR DE UN ERROR", lambda: self.report_error())]
        for c in cs[:3]:
            when = time.strftime("%d-%m %H:%M", time.localtime(c.get("ts", 0)))
            tag = "cerró el Hub" if c.get("fatal") else "fotograma"
            opts.append((f"{when} · {tag} · {c.get('error', '')[:48]}", lambda c=c: self.report_error(c)))
        opts += [("ENVIAR UNA SUGERENCIA", self.report_idea), ("CERRAR", lambda: None)]
        self._choice("Informe de error o sugerencia",
                     "Se arma un informe con la versión, el sistema y el final del registro. Lo ves antes de que salga nada; "
                     "luego lo guardas como zip o lo abres como issue en GitHub.", opts)

    def _report_make(self, kind, note, crash=None):
        def done(rep, err):
            if err or not rep:
                self.__dict__.setdefault("_uiq", []).append(lambda: self.toast(f"No pude armar el informe: {err}"))
                return
            self.__dict__.setdefault("_uiq", []).append(lambda: self._report_show(rep))
        self.work("Armando el informe…", lambda: report.build(kind, note, crash), done)

    def _report_show(self, rep):
        self._report = rep
        txt = rep["md"]
        log = self._TextLog(("Informe de error" if rep["kind"] == "error" else "Sugerencia") + " · vista previa (ya va tapado)",
                            "Revisa el texto: es exactamente lo que se guarda o se envía", txt)
        log.actions = [("lg:zip", "GUARDAR ZIP", self.report_save), ("lg:gh", "ABRIR ISSUE EN GITHUB", self.report_github),
                       ("lg:copy", "COPIAR", self.log_copy), ("lg:top", "AL PRINCIPIO", lambda: self.log_jump(False))]
        self.show_log(log)
        self.views.setdefault("log", View()).off = 0

    def report_save(self):
        rep = getattr(self, "_report", None)
        if not rep:
            return
        try:
            p = report.save_zip(rep)
            self.memo_clear()
            self.toast(f"Guardado en {p}  (adjúntalo a un issue o envíalo)")
        except OSError as ex:
            self.toast(f"No pude guardar el zip: {ex}")

    def report_github(self):
        rep = getattr(self, "_report", None)
        if not rep:
            return
        try:
            report.save_zip(rep)                     # por si el cuerpo se recortó: el zip completo queda en tu carpeta personal
        except OSError:
            pass
        self.open_url(report.issue_url(rep))
