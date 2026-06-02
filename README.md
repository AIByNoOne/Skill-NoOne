# session-report — kit compartible

Documenta cada **sesion de trabajo** con datos precisos: consumo de tokens,
modelo usado, skills/comandos, objetos (archivos) creados y modificados, lineas
de codigo, **commits de git** (con archivos y `+/-` por commit), si compilo y si
testeo. Mantiene un **CSV maestro** y un **consolidado diario**.

Pensado para usarse en equipo y de forma **local** en:
**Claude Code · Antigravity · GitHub Copilot · IBM Bob**.

---

## Que es exacto y que no (importante)

| Metrica | Claude Code | Antigravity / Copilot / IBM Bob |
|---|---|---|
| Commits, archivos, LOC (git) | ✅ exacto | ✅ exacto (universal) |
| Compilo / testeo | ⚠️ heuristico | ⚠️ heuristico |
| Tokens / modelo / skills | ✅ exacto (transcript JSONL) | ⚙️ manual via `--meta` |

> El consumo exacto de tokens se lee del **transcript JSONL**, un artefacto que
> **solo genera Claude Code**. Las demas herramientas no exponen ese archivo, asi
> que su modelo y tokens se aportan con `--meta` (lo rellena el agente o el usuario).
> Todo lo basado en **git** es exacto en cualquier herramienta.

---

## Estructura del kit

```
session-report-kit/
├── README.md                 ← este archivo
├── AGENTS.md                 ← estandar abierto (Copilot/Antigravity/Bob)
├── install.sh                ← instalador local
├── VERSION
├── bin/report.py             ← motor unico (toda la logica)
├── claude-code/SKILL.md      ← skill de Claude Code
├── github-copilot/session-report.prompt.md
├── antigravity/session-report.md
└── ibm-bob/session-report.md
```

## Instalacion

Requisitos: `python3` y `git`. Sin dependencias externas.

```bash
# CLI global + skill de Claude Code:
./install.sh

# + hook automatico de Claude Code (genera el reporte al cerrar sesion):
./install.sh --claude-hook

# + wrappers de Copilot/Antigravity/Bob dentro de un repo concreto:
./install.sh --all --project /ruta/a/mi/repo
```

El instalador crea el comando `session-report` en `~/.local/bin`. Asegurate de
tener esa carpeta en el `PATH`.

## Uso

```bash
# Claude Code (auto: lee tokens y modelo del transcript)
session-report

# Otras herramientas (git + modelo/tokens manuales)
session-report --source git --tool github-copilot \
  --meta '{"model":"gpt-5","input_tokens":0,"output_tokens":0}'

# Consolidado del dia
session-report --daily            # hoy
session-report --daily 2026-06-01 # una fecha
```

Salida en `analisis/sesiones/` del repo de trabajo:
`report-<id>.md`, `sessions-log.csv`, `diario/<fecha>.md`.

## Compartir con el equipo

Este kit es una carpeta autocontenida. Opciones:
- **Repo git:** publicalo y que cada quien clone y corra `./install.sh`.
- **Archivo:** comparte el `.tar.gz` generado; descomprimir y `./install.sh`.

## Extender la deteccion de build/test

Si tu equipo usa comandos de compilacion o test poco comunes, anade el patron en
`bin/report.py` (`COMPILE_RE` / `TEST_RE`).
