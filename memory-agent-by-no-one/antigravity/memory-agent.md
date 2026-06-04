# memory-agent by no one (Antigravity)

Regla para memoria persistente entre sesiones en Antigravity.
Instala en `.antigravity/` del repo o en tu config global `~/.gemini/antigravity/`.

## Prerequisito

```bash
brew install gentleman-programming/tap/engram
```

Agregar a `~/.gemini/antigravity/mcp_config.json`:
```json
{
  "mcpServers": {
    "engram": { "command": "engram", "args": ["mcp"] }
  }
}
```

## Instruccion

Al iniciar: llama `mem_current_project` y `mem_context` para recuperar
contexto de sesiones anteriores.

Guarda memoria con `mem_save` inmediatamente despues de cualquier decision,
bugfix, patron o descubrimiento. Formato obligatorio:
- title: verbo + que (corto y buscable)
- type: bugfix | decision | architecture | discovery | pattern | config | preference
- content con secciones **What** / **Why** / **Where** / **Learned**

Para buscar: `mem_context` primero, luego `mem_search` si no encontro.
Ante conflictos (`judgment_required: true`): resolver con `mem_judge`.

Antes de cerrar sesion: llamar `mem_session_summary` con Goal / Instructions /
Discoveries / Accomplished / Next Steps / Relevant Files.
