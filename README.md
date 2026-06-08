# Skill-NoOne

Skills de productividad para equipos que usan AI coding tools.
Funciona en **Claude Code · Antigravity · GitHub Copilot · IBM Bob**.

## Skills disponibles

| Skill | Que hace |
|---|---|
| [session-report](session-report/) | Documenta cada sesion: tokens, modelo, archivos, LOC, commits, compilo/testeo. CSV maestro + consolidado diario. |
| [git-flow](git-flow/) | Flujo Gitflow completo y seguro para entorno local. Commits Conventional Commits estricto. Respaldo automatico. |
| [memory-agent-by-no-one](memory-agent-by-no-one/) | Memoria persistente entre sesiones. Guarda decisiones, bugfixes y contexto en SQLite local. Motor: engram. Sin servicios externos. |
| [as400-quality](as400-quality/) | Calidad de codigo AS/400 (IBM i) estilo SonarQube, 100% local. Analisis estatico + semantico de RPG/SQLRPGLE/CL/DDS/SQL, metricas, quality gate. |

## Instalacion rapida

```bash
git clone https://github.com/AIByNoOne/Skill-NoOne.git
cd Skill-NoOne
./install.sh --all --project /ruta/a/tu/repo
```

Requisitos: `python3` y `git`. Sin dependencias externas.
`memory-agent-by-no-one` requiere ademas el binario `engram`:
```bash
brew install gentleman-programming/tap/engram
```

Opciones del instalador:
```bash
./install.sh                        # CLI globales + skills de Claude Code
./install.sh --claude-hook          # + hook SessionEnd automatico
./install.sh --all --project DIR    # + wrappers de Copilot/Antigravity/Bob en tu repo
```

Los comandos se instalan en `~/.local/bin/`:
- `session-report` — reporte de sesion
- `flow`           — flujo git
- `memory-agent`   — helper de verificacion/backup (requiere engram instalado)
- `as400-quality`  — analisis de calidad de codigo AS/400 (estatico + semantico)

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

# Calidad AS/400 (estilo SonarQube, local)
as400-quality src                          # analisis estatico de la carpeta src/
as400-quality src --json scan.json         # + reporte JSON (semantico lo completa el agente)
```

## Estructura del repositorio

```
Skill-NoOne/
├── README.md
├── AGENTS.md                     ← leido por Copilot / Antigravity / IBM Bob
├── install.sh
├── session-report/
│   ├── bin/report.py
│   ├── claude-code/SKILL.md
│   ├── github-copilot/ · antigravity/ · ibm-bob/
│   └── VERSION
├── git-flow/
│   ├── bin/flow.py
│   ├── claude-code/SKILL.md
│   ├── github-copilot/ · antigravity/ · ibm-bob/
│   └── VERSION
├── memory-agent-by-no-one/
│   ├── bin/setup.py              ← helper de verificacion/backup
│   ├── claude-code/SKILL.md
│   ├── github-copilot/ · antigravity/ · ibm-bob/
│   └── VERSION
└── as400-quality/
    ├── bin/analyze.py            ← scanner determinista (metricas + reglas)
    ├── claude-code/SKILL.md
    ├── github-copilot/ · antigravity/ · ibm-bob/
    └── VERSION
```
