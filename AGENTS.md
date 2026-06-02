# AGENTS.md — session-report

> Estandar abierto leido por GitHub Copilot, Antigravity, IBM Bob y otros agentes.
> Define el comando **session-report** para documentar cada sesion de trabajo.

## Cuando usarlo
Cuando el usuario pida "documentar la sesion", "reporte de consumo", "cuanto gaste",
"metricas del dia" o el consolidado diario.

## Como ejecutarlo

El motor es un unico script Python portable: `bin/report.py` (instalado tambien como
`session-report` en el PATH). Ejecutalo desde la raiz del repositorio de trabajo.

**Reporte de la sesion actual** (sustituye `<TOOL>` por: `github-copilot`,
`antigravity`, `ibm-bob`, o `claude-code`):

```bash
session-report --source git --tool <TOOL> \
  --meta '{"model":"<MODELO-QUE-USAS>","input_tokens":0,"output_tokens":0}'
```

- Rellena `model` con el modelo que estas usando.
- Si conoces el consumo de tokens, ponlo en `input_tokens` / `output_tokens`;
  si no, dejalos en 0 (las metricas de git, archivos y LOC siguen siendo exactas).
- En **Claude Code** no hace falta `--meta` ni `--source`: los tokens y el modelo
  se leen automaticamente del transcript. Usa solo `session-report`.

**Consolidado diario:**

```bash
session-report --daily
```

## Salida
- `analisis/sesiones/report-<id>.md` — reporte legible de la sesion.
- `analisis/sesiones/sessions-log.csv` — registro maestro acumulado.
- `analisis/sesiones/diario/<fecha>.md` — consolidado del dia.

## Pasos para el agente
1. Ejecuta el comando con el `--tool` correcto y `--meta` con tu modelo.
2. Lee el `report-*.md` generado y resume al usuario: tokens, archivos, LOC,
   commits, si compilo y si testeo.
3. Si el directorio no es repo git, avisa que la seccion de commits queda vacia.

## Precision
- **Exacto en cualquier herramienta:** commits, archivos tocados, LOC por commit (git).
- **Exacto solo en Claude Code:** tokens, modelo y skills (via transcript JSONL).
- **Manual/agente en otras herramientas:** tokens y modelo via `--meta`.
- **Heuristico:** etiqueta compilo/testeo (patron de comando + salida).
