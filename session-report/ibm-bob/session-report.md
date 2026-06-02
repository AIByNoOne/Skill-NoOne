# session-report (IBM Bob)

Instruccion para documentar la sesion de trabajo en IBM Bob.

Instalacion: anade este comando a las instrucciones/custom commands de tu
proyecto en IBM Bob, o usa el `AGENTS.md` del kit en la raiz del repo (Bob lee
el estandar AGENTS.md). Verifica la convencion exacta en tu version de Bob.

## Instruccion

Cuando el usuario pida documentar la sesion o un reporte de consumo, ejecuta en
la terminal, desde la raiz del repositorio:

```bash
session-report --source git --tool ibm-bob \
  --meta '{"model":"<MODELO-QUE-USAS>","input_tokens":0,"output_tokens":0}'
```

- Pon en `model` el modelo activo (p.ej. `granite-*` u otro).
- Si conoces tokens consumidos, rellenalos; si no, dejalos en 0.
- Commits, archivos y LOC se miden con exactitud desde git.

Si `session-report` no esta en el PATH:
`python3 <ruta-al-kit>/bin/report.py` con los mismos argumentos.

Luego lee `analisis/sesiones/report-*.md` y resume al usuario. Para el acumulado
del dia: `session-report --daily`.
