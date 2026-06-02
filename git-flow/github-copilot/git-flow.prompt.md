---
mode: agent
description: Flujo Gitflow local seguro con Conventional Commits.
---

# /git-flow (GitHub Copilot)

Ejecuta operaciones git usando el CLI `flow` desde la raiz del repositorio.

## Comandos disponibles
```bash
flow init
flow status
flow feature start <nombre> | flow feature finish
flow release start <X.Y.Z>  | flow release finish
flow hotfix  start <X.Y.Z>  | flow hotfix  finish
flow commit [-m "tipo(scope): asunto"]
flow save | flow undo | flow discard <archivo|all> [--yes]
flow backup | flow restore | flow log
```

Si `flow` no esta en el PATH: `python3 <ruta-al-kit>/git-flow/bin/flow.py`.

## Reglas
- Siempre usa `flow commit`, nunca `git commit` directo.
- Conventional Commits obligatorio: `tipo(scope): asunto`
  Tipos: feat fix chore docs refactor test perf build ci style revert
- Ante `discard all` o `finish` de release/hotfix: **confirma con el usuario antes**.
- Si el repo no esta inicializado con Gitflow: `flow init` primero.

> Nota: instala el prompt file en `.github/prompts/` del repo.
