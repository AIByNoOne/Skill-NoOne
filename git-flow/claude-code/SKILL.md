---
name: git-flow
description: Flujo Gitflow completo y seguro para entorno local. Inicializa repos, maneja ramas (feature/release/hotfix), commits con Conventional Commits estricto, deshacer/descartar con respaldo automatico. Usar para cualquier operacion git en el proyecto.
---

# git-flow (Claude Code)

Flujo Gitflow local con motor determinista `flow.py`. El CLI maneja la seguridad
(backups, validaciones) y el agente aporta el juicio (nombre de rama, mensaje).

## Comandos
```bash
flow init
flow status
flow feature start <nombre> | flow feature finish
flow release start <X.Y.Z>  | flow release finish
flow hotfix  start <X.Y.Z>  | flow hotfix  finish
flow commit [-m "tipo(scope): asunto"]
flow save   [-m "mensaje wip"]
flow undo
flow discard <archivo|all> [--yes]
flow backup [etiqueta] | flow restore [tag]
flow log
```

## Pasos para Claude
1. Para commits: redacta el mensaje en formato Conventional Commits y ejecuta
   `flow commit -m "tipo(scope): asunto"`. Si el usuario no da el tipo, inferirlo.
2. Para destructivos (`discard all`, `hotfix/release finish`): confirmar con el
   usuario antes de ejecutar.
3. Si el repo no tiene Gitflow: ejecutar `flow init` primero.
4. Si `flow` no esta en el PATH: `python3 ~/.claude/skills/git-flow/flow.py`.

## Conventional Commits (estricto)
- Formato: `tipo(scope): asunto en minusculas`
- Tipos: feat fix chore docs refactor test perf build ci style revert
- Ejemplo: `feat(auth): agrega validacion de email`
- `flow commit` rechaza mensajes que no cumplan el formato.

## Modelo de ramas
```
main    → produccion (solo releases y hotfixes, tags vX.Y.Z)
develop → integracion
feature/* → desde develop, mergea a develop
release/* → desde develop, mergea a main + develop + tag
hotfix/*  → desde main,    mergea a main + develop + tag
```
