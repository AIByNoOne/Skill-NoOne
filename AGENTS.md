# AGENTS.md — Skill-NoOne

> Estandar abierto leido por GitHub Copilot, Antigravity, IBM Bob y otros agentes.
> Define las skills **session-report**, **git-flow**, **memory-agent-by-no-one** y **as400-quality**.

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

---

## skill: memory-agent-by-no-one

Memoria persistente entre sesiones. Guarda decisiones, bugfixes, patrones y
contexto en SQLite local. Motor interno: engram (Gentleman-Programming).
Sin servicios externos, sin API keys, sin costo por uso.

### Prerequisito
```bash
brew install gentleman-programming/tap/engram
```
Configurar el MCP en tu agente con: `{"command": "engram", "args": ["mcp"]}`

### Cuando usarlo
"recuerda que", "guarda esto", "acordate de", "que hicimos con",
"como resolvimos", "busca en la memoria", "remember that", "recall"

### Al iniciar sesion
Llamar `mem_current_project` y `mem_context` antes de responder al usuario
si se menciona un proyecto o problema previo.

### Guardar memoria
Llamar `mem_save` inmediatamente despues de decision, bugfix, patron o
descubrimiento. Formato:
```
title: verbo + que (corto y buscable)
type: bugfix | decision | architecture | discovery | pattern | config | preference
content:
  **What**: que se hizo
  **Why**: que lo motivo
  **Where**: archivos afectados
  **Learned**: gotchas (omitir si no hay)
```

### Buscar memoria
1. `mem_context` — sesiones recientes (rapido)
2. `mem_search(query)` — FTS5 full-text si no encontro
3. `mem_get_observation(id)` — contenido completo

### Cerrar sesion (obligatorio)
Llamar `mem_session_summary` antes de "listo" o "terminamos":
Goal / Instructions / Discoveries / Accomplished / Next Steps / Relevant Files

### Pasos para el agente
1. Al iniciar: detectar proyecto con `mem_current_project`, recuperar contexto con `mem_context`.
2. Despues de cada trabajo significativo: guardar con `mem_save`.
3. Si `mem_save` devuelve `judgment_required: true`: resolver conflicto con `mem_judge`.
4. Al cerrar: llamar `mem_session_summary` siempre.

### Nota sobre compatibilidad
- Claude Code, Antigravity, Codex, Gemini CLI, VS Code: soporte oficial de engram.
- IBM Bob: funciona si soporta MCP stdio estandar (no verificado oficialmente).

---

## skill: as400-quality

Analiza la calidad del codigo AS/400 (IBM i) estilo SonarQube, 100% local y sin
servicios externos. Cubre RPG IV (fixed/mixed/fully-free), SQLRPGLE, CL, DDS y SQL.

### Cuando usarlo
"revisa la calidad del codigo", "code review AS/400", "busca bugs o vulnerabilidades",
"metricas de complejidad", "quality gate", "deuda tecnica", "como SonarQube", "linter RPG"

### Dos capas (ambas obligatorias)
1. **Estatica** — el CLI `as400-quality` (motor `analyze.py`): clasifica formato, calcula
   metricas (LOC, densidad de comentarios, complejidad ciclomatica) y aplica reglas por
   patron. Exit code 1 si el quality gate da FAIL → integrable en CI/CD.
2. **Semantica** — el agente lee el codigo y razona lo que el regex no ve: bugs de logica,
   SQL injection real, duplicacion, cross-reference RPG<->DDS.

### Comando
```bash
as400-quality src --json quality-reports/scan.json
# si no esta en PATH:
python3 <ruta-al-kit>/as400-quality/bin/analyze.py src --json -
```

### Pasos para el agente
1. Definir alcance (default `src/`) y correr `as400-quality` (capa estatica).
2. **Antes de revisar logica RPG**, cruzar cada `dcl-f` con su DDS: un nombre en mayusculas
   no declarado es valido si es campo externo del record format (no marcar como bug sin verificar).
3. Revisar semanticamente: `%EOF` tras READ, `%FOUND` tras CHAIN, variables sin inicializar,
   division por cero, `SQLCOD` tras EXEC SQL, SQL dinamico con parameter markers (`?`),
   credenciales hardcodeadas, duplicacion, complejidad.
4. Reglas de contexto (no falsos positivos): I/O nativo en PUB400 es deliberado; `GOTO` de
   error en CL es idiomatico; mega-archivos de prueba van fuera del gate del codigo real.
5. Entregar reporte consolidado: quality gate, conteo Bug/Vulnerability/Smell, metricas por
   archivo y fixes accionables (archivo:linea). Correr solo el script es resultado parcial.

### Severidades y gate
BLOCKER > CRITICAL > MAJOR > MINOR > INFO. Gate: PASS (0 issues) · WARN (sin BLOCKER/CRITICAL)
· FAIL (≥1 BLOCKER/CRITICAL, exit 1).
