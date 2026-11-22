"""Tu archivo del juego: reconocerlo, extraerlo y guardarlo en tu biblioteca ES-DE. Parte de la clase UI (hub/ui.py) separada en su propio archivo: los métodos usan los mismos nombres globales
que ui.py (colores del tema, módulos, funciones), porque ui.py los adopta con su espacio de nombres (ver _adopt)."""
# flake8: noqa: F821


class FilesMixin:
    def _accept(self, e, path, how, original=None):
        """Archivo reconocido. Antes de enlazarlo ofrece guardarlo en tu biblioteca estilo ES-DE (copiar/mover) si está fuera de ella."""
        roots = self.roms_roots()
        system = esde.system_for(e.get("platform", ""))
        mode = self.cfg.get("esde_store", "ask")
        if original and Path(original) != Path(path) and roots and system and mode != "link" and self.cfg.get("extract_to_library", True):
            return self._store_extracted(e, Path(original), Path(path), how, system, roots[0])
        src = Path(original) if original else Path(path)
        # preferimos guardar lo que descargaste tal cual si ES-DE lo acepta para ese sistema; si no, el archivo ya preparado
        keep = src if (original and esde.accepts(system, src.suffix) and src.suffix.lower() not in formats.PROPRIETARY) else Path(path)
        if not roots or not system or mode == "link" or esde.is_inside(keep, roots) or esde.is_inside(path, roots):
            return self._accept_final(e, path, how)
        pl = esde.plan(keep, system, roots[0])
        names = ", ".join(d.name for _, d in pl["files"])[:120]
        msg = f"Reconocido ({how}).\n¿Guardarlo en tu biblioteca?\n{pl['dir']}/\n{names}  ({pl['size'] / (1 << 30):.1f} GB)"
        if mode in ("copy", "move"):
            return self._store_then(e, keep, path, how, system, roots[0], mode)
        self.modal = {"kind": "choice", "title": "Guardar en tu biblioteca (ES-DE)", "msg": msg, "prev": None, "options": [
            ("COPIAR A MI BIBLIOTECA", lambda: self._store_then(e, keep, path, how, system, roots[0], "copy")),
            ("MOVER A MI BIBLIOTECA (borra el original)", lambda: self._store_then(e, keep, path, how, system, roots[0], "move")),
            ("SOLO ENLAZAR (no tocar nada)", lambda: self._accept_final(e, path, how))]}
        self.focus = None

    def _store_extracted(self, e, orig, plain, how, system, root):
        """Siempre extraído: la biblioteca guarda el archivo llano (z64, iso…) y el paquete (zip/rar/7z) se elimina tras comprobar la copia."""
        def job():
            try:
                self.match_res[e["id"]] = {"busy": True, "path": str(plain), "how": "guardando el archivo extraído en tu biblioteca…"}
                want = plain.stat().st_size
                dest = esde.store(plain, system, root, "move", lambda d, t: self.progress.__setitem__(e["id"], d / t))
                if not dest.exists() or dest.stat().st_size != want:
                    raise OSError("la copia en la biblioteca no coincide; no borro nada")
                if plain.exists() and plain != dest:
                    plain.unlink()
                gone = ""
                if self.cfg.get("delete_archive", True) and orig.exists() and orig != dest and orig.is_file():
                    orig.unlink()
                    gone = f" · eliminado {orig.name}"
                for p_ in (plain.parent,):
                    try:
                        p_.rmdir()
                    except OSError:
                        pass
                try:
                    roms.INDEX.unlink()
                except OSError:
                    pass
                self.lib_loaded = False
                self.toast(f"Guardado en {dest.parent}{gone}")
                self._accept_final(e, dest, how + " · extraído a tu biblioteca")
            except OSError as ex:
                self.match_res[e["id"]] = {"ok": False, "path": str(plain), "how": f"no pude guardarlo: {ex}"}
                self.toast(f"No pude guardarlo en tu biblioteca: {ex}")
            finally:
                self.progress.pop(e["id"], None)
        threading.Thread(target=job, daemon=True).start()

    def _store_then(self, e, keep, path, how, system, root, mode):
        def job():
            try:
                self.match_res[e["id"]] = {"busy": True, "path": str(keep), "how": f"{'copiando' if mode == 'copy' else 'moviendo'} a tu biblioteca…"}
                dest = esde.store(keep, system, root, mode, lambda d, t: self.progress.__setitem__(e["id"], d / t))
                try:
                    roms.INDEX.unlink()
                except OSError:
                    pass
                self.lib_loaded = False
                self.toast(f"Guardado en {dest.parent}")
                # si lo guardado es el original comprimido (p. ej. .zip), el port sigue usando el archivo ya preparado
                self._accept_final(e, dest if Path(keep) == Path(path) else Path(path), how + " · guardado en tu biblioteca")
            except OSError as ex:
                self.match_res[e["id"]] = {"ok": False, "path": str(keep), "how": f"no pude guardarlo: {ex}"}
                self.toast(f"No pude guardarlo en tu biblioteca: {ex}")
            finally:
                self.progress.pop(e["id"], None)
        threading.Thread(target=job, daemon=True).start()

    def toggle_store_mode(self):
        order = ["ask", "copy", "move", "link"]
        cur = self.cfg.get("esde_store", "ask")
        self.cfg["esde_store"] = order[(order.index(cur) + 1) % 4] if cur in order else "ask"
        config.save_settings(self.cfg)
        self.toast("Al reconocer un juego: " + {"ask": "preguntar", "copy": "copiar a tu biblioteca", "move": "mover a tu biblioteca", "link": "solo enlazar"}[self.cfg["esde_store"]])

    def _accept_final(self, e, path, how):
        prev_lk = library.link_get(e["id"])
        library.link_set(e["id"], path)
        self._note_disc_link(e, path)             # v2.41: ports de varios discos (God of War PSP): uno por ID
        relinked = 0
        try:
            library.adopt(path, e.get("platform") or "otros", "link")
            info = install.installed_info(e, None, self.entries)
            if info["installed"]:
                relinked = library.relink(info["dir"], prev_lk, path)      # v2.76: CAMBIAR ARCHIVO: linux/ y windows/ pasan al archivo nuevo
                library.place(e, path, info["dir"])
                if self.cfg.get("link_in_project", True) and not relinked:
                    library.place_default(e, path, info["dir"])
            library.place_rom(e, path)
        except OSError as ex:
            self.toast(f"Reconocido, pero no pude enlazarlo: {ex}")
        self.match_res[e["id"]] = {"ok": True, "how": how, "path": str(path)}
        self.detected.pop(e["id"], None)
        self.toast(f"Archivo reconocido ({how})" + (f" · {relinked} enlace(s) del juego actualizados" if relinked else "") + self._auto_libcwd(e))

    def _auto_libcwd(self, e):
        """Que el selector de archivos del propio juego (p. ej. «no hay O2R, ¿generar?») abra donde está tu ROM ya lista."""
        if not self.cfg.get("auto_libcwd", True):
            return ""
        try:
            inf = self.inst(e)
            if not inf.get("installed"):
                return ""
            st = gamecfg.state(inf["launcher_id"])
            lk = library.link_get(e["id"])
            if not st["exists"] or st["libcwd"] or not lk:
                return ""
            gamecfg.set_libcwd(inf["launcher_id"], str(Path(lk).expanduser().parent), True)
            return " · el selector del juego empezará en esa carpeta"
        except (OSError, ValueError, KeyError):
            return ""

    def check_file(self, e, path):
        req = e.get("requires") or {}
        self.match_res[e["id"]] = {"busy": True, "path": str(path)}

        def job():
            real, via = Path(path), ""
            try:
                if formats.kind(path) != "plain":
                    self.match_res[e["id"]] = {"busy": True, "path": str(path), "how": "preparando el archivo…"}
                    rs = formats.resolve(path, req)
                    if not rs["path"]:
                        self.match_res[e["id"]] = {"ok": False, "path": str(path), "how": rs["note"] or "formato no soportado"}
                        self.toast(rs["note"] or "Formato no soportado")
                        return
                    real, via = Path(rs["path"]), rs["how"]
                r = library.match(real, req, lambda d, t: self.progress.__setitem__(e["id"], d / max(1, t)))
                if via:
                    r["how"] = (r["how"] + " · " if r["how"] else "") + via
            except OSError as ex:
                self.match_res[e["id"]] = {"ok": False, "how": str(ex), "path": str(path)}
                return
            finally:
                self.progress.pop(e["id"], None)
            path_ = real
            if r["ok"]:
                self._accept(e, path_, r["how"], original=Path(path) if path_ != Path(path) else None)
            else:
                self.match_res[e["id"]] = {"ok": False, "path": str(path_), "how": r["how"] or "no coincide", "weak": r["weak"]}
                msg = ("No puedo verificar este archivo (el catálogo no trae hash ni serial)." if r["weak"] else
                       "Este archivo NO coincide con lo que pide el port.")
                did = discid.read_id(path_)
                if did:
                    self.match_res[e["id"]]["disc"] = did
                    msg += f"\nTu archivo es {did['id']}" + (f" ({did['note']})" if did["note"] else "") + (f"; el port pide {', '.join(req['serials'])}." if req.get("serials") else ".")
                    if req.get("note"):
                        msg += "\n" + req["note"]
                msg += "\n¿Usarlo de todos modos?"
                self.modal = {"kind": "confirm", "title": Path(path_).name, "msg": msg,
                              "cb": lambda: self._accept(e, path_, "elegido manualmente"), "prev": None}
        threading.Thread(target=job, daemon=True).start()
