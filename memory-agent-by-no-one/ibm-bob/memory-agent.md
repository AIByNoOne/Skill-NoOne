# memory-agent by no one (IBM Bob)

Instruccion para memoria persistente entre sesiones en IBM Bob.
Copia este archivo a la convencion de tu version de Bob,
o referencialo desde el AGENTS.md de la raiz del repo.

## Prerequisito

```bash
brew install gentleman-programming/tap/engram
```

Agregar en la config MCP de Bob:
```json
{
  "mcpServers": {
    "engram": { "command": "engram", "args": ["mcp"] }
  }
}
```

## Instruccion

Al iniciar: llama `mem_current_project` y `mem_context` para recuperar
contexto de sesiones anteriores antes de responder al usuario.

Guarda memoria con `mem_save` inmediatamente despues de cualquier
decision, bugfix, patron o descubrimiento. Formato:
- title: verbo + que (corto y buscable)
- type: bugfix | decision | architecture | discovery | pattern | config | preference
- content con secciones **What** / **Why** / **Where** / **Learned**

Para buscar: `mem_context` primero, luego `mem_search` con palabras clave.
Ante conflictos (`judgment_required: true`): resolver con `mem_judge`.

Antes de cerrar sesion: `mem_session_summary` con Goal / Instructions /
Discoveries / Accomplished / Next Steps / Relevant Files.

Nota: IBM Bob no tiene integracion oficial verificada con engram.
Funciona si Bob soporta servidores MCP stdio estandar.
