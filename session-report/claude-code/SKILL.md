---
name: session-report
description: Genera un reporte preciso de la sesion de trabajo (tokens por modelo, skills usadas, archivos creados/modificados, lineas de codigo, commits de git, si compilo y si testeo) desde el transcript JSONL, con CSV maestro y consolidado diario. Usar cuando el usuario pida documentar/medir una sesion, un resumen de consumo, o el consolidado diario.
---

# session-report (Claude Code)

Documenta una sesion con datos **exactos** leidos del transcript JSONL en disco.
La aritmetica la hace el script Python `report.py` (no el LLM).

## Ejecutar
Sesion actual (autodetecta el transcript mas reciente):
```bash
python3 ~/.claude/skills/session-report/report.py
```
Transcript especifico:
```bash
python3 ~/.claude/skills/session-report/report.py /ruta/al/transcript.jsonl
```
Consolidado diario:
```bash
python3 ~/.claude/skills/session-report/report.py --daily 2026-06-01
```

## Salida
- `analisis/sesiones/report-<sessionId>.md`
- `analisis/sesiones/sessions-log.csv`
- `analisis/sesiones/diario/<fecha>.md`

## Pasos para Claude
1. Ejecuta el script con Bash; imprime las rutas.
2. Lee el `report-<sessionId>.md` y resume: tokens por modelo, archivos, LOC,
   commits, compilo/testeo.
3. Si el directorio no es repo git, avisa y ofrece `git init`.

## Precision y limites
- Exacto: tokens, modelo, archivos, LOC por transcript, commits y LOC por commit (git).
- Heuristico: compilo/testeo (no hay exit code en el transcript). Comandos raros de
  build/test pueden no detectarse; anadir patron en `COMPILE_RE` / `TEST_RE`.
- El hook `SessionEnd` lo corre automaticamente al cerrar la sesion.
