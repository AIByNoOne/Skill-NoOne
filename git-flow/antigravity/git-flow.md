# git-flow (Antigravity)

Regla para usar el flujo Gitflow local en Antigravity.
Instala en `.antigravity/` del repo o en tu config global.

## Instruccion

Usa el CLI `flow` para todas las operaciones git:
```bash
flow init | flow status | flow log
flow feature start <nombre> | flow feature finish
flow release start <X.Y.Z>  | flow release finish
flow hotfix  start <X.Y.Z>  | flow hotfix  finish
flow commit [-m "tipo(scope): asunto"]
flow save | flow undo | flow discard <archivo|all> [--yes]
flow backup | flow restore
```

Nunca uses `git commit` directamente: usa `flow commit` para garantizar
el formato Conventional Commits y los guardrails de seguridad.

Si `flow` no esta en el PATH: `python3 <ruta-al-kit>/git-flow/bin/flow.py`.
