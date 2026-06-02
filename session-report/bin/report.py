#!/usr/bin/env python3
"""
session-report: reporte preciso por sesion de trabajo, multi-herramienta.

Funciona en Claude Code, Antigravity, GitHub Copilot e IBM Bob:
  - Metricas de git (commits, archivos, LOC): UNIVERSALES, en cualquier repo.
  - Tokens / modelo / skills automaticos: SOLO Claude Code (transcript JSONL).
    En las demas herramientas se aportan con --meta o el sidecar .session-meta.json.

Modos:
  report.py [TRANSCRIPT.jsonl] [opciones]      reporte (auto: Claude si hay transcript)
  report.py --source git [opciones]            modo git-only (Copilot/Antigravity/Bob)
  report.py --stdin-hook                        lee JSON de hook por stdin (Claude SessionEnd)
  report.py --daily [YYYY-MM-DD]               consolidado diario

Opciones:
  --tool NOMBRE        etiqueta de la herramienta (claude-code|antigravity|copilot|ibm-bob|...)
  --source auto|claude|git   fuente de datos (def: auto)
  --since FECHA        (git-only) commits desde; def: hoy 00:00 UTC
  --session-id ID      (git-only) id de sesion; def: <tool>-<fecha>
  --meta JSON          inyecta {"model","input_tokens","output_tokens",...}
  --out-dir DIR        carpeta de salida; def: <cwd>/analisis/sesiones
"""
import sys, os, json, csv, re, subprocess, glob
from datetime import datetime, timezone, time as dtime

# ---------------------------------------------------------------- utilidades

def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def now_utc():
    return datetime.now(timezone.utc)

def nlines(text):
    if not text:
        return 0
    return text.count("\n") + 1

COMPILE_RE = re.compile(
    r"\b(tsc|next build|nuxt build|vite build|webpack|rollup|esbuild|"
    r"npm run build|yarn build|pnpm run build|pnpm build|"
    r"make\b|cmake|cargo build|go build|javac|"
    r"mvn (?:compile|package|install)|gradle\b|gradlew\b|dotnet build|"
    r"gcc|g\+\+|clang|rustc|python\s+setup\.py\s+build|pip install|"
    r"pyinstaller|tsc -b|tsc --build)\b", re.I)
TEST_RE = re.compile(
    r"\b(pytest|py\.test|python\s+-m\s+pytest|python\s+-m\s+unittest|"
    r"npm (?:run )?test|yarn test|pnpm (?:run )?test|jest|vitest|mocha|"
    r"go test|cargo test|mvn test|gradle test|dotnet test|rspec|phpunit|"
    r"tox|nose2|ava|cypress run|playwright test)\b", re.I)
FAIL_RE = re.compile(
    r"(failed|fail\b|error:|errors:|traceback|npm err!|exception|panic:|"
    r"fatal:|assertion|cannot find|no such file|exit code [1-9]|"
    r"compilation failed|build failed|tests? failed)", re.I)
OK_RE = re.compile(
    r"(passed|all tests? pass|build succeeded|compiled successfully|"
    r"\b0 errors?\b|no errors|success\b|ok\b|✓|build complete|done in)", re.I)

def classify_outcome(result):
    if not isinstance(result, dict):
        return "incierto"
    if result.get("interrupted"):
        return "interrumpido"
    blob = (str(result.get("stdout", "")) + "\n" + str(result.get("stderr", ""))).lower()
    fail = bool(FAIL_RE.search(blob))
    ok = bool(OK_RE.search(blob))
    if fail and not ok:
        return "fail"
    if ok and not fail:
        return "ok"
    if fail and ok:
        return "incierto"
    return "ok"

ICON = {"ok": "✅", "fail": "❌", "incierto": "⚠️", "interrumpido": "⏹️"}

# ---------------------------------------------------------------- estructura

def empty_session(session_id=None, cwd=None, tool="unknown"):
    return {
        "session_id": session_id, "cwd": cwd, "version": None, "tool": tool,
        "first_ts": None, "last_ts": None,
        "models": {}, "user_turns": 0, "skills": {},
        "files_created": {}, "files_modified": {},
        "loc_written": 0, "loc_edited_net": 0,
        "compiles": [], "tests": [], "bash_count": 0,
        "user_messages": [],   # textos reales de los mensajes del usuario
    }

STRIP_TAGS_RE = re.compile(r"<[^>]+>.*?</[^>]+>|<[^>]+/>", re.DOTALL)

def clean_user_text(text):
    """Elimina tags XML/sistema y retorna texto limpio."""
    text = STRIP_TAGS_RE.sub("", text)
    # quitar lineas que son solo ruido de hooks/system
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if not l.startswith(("<", "[", "---"))]
    return " ".join(lines).strip()

def model_bucket(d, model):
    return d["models"].setdefault(
        model, {"msgs": 0, "in": 0, "out": 0, "cc": 0, "cr": 0})

# ---------------------------------------------------------------- parseo Claude

def load_transcript(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

def analyze_claude(rows, tool="claude-code"):
    d = empty_session(tool=tool)
    pending_tools, results = {}, {}
    for o in rows:
        ts = parse_iso(o.get("timestamp"))
        if ts:
            if d["first_ts"] is None or ts < d["first_ts"]:
                d["first_ts"] = ts
            if d["last_ts"] is None or ts > d["last_ts"]:
                d["last_ts"] = ts
        if o.get("sessionId"):
            d["session_id"] = o["sessionId"]
        if o.get("cwd"):
            d["cwd"] = o["cwd"]
        if o.get("version"):
            d["version"] = o["version"]
        typ = o.get("type")
        msg = o.get("message") if isinstance(o.get("message"), dict) else {}

        if typ == "user" and not o.get("isMeta") and not o.get("isSidechain"):
            content = msg.get("content")
            is_tool_result, text_blob = False, ""
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        if b.get("type") == "tool_result":
                            is_tool_result = True
                        elif b.get("type") == "text":
                            text_blob += b.get("text", "")
            elif isinstance(content, str):
                text_blob = content
            if not is_tool_result:
                d["user_turns"] += 1
                clean = clean_user_text(text_blob)
                if clean and len(clean) > 8:
                    d["user_messages"].append(clean)
            for m in re.findall(r"<command-name>/?([\w:-]+)</command-name>", text_blob):
                d["skills"][m] = d["skills"].get(m, 0) + 1

        if typ == "assistant":
            model = msg.get("model")
            u = msg.get("usage") or {}
            if model:
                mm = model_bucket(d, model)
                mm["msgs"] += 1
                mm["in"] += int(u.get("input_tokens", 0) or 0)
                mm["out"] += int(u.get("output_tokens", 0) or 0)
                mm["cc"] += int(u.get("cache_creation_input_tokens", 0) or 0)
                mm["cr"] += int(u.get("cache_read_input_tokens", 0) or 0)

        content = msg.get("content")
        if isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    tid = b.get("id")
                    if tid:
                        pending_tools[tid] = {"name": b.get("name"), "input": b.get("input") or {}}
                    handle_tool_use(d, b.get("name"), b.get("input") or {})
                elif b.get("type") == "tool_result":
                    tid = b.get("tool_use_id")
                    if tid is not None:
                        results[tid] = o.get("toolUseResult")

    for tid, tu in pending_tools.items():
        if tu["name"] == "Bash":
            d["bash_count"] += 1
            cmd = (tu["input"] or {}).get("command", "")
            res = results.get(tid)
            if COMPILE_RE.search(cmd):
                d["compiles"].append({"cmd": cmd, "outcome": classify_outcome(res)})
            if TEST_RE.search(cmd):
                d["tests"].append({"cmd": cmd, "outcome": classify_outcome(res)})
    return d

def handle_tool_use(d, name, inp):
    if name == "Skill":
        sk = inp.get("skill") or inp.get("command") or "?"
        d["skills"][sk] = d["skills"].get(sk, 0) + 1
        return
    if name == "Write":
        path = inp.get("file_path")
        loc = nlines(inp.get("content", ""))
        if path:
            d["files_created"][path] = d["files_created"].get(path, 0) + loc
            d["loc_written"] += loc
        return
    if name in ("Edit", "MultiEdit", "NotebookEdit"):
        path = inp.get("file_path") or inp.get("notebook_path")
        if name == "MultiEdit":
            net = sum(nlines(e.get("new_string", "")) - nlines(e.get("old_string", ""))
                      for e in (inp.get("edits", []) or []))
        else:
            net = nlines(inp.get("new_string", "")) - nlines(inp.get("old_string", ""))
        if path:
            d["files_modified"][path] = d["files_modified"].get(path, 0) + max(net, 0)
            d["loc_edited_net"] += max(net, 0)
        return

# ---------------------------------------------------------------- meta (otras herramientas)

def apply_meta(d, meta):
    """Inyecta tokens/modelo/skills aportados manualmente o por el agente."""
    if not meta:
        return
    items = meta if isinstance(meta, list) else [meta]
    for m in items:
        if not isinstance(m, dict):
            continue
        model = m.get("model")
        if model:
            mm = model_bucket(d, model)
            mm["msgs"] += int(m.get("messages", 0) or 0)
            mm["in"] += int(m.get("input_tokens", 0) or 0)
            mm["out"] += int(m.get("output_tokens", 0) or 0)
            mm["cc"] += int(m.get("cache_creation", 0) or 0)
            mm["cr"] += int(m.get("cache_read", 0) or 0)
        for s in (m.get("skills") or []):
            d["skills"][s] = d["skills"].get(s, 0) + 1
        if m.get("user_turns"):
            d["user_turns"] += int(m["user_turns"])

def load_sidecar(out_dir):
    p = os.path.join(out_dir, ".session-meta.json")
    if not os.path.exists(p):
        return None, None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh), p
    except Exception:
        return None, None

# ---------------------------------------------------------------- git

def git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args],
                             capture_output=True, text=True, timeout=20)
        return out.stdout if out.returncode == 0 else None
    except Exception:
        return None

def is_repo(cwd):
    return bool(cwd and os.path.isdir(cwd) and
               git(cwd, "rev-parse", "--is-inside-work-tree"))

def git_commits(cwd, first_ts, last_ts):
    if not is_repo(cwd):
        return None
    since = first_ts.isoformat() if first_ts else "1 day ago"
    until = last_ts.isoformat() if last_ts else "now"
    log = git(cwd, "log", f"--since={since}", f"--until={until}",
              "--pretty=%H%x1f%an%x1f%aI%x1f%s")
    info = {"repo": True, "commits": [], "ins": 0, "del": 0}
    if not log:
        return info
    for line in log.splitlines():
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        h, author, date, subject = parts[:4]
        stat = git(cwd, "show", "--numstat", "--pretty=format:", h) or ""
        files, ins, dels = [], 0, 0
        for sl in stat.splitlines():
            cols = sl.strip().split("\t")
            if len(cols) == 3:
                a, b, fname = cols
                ai = int(a) if a.isdigit() else 0
                bi = int(b) if b.isdigit() else 0
                ins += ai; dels += bi
                files.append((fname, ai, bi))
        info["ins"] += ins; info["del"] += dels
        info["commits"].append({"hash": h[:8], "author": author, "date": date,
                                "subject": subject, "files": files, "ins": ins, "del": dels})
    return info

# ---------------------------------------------------------------- render md

def render_md(d, gitinfo):
    L = []
    sid = d["session_id"] or "desconocida"
    start, end = d["first_ts"], d["last_ts"]
    dur_min = round((end - start).total_seconds() / 60, 1) if start and end else 0
    L += [f"# Reporte de sesion — {sid}", "",
          f"- **Herramienta:** {d.get('tool','?')}",
          f"- **Inicio:** {start.isoformat() if start else '?'}",
          f"- **Fin:** {end.isoformat() if end else '?'}",
          f"- **Duracion:** {dur_min} min",
          f"- **Directorio:** {d['cwd'] or '?'}",
          f"- **Version:** {d['version'] or '—'}",
          f"- **Turnos de usuario:** {d['user_turns']}", ""]

    L += ["## Tokens y modelos", ""]
    if d["models"]:
        L += ["| Modelo | Msgs | Input | Output | Cache-creacion | Cache-lectura | Total |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        T = {"msgs": 0, "in": 0, "out": 0, "cc": 0, "cr": 0}
        for model, m in sorted(d["models"].items()):
            tot = m["in"] + m["out"] + m["cc"] + m["cr"]
            for k in T:
                T[k] += m[k]
            L.append(f"| {model} | {m['msgs']} | {m['in']:,} | {m['out']:,} | "
                     f"{m['cc']:,} | {m['cr']:,} | {tot:,} |")
        grand = T["in"] + T["out"] + T["cc"] + T["cr"]
        L.append(f"| **TOTAL** | **{T['msgs']}** | **{T['in']:,}** | **{T['out']:,}** | "
                 f"**{T['cc']:,}** | **{T['cr']:,}** | **{grand:,}** |")
    else:
        L.append("- _Sin datos de tokens. La extraccion automatica solo esta disponible "
                 "en Claude Code; en otras herramientas aporta los datos con `--meta`._")
    L.append("")

    L += ["## Skills / comandos usados", ""]
    if d["skills"]:
        for name, c in sorted(d["skills"].items(), key=lambda x: -x[1]):
            L.append(f"- `{name}` ×{c}")
    else:
        L.append("- _ninguno_")
    L.append("")

    L += ["## Objetos creados y modificados", "",
          f"- **Archivos creados:** {len(d['files_created'])} ({d['loc_written']:,} lineas escritas)"]
    for p, loc in sorted(d["files_created"].items()):
        L.append(f"  - `{p}` (+{loc} lineas)")
    L.append(f"- **Archivos modificados:** {len(d['files_modified'])} "
             f"({d['loc_edited_net']:,} lineas netas via Edit)")
    for p, loc in sorted(d["files_modified"].items()):
        L.append(f"  - `{p}` (~+{loc} lineas netas)")
    L.append(f"- **LOC generadas (por transcript):** {d['loc_written'] + d['loc_edited_net']:,}")
    L.append("")

    L += ["## Compilaciones", ""]
    L += ([f"- {ICON.get(c['outcome'],'')} `{c['cmd'][:120]}`" for c in d["compiles"]]
          or ["- _no se compilo nada detectado_"])
    L.append("")
    L += ["## Tests", ""]
    L += ([f"- {ICON.get(t['outcome'],'')} `{t['cmd'][:120]}`" for t in d["tests"]]
          or ["- _no se ejecutaron tests detectados_"])
    L.append("")

    L += ["## Commits (git)", ""]
    if not gitinfo:
        L.append("- _el directorio no es un repositorio git — sin datos de commits_")
    elif not gitinfo["commits"]:
        L.append("- _repositorio git sin commits en la ventana de la sesion_")
    else:
        L.append(f"- **Commits:** {len(gitinfo['commits'])} "
                 f"(+{gitinfo['ins']}/-{gitinfo['del']} lineas)")
        for c in gitinfo["commits"]:
            L.append(f"  - `{c['hash']}` {c['subject']} "
                     f"(+{c['ins']}/-{c['del']}, {len(c['files'])} archivos)")
            for fname, ai, bi in c["files"]:
                L.append(f"    - {fname} (+{ai}/-{bi})")
    L.append("")

    # Solicitudes del usuario — input para el resumen generado por Claude
    L += ["## Solicitudes del usuario", ""]
    msgs = d.get("user_messages") or []
    if msgs:
        for i, m in enumerate(msgs, 1):
            # truncar mensajes muy largos para no inflar el reporte
            snippet = m[:300] + ("…" if len(m) > 300 else "")
            L.append(f"{i}. {snippet}")
    else:
        L.append("- _no se pudieron extraer mensajes del usuario_")
    L += ["", "---",
          "<!-- RESUMEN_PENDIENTE -->",
          "<!-- Claude: reemplaza este marcador con las secciones",
          "     '## Resumen de trabajo' y '## Tareas realizadas'",
          "     basandote en las solicitudes del usuario, archivos creados",
          "     y commits listados arriba. -->",
          "",
          "---",
          "_Git, archivos y LOC son exactos en cualquier herramienta. Tokens/modelo son "
          "exactos en Claude Code (transcript) y manuales (`--meta`) en las demas. "
          "Compilo/testeo es heuristico._"]
    return "\n".join(L)

# ---------------------------------------------------------------- CSV maestro

CSV_FIELDS = ["date", "session_id", "tool", "start", "end", "duration_min", "models",
              "user_turns", "skills_used", "input_tokens", "output_tokens",
              "cache_creation", "cache_read", "total_tokens", "files_created",
              "files_modified", "loc_written", "loc_edited_net", "commits",
              "git_insertions", "git_deletions", "compiles_run", "compiles_ok",
              "compiles_fail", "tests_run", "tests_ok", "tests_fail"]

def csv_row(d, gitinfo):
    T = {"in": 0, "out": 0, "cc": 0, "cr": 0}
    for m in d["models"].values():
        for k in T:
            T[k] += m[k]
    start, end = d["first_ts"], d["last_ts"]
    dur = round((end - start).total_seconds() / 60, 1) if start and end else 0
    return {
        "date": (start.date().isoformat() if start else now_utc().date().isoformat()),
        "session_id": d["session_id"] or "", "tool": d.get("tool", ""),
        "start": start.isoformat() if start else "",
        "end": end.isoformat() if end else "",
        "duration_min": dur,
        "models": ";".join(sorted(d["models"].keys())),
        "user_turns": d["user_turns"],
        "skills_used": ";".join(sorted(d["skills"].keys())),
        "input_tokens": T["in"], "output_tokens": T["out"],
        "cache_creation": T["cc"], "cache_read": T["cr"],
        "total_tokens": T["in"] + T["out"] + T["cc"] + T["cr"],
        "files_created": len(d["files_created"]),
        "files_modified": len(d["files_modified"]),
        "loc_written": d["loc_written"], "loc_edited_net": d["loc_edited_net"],
        "commits": (len(gitinfo["commits"]) if gitinfo else 0),
        "git_insertions": (gitinfo["ins"] if gitinfo else 0),
        "git_deletions": (gitinfo["del"] if gitinfo else 0),
        "compiles_run": len(d["compiles"]),
        "compiles_ok": sum(1 for c in d["compiles"] if c["outcome"] == "ok"),
        "compiles_fail": sum(1 for c in d["compiles"] if c["outcome"] == "fail"),
        "tests_run": len(d["tests"]),
        "tests_ok": sum(1 for t in d["tests"] if t["outcome"] == "ok"),
        "tests_fail": sum(1 for t in d["tests"] if t["outcome"] == "fail"),
    }

def upsert_csv(csv_path, row):
    rows = []
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh)
                    if r.get("session_id") != row["session_id"]]
    rows.append({k: str(row.get(k, "")) for k in CSV_FIELDS})
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})

# ---------------------------------------------------------------- consolidado diario

def build_daily(csv_path, out_dir, day):
    if not os.path.exists(csv_path):
        print("No hay CSV maestro todavia.", file=sys.stderr)
        return None
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("date") == day]
    if not rows:
        print(f"Sin sesiones para {day}.", file=sys.stderr)
        return None

    def s(field):
        return sum(int(float(r.get(field) or 0)) for r in rows)

    models, skills, tools = set(), set(), set()
    for r in rows:
        models.update(filter(None, (r.get("models") or "").split(";")))
        skills.update(filter(None, (r.get("skills_used") or "").split(";")))
        if r.get("tool"):
            tools.add(r["tool"])

    L = [f"# Consolidado diario — {day}", "",
         f"- **Sesiones:** {len(rows)}",
         f"- **Herramientas:** {', '.join(sorted(tools)) or '—'}",
         f"- **Modelos:** {', '.join(sorted(models)) or '—'}",
         f"- **Skills:** {', '.join(sorted(skills)) or '—'}",
         f"- **Turnos de usuario:** {s('user_turns')}",
         f"- **Duracion total:** {round(sum(float(r.get('duration_min') or 0) for r in rows),1)} min",
         "", "## Tokens",
         f"- Input: {s('input_tokens'):,}",
         f"- Output: {s('output_tokens'):,}",
         f"- Cache-creacion: {s('cache_creation'):,}",
         f"- Cache-lectura: {s('cache_read'):,}",
         f"- **Total: {s('total_tokens'):,}**",
         "", "## Codigo",
         f"- Archivos creados: {s('files_created')}",
         f"- Archivos modificados: {s('files_modified')}",
         f"- LOC escritas (Write): {s('loc_written'):,}",
         f"- LOC netas (Edit): {s('loc_edited_net'):,}",
         f"- Commits: {s('commits')}  (+{s('git_insertions')}/-{s('git_deletions')})",
         "", "## Build / Test",
         f"- Compilaciones: {s('compiles_run')} (ok {s('compiles_ok')}, fail {s('compiles_fail')})",
         f"- Tests: {s('tests_run')} (ok {s('tests_ok')}, fail {s('tests_fail')})",
         "", "## Sesiones del dia", "",
         "| Sesion | Herramienta | Inicio | Min | Tokens | LOC | Commits |",
         "|---|---|---|---:|---:|---:|---:|"]
    for r in rows:
        loc = int(float(r.get("loc_written") or 0)) + int(float(r.get("loc_edited_net") or 0))
        L.append(f"| {(r.get('session_id') or '')[:8]} | {r.get('tool','')} | "
                 f"{r.get('start','')[:16]} | {r.get('duration_min','')} | "
                 f"{int(float(r.get('total_tokens') or 0)):,} | {loc} | {r.get('commits','0')} |")
    path = os.path.join(out_dir, "diario", f"{day}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return path

# ---------------------------------------------------------------- localizacion

def find_latest_transcript():
    base = os.path.expanduser("~/.claude/projects")
    cands = glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True)
    return max(cands, key=os.path.getmtime) if cands else None

def default_out_dir(cwd):
    return os.path.join(cwd or os.getcwd(), "analisis", "sesiones")

def take_opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        val = argv[i + 1] if len(argv) > i + 1 else default
        del argv[i:i + 2]
        return val
    return default

# ---------------------------------------------------------------- main

def main():
    argv = sys.argv[1:]
    out_dir = take_opt(argv, "--out-dir")
    tool = take_opt(argv, "--tool")
    source = take_opt(argv, "--source", "auto")
    since_arg = take_opt(argv, "--since")
    session_id_arg = take_opt(argv, "--session-id")
    meta_arg = take_opt(argv, "--meta")
    meta = None
    if meta_arg:
        try:
            meta = json.loads(meta_arg)
        except Exception:
            print("--meta no es JSON valido; se ignora.", file=sys.stderr)

    # modo diario
    if "--daily" in argv:
        i = argv.index("--daily")
        day = argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("-") \
            else now_utc().date().isoformat()
        out_dir = out_dir or default_out_dir(os.getcwd())
        p = build_daily(os.path.join(out_dir, "sessions-log.csv"), out_dir, day)
        if p:
            print(p)
        return

    # localizar transcript / hook
    transcript, hook_cwd = None, None
    if "--stdin-hook" in argv:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        transcript = payload.get("transcript_path")
        hook_cwd = payload.get("cwd")
        tool = tool or "claude-code"
    else:
        pos = [a for a in argv if not a.startswith("-")]
        if pos:
            transcript = pos[0]

    git_only = (source == "git")
    if source == "auto" and not transcript:
        transcript = find_latest_transcript()

    if git_only or not transcript or not os.path.exists(transcript or ""):
        # ---- modo git-only (Antigravity / Copilot / Bob / CLI) ----
        cwd = hook_cwd or os.getcwd()
        tool = tool or "unknown"
        since = parse_iso(since_arg) or datetime.combine(
            now_utc().date(), dtime.min, tzinfo=timezone.utc)
        d = empty_session(
            session_id=session_id_arg or f"{tool}-{since.date().isoformat()}",
            cwd=cwd, tool=tool)
        d["first_ts"], d["last_ts"] = since, now_utc()
    else:
        # ---- modo Claude (transcript) ----
        rows = load_transcript(transcript)
        d = analyze_claude(rows, tool=tool or "claude-code")

    cwd = d["cwd"] or hook_cwd or os.getcwd()
    out_dir = out_dir or default_out_dir(cwd)
    os.makedirs(os.path.join(out_dir, "diario"), exist_ok=True)

    # meta: argumento + sidecar
    apply_meta(d, meta)
    side, side_path = load_sidecar(out_dir)
    if side:
        apply_meta(d, side)
        try:
            os.remove(side_path)   # consumir para no duplicar
        except Exception:
            pass

    gitinfo = git_commits(cwd, d["first_ts"], d["last_ts"])

    md = render_md(d, gitinfo)
    sid = d["session_id"] or "sesion"
    md_path = os.path.join(out_dir, f"report-{sid}.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md + "\n")

    csv_path = os.path.join(out_dir, "sessions-log.csv")
    row = csv_row(d, gitinfo)
    upsert_csv(csv_path, row)
    if row["date"]:
        build_daily(csv_path, out_dir, row["date"])

    print(md_path)
    print(csv_path)


if __name__ == "__main__":
    main()
