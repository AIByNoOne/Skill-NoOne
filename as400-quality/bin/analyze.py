#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py - Scanner de calidad de codigo AS/400 (IBM i), estilo SonarQube, 100% local.

Capa determinista de la skill `as400-quality`: clasifica cada fuente por lenguaje y
formato, calcula metricas (LOC, densidad de comentarios, complejidad ciclomatica
aproximada, tamano de procedimientos) y aplica las reglas detectables por patron del
catalogo (references/rule-catalog.md). El analisis semantico profundo (bugs de logica,
revision real de SQL dinamico, naming) lo hace Claude leyendo los archivos senalados.

Sin dependencias externas, sin servicios en la nube, sin API keys.

Uso:
  python3 analyze.py [RUTA ...]            # default: ./src
  python3 analyze.py src --json report.json
  python3 analyze.py src --json -          # JSON crudo a stdout (para pipes/CI)

Codigo de salida:
  0 = quality gate PASS / WARN
  1 = quality gate FAIL (hay issues BLOCKER o CRITICAL)
  2 = error de uso (no se encontraron fuentes)
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuracion de severidad y quality gate (ajustable)
# ---------------------------------------------------------------------------
SEVERITY_ORDER = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]
GATE_FAIL_ON = {"BLOCKER", "CRITICAL"}   # severidades que reprueban el gate

# Umbrales de metricas
LONGPROC_MINOR = 100     # lineas de codigo en una proc/subr -> MINOR
LONGPROC_MAJOR = 200     # -> MAJOR
COMPLEXITY_MINOR = 15    # complejidad ciclomatica por archivo -> MINOR
COMPLEXITY_MAJOR = 30    # -> MAJOR
LOWCOMMENT_PCT = 8.0     # densidad de comentarios minima (% del codigo)
RPG_FIXED_MAXCOL = 100   # ancho maximo razonable de una linea de fuente RPG

# Extensiones reconocidas
EXT_LANG = {
    ".rpgle": "RPG",
    ".sqlrpgle": "RPG",
    ".rpg": "RPG",
    ".clle": "CL",
    ".cl": "CL",
    ".clp": "CL",
    ".pf": "DDS",
    ".lf": "DDS",
    ".dspf": "DDS",
    ".prtf": "DDS",
    ".dds": "DDS",
    ".sql": "SQL",
    ".cbl": "COBOL",
    ".cblle": "COBOL",
    ".sqlcblle": "COBOL",
}


# ---------------------------------------------------------------------------
# Clasificacion de formato
# ---------------------------------------------------------------------------
def classify(path, lines):
    """Devuelve (lenguaje, formato, flags) para el archivo."""
    ext = os.path.splitext(path)[1].lower()
    lang = EXT_LANG.get(ext, "UNKNOWN")
    fmt = "n/a"
    flags = set()

    joined_lower = "\n".join(lines).lower()

    if lang == "RPG":
        first = next((l for l in lines if l.strip()), "")
        if first.strip().lower().startswith("**free"):
            fmt = "fully-free"
        elif "/free" in joined_lower or "/end-free" in joined_lower:
            fmt = "mixed"
        elif re.search(r"^\s{5}[hfdcpio]\s", "\n".join(lines), re.IGNORECASE | re.MULTILINE):
            fmt = "fixed"
        else:
            # sin marcador y sin specs en col 6 -> asumimos free moderno
            fmt = "fully-free"
        if re.search(r"\bexec\s+sql\b", joined_lower):
            flags.add("embedded-sql")
        if ext == ".sqlrpgle":
            flags.add("embedded-sql")
    elif lang == "DDS":
        sub = {
            ".pf": "physical-file", ".lf": "logical-file",
            ".dspf": "display-file", ".prtf": "printer-file",
        }
        fmt = sub.get(ext, "dds")
    elif lang == "CL":
        fmt = "ile-cl"
    elif lang == "COBOL":
        fmt = "cobol"
        if re.search(r"\bexec\s+sql\b", joined_lower):
            flags.add("embedded-sql")

    return lang, fmt, flags


# ---------------------------------------------------------------------------
# Deteccion de comentarios por lenguaje/formato
# ---------------------------------------------------------------------------
def is_comment(line, lang, fmt):
    s = line.strip()
    if not s:
        return False
    if lang == "RPG":
        if fmt == "fully-free":
            return s.startswith("//")
        # fixed/mixed: '*' en columna 7 (indice 6) o '//' dentro de bloque free
        if len(line) > 6 and line[6] == "*":
            return True
        return s.startswith("//") or s.startswith("*")
    if lang == "CL":
        return s.startswith("/*") and "*/" in s or s.startswith("/*")
    if lang == "DDS":
        if len(line) > 6 and line[6] == "*":
            return True
        return s.startswith("*")
    if lang == "SQL":
        return s.startswith("--") or s.startswith("/*")
    if lang == "COBOL":
        # col 7 = '*' o '/' marca comentario en formato fijo
        if len(line) > 6 and line[6] in ("*", "/"):
            return True
        return s.startswith("*>")
    return False


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
COMPLEXITY_KW = {
    "RPG": r"\b(IF|ELSEIF|WHEN|DOW|DOU|DOWLE|DOWGT|DOWEQ|FOR|FORE|CAS|CASEQ|CASNE|CASGT|CASLT|MONITOR|ITER|LEAVE|ANDEQ|OREQ)\b|\b(AND|OR)\b|\bWHEN\b",
    "CL": r"\b(IF|DO|DOWHILE|DOUNTIL|DOFOR|WHEN|MONMSG)\b|\b(AND|OR)\b",
    "SQL": r"\b(WHERE|CASE|WHEN|AND|OR|HAVING|JOIN)\b",
    "COBOL": r"\b(IF|WHEN|UNTIL|PERFORM|EVALUATE|AND|OR)\b",
}


def compute_metrics(lines, lang, fmt):
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comment = sum(1 for l in lines if is_comment(l, lang, fmt))
    code = total - blank - comment
    density = round((comment / code * 100.0), 1) if code else 0.0

    complexity = 1
    kw = COMPLEXITY_KW.get(lang)
    if kw:
        rx = re.compile(kw, re.IGNORECASE)
        for l in lines:
            if is_comment(l, lang, fmt):
                continue
            complexity += len(rx.findall(l))

    return {
        "lines_total": total,
        "lines_code": code,
        "lines_comment": comment,
        "lines_blank": blank,
        "comment_density_pct": density,
        "cyclomatic_complexity": complexity,
    }


# ---------------------------------------------------------------------------
# Deteccion de procedimientos / subrutinas y su tamano
# ---------------------------------------------------------------------------
def find_procedures(lines, lang, fmt):
    """Devuelve lista de (nombre, linea_inicio, lineas_codigo)."""
    procs = []
    if lang == "RPG":
        start, name = None, None
        for i, l in enumerate(lines, 1):
            s = l.strip().lower()
            m = re.match(r"(?:dcl-proc|begsr)\s+([\w$#@]+)", s)
            if m:
                start, name = i, m.group(1)
                continue
            if (s.startswith("end-proc") or s.startswith("endsr")) and start:
                procs.append((name, start, i - start - 1))
                start, name = None, None
    elif lang == "CL":
        # CL es un solo flujo; medimos el cuerpo entre PGM y ENDPGM
        body = [i for i, l in enumerate(lines, 1) if l.strip()]
        if body:
            procs.append(("PGM", body[0], body[-1] - body[0]))
    return procs


# ---------------------------------------------------------------------------
# Reglas detectables por patron
# ---------------------------------------------------------------------------
def add(issues, rule, severity, line, msg):
    issues.append({"rule": rule, "severity": severity, "line": line, "message": msg})


def run_rules(path, lines, lang, fmt, flags, metrics, procs):
    issues = []

    def code_lines():
        for i, l in enumerate(lines, 1):
            if not is_comment(l, lang, fmt) and l.strip():
                yield i, l

    # --- RPG ---
    if lang == "RPG":
        for i, l in code_lines():
            low = l.lower()
            # GOTO en RPG (en RPG es mal olor; en CL se acepta)
            if re.search(r"\bgoto\b", low):
                add(issues, "AS4-SMELL-GOTO", "MAJOR", i,
                    "GOTO en RPG: reemplazar por estructuras IF/DOW/DOU/LEAVE/ITER.")
            # Opcodes legacy
            if re.search(r"\b(move|movel|movea|z-add|z-sub|mult|div|add|sub)\b\s", low) and fmt != "fully-free":
                if re.search(r"\b(move|movel|movea|z-add|z-sub)\b", low):
                    add(issues, "AS4-SMELL-DEPOPCODE", "MINOR", i,
                        "Opcode legacy (MOVE/MOVEL/MOVEA/Z-ADD/Z-SUB): modernizar con EVAL/%-BIFs.")
            # CASxx deprecado
            if re.search(r"\bcas(eq|ne|gt|lt|ge|le)?\b", low) and "select" not in low:
                add(issues, "AS4-SMELL-CASXX", "MINOR", i,
                    "CASxx deprecado: usar SELECT/WHEN/OTHER/ENDSL.")
            # DSPLY (debug / no permitido por SSH en PUB400)
            if re.search(r"\bdsply\b", low):
                add(issues, "AS4-SMELL-DSPLY", "MINOR", i,
                    "DSPLY: resto de depuracion; escribir a archivo/data area en su lugar.")
            # DFTACTGRP(*YES) en mundo ILE
            if re.search(r"dftactgrp\s*\(\s*\*yes\s*\)", low):
                add(issues, "AS4-SMELL-DFTACTGRP", "MAJOR", i,
                    "DFTACTGRP(*YES) fuerza modo OPM; preferir DFTACTGRP(*NO) ACTGRP(...).")
            # SQL dinamico -> hotspot de seguridad
            if re.search(r"\b(execute\s+immediate|prepare)\b", low):
                add(issues, "AS4-VUL-DYNSQL", "MAJOR", i,
                    "SQL dinamico: revisar uso de parameter markers (?) para evitar SQL injection.")
            if "exec sql" in low and "+" in l and re.search(r"'\s*\+|\+\s*'", l):
                add(issues, "AS4-VUL-SQLCONCAT", "CRITICAL", i,
                    "Concatenacion de strings en sentencia SQL: posible SQL injection. Usar parameter markers.")
            # Tabs en fuente de columna fija
            if "\t" in l and fmt in ("fixed", "mixed"):
                add(issues, "AS4-BUG-TABS", "MAJOR", i,
                    "Caracter TAB en fuente de formato fijo: corrompe el alineamiento por columnas.")
            # Linea demasiado larga
            if len(l.rstrip("\n")) > RPG_FIXED_MAXCOL:
                add(issues, "AS4-STYLE-LINELEN", "MINOR", i,
                    "Linea supera %d columnas; el miembro fuente puede truncarla." % RPG_FIXED_MAXCOL)
            # TODO / FIXME
            if re.search(r"\b(todo|fixme|hack|xxx)\b", low):
                add(issues, "AS4-INFO-TODO", "INFO", i, "Marcador TODO/FIXME pendiente.")

        # SQL sin verificacion de estado
        if "embedded-sql" in flags:
            text = "\n".join(lines).lower()
            has_exec = re.search(r"exec\s+sql\s+(?!set\s+option|declare|include)", text)
            if has_exec and not re.search(r"\b(sqlcod|sqlstt|sqlstate)\b", text):
                add(issues, "AS4-BUG-NOSQLCHECK", "MAJOR", 0,
                    "Hay sentencias EXEC SQL ejecutables pero no se verifica SQLCOD/SQLSTT tras ellas.")

    # --- CL ---
    elif lang == "CL":
        has_global_monmsg = False
        for i, l in code_lines():
            up = l.upper()
            if "MONMSG" in up:
                has_global_monmsg = True
            if "\t" in l:
                add(issues, "AS4-BUG-TABS", "MINOR", i, "Caracter TAB en fuente CL.")
            if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", up):
                add(issues, "AS4-INFO-TODO", "INFO", i, "Marcador TODO/FIXME pendiente.")
        if not has_global_monmsg:
            add(issues, "AS4-BUG-NOMONMSG", "MAJOR", 0,
                "Programa CL sin MONMSG: errores no monitoreados pueden abortar el job sin control.")

    # --- DDS ---
    elif lang == "DDS":
        has_text = any("text(" in l.lower() for l in lines)
        if not has_text:
            add(issues, "AS4-SMELL-NOTEXT", "MINOR", 0,
                "DDS sin keyword TEXT/COLHDG: campos sin documentar dificultan el mantenimiento.")
        for i, l in enumerate(lines, 1):
            if "\t" in l:
                add(issues, "AS4-BUG-TABS", "MAJOR", i,
                    "Caracter TAB en DDS: corrompe el alineamiento por columnas.")

    # --- Metricas -> issues ---
    cc = metrics["cyclomatic_complexity"]
    if cc > COMPLEXITY_MAJOR:
        add(issues, "AS4-SMELL-COMPLEXITY", "MAJOR", 0,
            "Complejidad ciclomatica alta (%d): dividir en subprocedimientos." % cc)
    elif cc > COMPLEXITY_MINOR:
        add(issues, "AS4-SMELL-COMPLEXITY", "MINOR", 0,
            "Complejidad ciclomatica moderada (%d): considerar refactor." % cc)

    if metrics["lines_code"] >= 30 and metrics["comment_density_pct"] < LOWCOMMENT_PCT:
        add(issues, "AS4-SMELL-LOWCOMMENT", "MINOR", 0,
            "Densidad de comentarios baja (%.1f%%)." % metrics["comment_density_pct"])

    for name, start, length in procs:
        if length > LONGPROC_MAJOR:
            add(issues, "AS4-SMELL-LONGPROC", "MAJOR", start,
                "Procedimiento/subrutina '%s' muy largo (%d lineas): dividir." % (name, length))
        elif length > LONGPROC_MINOR:
            add(issues, "AS4-SMELL-LONGPROC", "MINOR", start,
                "Procedimiento/subrutina '%s' largo (%d lineas)." % (name, length))

    return issues


# ---------------------------------------------------------------------------
# Recorrido de archivos
# ---------------------------------------------------------------------------
def discover(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                if ".git" in root.split(os.sep):
                    continue
                for n in names:
                    if os.path.splitext(n)[1].lower() in EXT_LANG:
                        files.append(os.path.join(root, n))
    return sorted(set(files))


def read_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def analyze(paths):
    report = {"files": [], "summary": {}}
    sev_count = {s: 0 for s in SEVERITY_ORDER}
    totals = {"files": 0, "lines_total": 0, "lines_code": 0,
              "lines_comment": 0, "issues": 0}

    for path in discover(paths):
        lines = read_lines(path)
        lang, fmt, flags = classify(path, lines)
        if lang == "UNKNOWN":
            continue
        metrics = compute_metrics(lines, lang, fmt)
        procs = find_procedures(lines, lang, fmt)
        issues = run_rules(path, lines, lang, fmt, flags, metrics, procs)

        for it in issues:
            sev_count[it["severity"]] += 1
        totals["files"] += 1
        totals["lines_total"] += metrics["lines_total"]
        totals["lines_code"] += metrics["lines_code"]
        totals["lines_comment"] += metrics["lines_comment"]
        totals["issues"] += len(issues)

        report["files"].append({
            "path": path,
            "language": lang,
            "format": fmt,
            "flags": sorted(flags),
            "metrics": metrics,
            "procedures": [{"name": n, "line": s, "code_lines": ln} for n, s, ln in procs],
            "issues": sorted(issues, key=lambda x: (SEVERITY_ORDER.index(x["severity"]), x["line"])),
        })

    gate = "FAIL" if any(sev_count[s] for s in GATE_FAIL_ON) else (
        "WARN" if totals["issues"] else "PASS")

    report["summary"] = {
        "totals": totals,
        "by_severity": sev_count,
        "quality_gate": gate,
    }
    return report


def print_text(report):
    s = report["summary"]
    t = s["totals"]
    print("=" * 64)
    print(" AS/400 QUALITY REPORT  (motor local, estilo SonarQube)")
    print("=" * 64)
    print(" Archivos analizados : %d" % t["files"])
    print(" Lineas totales      : %d  (codigo %d / comentarios %d)" %
          (t["lines_total"], t["lines_code"], t["lines_comment"]))
    print(" Issues detectados   : %d" % t["issues"])
    print(" Por severidad       : " + "  ".join(
        "%s=%d" % (k, s["by_severity"][k]) for k in SEVERITY_ORDER))
    gate = s["quality_gate"]
    mark = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[gate]
    print(" QUALITY GATE        : %s %s" % (mark, gate))
    print("=" * 64)
    for f in report["files"]:
        if not f["issues"]:
            continue
        print("\n%s  (%s / %s)  CC=%d  densidad=%.1f%%" % (
            f["path"], f["language"], f["format"],
            f["metrics"]["cyclomatic_complexity"],
            f["metrics"]["comment_density_pct"]))
        for it in f["issues"]:
            loc = ("L%d" % it["line"]) if it["line"] else "file"
            print("  [%-8s] %-22s %-6s %s" % (
                it["severity"], it["rule"], loc, it["message"]))
    files_clean = [f["path"] for f in report["files"] if not f["issues"]]
    if files_clean:
        print("\nSin hallazgos por patron (revisar igual a nivel semantico):")
        for p in files_clean:
            print("  - %s" % p)


def main():
    ap = argparse.ArgumentParser(description="Scanner de calidad AS/400 local.")
    ap.add_argument("paths", nargs="*", default=["src"],
                    help="Archivos o carpetas a analizar (default: src).")
    ap.add_argument("--json", metavar="FILE",
                    help="Escribe el reporte JSON al archivo (o '-' para stdout).")
    args = ap.parse_args()

    paths = args.paths if args.paths else ["src"]
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        sys.stderr.write("error: no se encontraron rutas: %s\n" % ", ".join(paths))
        return 2

    report = analyze(existing)

    if args.json == "-":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text(report)
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            sys.stderr.write("JSON escrito en %s\n" % args.json)

    return 1 if report["summary"]["quality_gate"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
