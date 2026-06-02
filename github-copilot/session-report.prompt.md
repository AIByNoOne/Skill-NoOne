---
mode: agent
description: Documenta la sesion de trabajo (commits, archivos, LOC, tokens) y genera el reporte.
---

# /session-report (GitHub Copilot)

Eres responsable de documentar esta sesion de trabajo. Ejecuta en la terminal,
desde la raiz del repositorio:

```bash
session-report --source git --tool github-copilot \
  --meta '{"model":"${input:modelo}","input_tokens":0,"output_tokens":0}'
```

- Sustituye `${input:modelo}` por el modelo que estas usando (p.ej. `gpt-5`, `claude-sonnet-4-6`).
- Si conoces el consumo de tokens, ponlo en `input_tokens` / `output_tokens`.
- Las metricas de git (commits, archivos, LOC) son exactas aunque no haya tokens.

Si `session-report` no esta en el PATH, usa la ruta directa al kit:
`python3 <ruta-al-kit>/bin/report.py ...` con los mismos argumentos.

Despues:
1. Abre `analisis/sesiones/report-*.md` y resume al usuario tokens, archivos, LOC,
   commits y si compilo/testeo.
2. Para el acumulado del dia: `session-report --daily`.

> Nota: la instalacion de prompt files de Copilot va en `.github/prompts/` del repo.
