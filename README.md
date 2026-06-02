# Skill-NoOne

Skills de productividad para equipos que usan AI coding tools.
Funciona en **Claude Code · Antigravity · GitHub Copilot · IBM Bob**.

## Skills disponibles

| Skill | Que hace |
|---|---|
| [session-report](session-report/) | Documenta cada sesion: tokens, modelo, archivos, LOC, commits, compilo/testeo. CSV maestro + consolidado diario. |
| [git-flow](git-flow/) | Flujo Gitflow completo y seguro para entorno local. Commits Conventional Commits estricto. Respaldo automatico. |

## Instalacion rapida

```bash
git clone https://github.com/AIByNoOne/Skill-NoOne.git
cd Skill-NoOne
./install.sh --all --project /ruta/a/tu/repo
```

Requisitos: `python3` y `git`. Sin dependencias externas.

Opciones del instalador:
```bash
./install.sh                        # CLI globales + skills de Claude Code
./install.sh --claude-hook          # + hook SessionEnd automatico
./install.sh --all --project DIR    # + wrappers de Copilot/Antigravity/Bob en tu repo
```

Los comandos se instalan en `~/.local/bin/`:
- `session-report` — reporte de sesion
- `flow`           — flujo git

## Uso rapido

```bash
# Session report
session-report          # Claude Code (tokens automaticos)
session-report --daily  # Consolidado del dia

# Git flow
flow init               # Inicializa Gitflow en el repo actual
flow status             # Estado actual
flow feature start login
flow commit -m "feat(auth): agrega login con email"
flow feature finish
```

## Estructura del repositorio

```
Skill-NoOne/
├── README.md
├── AGENTS.md            ← leido por Copilot / Antigravity / IBM Bob
├── install.sh
├── session-report/
│   ├── bin/report.py
│   ├── claude-code/SKILL.md
│   ├── github-copilot/ · antigravity/ · ibm-bob/
│   └── VERSION
└── git-flow/
    ├── bin/flow.py
    ├── claude-code/SKILL.md
    ├── github-copilot/ · antigravity/ · ibm-bob/
    └── VERSION
```
