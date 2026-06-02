# AGENTS.md — Skill-NoOne

> Estandar abierto leido por GitHub Copilot, Antigravity, IBM Bob y otros agentes.
> Define las skills **session-report** y **git-flow**.

---

## skill: session-report

Documenta cada sesion de trabajo (tokens, modelo, archivos, LOC, commits,
compilo/testeo) y mantiene un CSV maestro y un consolidado diario.

### Cuando usarlo
"documentar la sesion", "reporte de consumo", "cuanto gaste", "metricas del dia"

### Comando
```bash
# Claude Code (tokens/modelo automaticos via transcript)
session-report

# Otras herramientas (git + modelo/tokens manuales)
session-report --source git --tool <TOOL> \
  --meta '{"model":"<MODELO>","input_tokens":0,"output_tokens":0}'

# Consolidado diario
session-report --daily
```

Salida en `analisis/sesiones/`: `report-<id>.md`, `sessions-log.csv`, `diario/<fecha>.md`.

### Precision
- Exacto en cualquier herramienta: commits, archivos, LOC (git).
- Exacto solo en Claude Code: tokens/modelo/skills (transcript JSONL).
- Manual en otras herramientas: tokens/modelo via `--meta`.

---

## skill: git-flow

Flujo Gitflow completo y seguro para entorno local. Commits en formato
Conventional Commits estricto. Respaldo automatico antes de toda operacion
destructiva.

### Cuando usarlo
Cualquier operacion git: iniciar feature, hacer commit, mergear, deshacer,
consultar estado, crear release o hotfix.

### Modelo de ramas
```
main      → produccion, solo recibe releases y hotfixes, tags vX.Y.Z
develop   → integracion continua
feature/* → trabajo nuevo (desde develop)
release/* → preparacion de version (desde develop → main + develop)
hotfix/*  → parche urgente (desde main → main + develop)
```

### Comandos
```bash
flow init                        # Inicializa Gitflow en el repo
flow status                      # Estado: rama, rol, cambios, proximos pasos

flow feature start <nombre>      # Nueva rama feature/<nombre> desde develop
flow feature finish              # Mergea a develop, borra la rama

flow release start <X.Y.Z>       # Nueva rama release/<X.Y.Z> desde develop
flow release finish              # Mergea a main + develop, crea tag vX.Y.Z

flow hotfix start <X.Y.Z>        # Nueva rama hotfix/<X.Y.Z> desde main
flow hotfix finish               # Mergea a main + develop, crea tag vX.Y.Z

flow commit [-m "tipo(scope): asunto"]   # Commit guiado, valida Conventional Commits
flow save   [-m "mensaje"]               # Checkpoint WIP rapido
flow undo                                # Deshace ultimo commit (conserva cambios)
flow discard <archivo|all>               # Descarta cambios (pide --yes)
flow backup                              # Snapshot manual de seguridad
flow restore                             # Lista y restaura backups
flow log                                 # Historial en grafo
```

### Pasos para el agente
1. Ejecuta el comando `flow` apropiado desde la raiz del repo.
2. Lee la salida y comunica el resultado al usuario (rama actual, que cambio, que sigue).
3. Ante destructivos (`discard all`, `finish` en main), **confirma con el usuario antes**.
4. Si el repo no tiene Gitflow inicializado, corre `flow init` primero.

### Conventional Commits (obligatorio)
Formato: `tipo(scope): asunto en minusculas`
Tipos validos: feat, fix, chore, docs, refactor, test, perf, build, ci, style, revert
Ejemplo: `feat(auth): agrega validacion de email`
`flow commit` rechaza mensajes que no cumplan este formato.
