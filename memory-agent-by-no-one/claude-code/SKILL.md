---
name: memory-agent-by-no-one
description: >
  Memoria persistente entre sesiones. Guarda decisiones, bugfixes, patrones
  y contexto usando SQLite local + FTS5. Sin servicios externos, sin API keys.
  Motor interno: engram (Gentleman-Programming).
  Usar cuando el usuario pide recordar algo, guardar contexto, o buscar trabajo pasado.
---

# memory-agent by no one (Claude Code)

Motor interno: **engram** — binario Go, SQLite + FTS5, todo local.
Sin red, sin costo por uso.

## Prerequisito

```bash
brew install gentleman-programming/tap/engram
claude plugin marketplace add Gentleman-Programming/engram && claude plugin install engram
```

## Disparadores

Activar cuando el usuario diga:
"recuerda que", "guarda esto", "acordate de", "¿qué hicimos con",
"¿cómo resolvimos", "busca en la memoria", "remember that", "save this", "recall"

## Al iniciar sesion

```
1. mem_current_project  → detecta el proyecto activo
2. mem_context          → recupera contexto de sesiones anteriores
3. Si el usuario menciona un tema → mem_search con esas palabras
```

## Guardar memoria

Llamar INMEDIATAMENTE despues de: bugfix, decision de arquitectura,
descubrimiento no obvio, cambio de config, patron establecido, preferencia del usuario.

```
title:     Verbo + que — corto y buscable  (ej: "Fije N+1 en UserList")
type:      bugfix | decision | architecture | discovery | pattern | config | preference
scope:     project (default) | personal | global
topic_key: (opcional) clave estable para temas evolutivos
content:
  **What**: Una oracion — que se hizo
  **Why**: Que lo motivo
  **Where**: Archivos o rutas afectadas
  **Learned**: Gotchas o sorpresas (omitir si no hay)
```

Reglas de topic_key:
- Reusar el mismo key para actualizar un tema (evita duplicados)
- Si no estas seguro del key → mem_suggest_topic_key primero
- Si tenes el ID exacto → mem_update en lugar de mem_save

## Buscar memoria

```
1. mem_context          → sesiones recientes (rapido)
2. mem_search(query)    → FTS5 full-text si no encontro
3. mem_get_observation  → contenido completo por ID
4. Si mem_save devuelve judgment_required: true → resolver con mem_judge
```

Busqueda proactiva: antes de empezar trabajo que pudo hacerse antes,
correr mem_search y comunicar los resultados al usuario.

## Cerrar sesion (obligatorio antes de "listo" o "terminamos")

```
mem_session_summary:
  ## Goal           — objetivo de la sesion
  ## Instructions   — restricciones del usuario
  ## Discoveries    — hallazgos importantes
  ## Accomplished   — que se completo
  ## Next Steps     — pendientes
  ## Relevant Files — archivos clave
```

## Herramientas MCP (19)

| Categoria         | Herramientas |
|---|---|
| Guardar / Editar  | mem_save, mem_update, mem_delete, mem_suggest_topic_key |
| Buscar            | mem_search, mem_context, mem_timeline, mem_get_observation |
| Ciclo de sesion   | mem_session_start, mem_session_end, mem_session_summary |
| Conflictos        | mem_judge, mem_compare |
| Utilidades        | mem_save_prompt, mem_stats, mem_capture_passive, mem_merge_projects, mem_current_project, mem_doctor |
