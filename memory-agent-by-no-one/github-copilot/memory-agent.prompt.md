---
mode: agent
description: Memoria persistente entre sesiones usando engram (SQLite local, sin servicios externos).
---

# /memory-agent (GitHub Copilot)

Motor interno: engram — binario Go + SQLite local. Sin API keys, sin red.

## Prerequisito

```bash
brew install gentleman-programming/tap/engram
code --add-mcp '{"name":"engram","command":"engram","args":["mcp"]}'
```

## Uso

Al iniciar la sesion:
```
mem_current_project → mem_context → mem_search si el usuario menciona un tema
```

Guardar con `mem_save` inmediatamente despues de decision, bugfix, patron o descubrimiento:
```
title: verbo + que (buscable)
type: bugfix | decision | architecture | discovery | pattern | config | preference
content: **What** / **Why** / **Where** / **Learned**
```

Buscar: `mem_context` → `mem_search` → `mem_get_observation` para contenido completo.

Cerrar sesion: `mem_session_summary` con Goal / Discoveries / Accomplished / Next Steps.

Conflictos: si `mem_save` devuelve `judgment_required: true`, resolver con `mem_judge`.
