"""Registro local de compilaciones (data/buildlog.jsonl) y estadística de los parámetros más usados."""
import collections
import json
import re
import time

from . import config


def _f():
    return config.DATA / "buildlog.jsonl"


def record(entry, container, cmd, jobs, ok, secs, error=""):
    row = {"t": int(time.time()), "id": entry.get("id"), "name": entry.get("name"), "container": container or "",
           "cmd": cmd or "", "jobs": jobs, "ok": bool(ok), "secs": round(secs, 1), "error": error[:200]}
    try:
        _f().parent.mkdir(parents=True, exist_ok=True)
        with open(_f(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    try:
        from . import history
        history.record(entry.get('launcher_id') or entry.get('id'), 'compilar', bool(ok), error or f'{round(secs)} s', container=container or '', cmd=(cmd or '')[:120])
    except Exception:  # noqa: BLE001
        pass
    return row


def rows():
    out = []
    try:
        for ln in _f().read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def tool(cmd: str) -> str:
    m = re.search(r"\b(cmake|make|ninja|meson|cargo|gradle|msbuild|scons|bash|python3?|npm)\b", cmd or "")
    return m.group(1) if m else "otro"


def stats():
    rs = rows()
    n = len(rs)
    ok = sum(1 for r in rs if r["ok"])
    c = collections.Counter(tool(r["cmd"]) for r in rs)
    cont = collections.Counter(r["container"] or "(sistema)" for r in rs)
    jobs = collections.Counter(r["jobs"] for r in rs)
    fails = collections.Counter((r["error"] or "?")[:60] for r in rs if not r["ok"])
    avg = sum(r["secs"] for r in rs if r["ok"]) / ok if ok else 0
    return {"total": n, "ok": ok, "tools": c.most_common(5), "containers": cont.most_common(3),
            "jobs": jobs.most_common(3), "fails": fails.most_common(3), "avg_secs": round(avg, 1)}


def summary() -> str:
    s = stats()
    if not s["total"]:
        return "sin compilaciones registradas todavía"
    t = ", ".join(f"{k} ×{v}" for k, v in s["tools"])
    return f"{s['ok']}/{s['total']} bien · herramientas: {t} · media {s['avg_secs']} s"
