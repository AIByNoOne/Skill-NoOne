# session-report (Antigravity)

Workflow/regla para documentar la sesion de trabajo en Antigravity.

Instalacion: copia este archivo a las reglas o workflows de Antigravity de tu
proyecto (carpeta `.antigravity/` del repo) o a tu config global. Verifica la
ruta exacta en tu version de Antigravity; el contenido es el mismo.

## Instruccion

Cuando el usuario pida documentar la sesion o un reporte de consumo, ejecuta en
la terminal, desde la raiz del repositorio:

```bash
session-report --source git --tool antigravity \
  --meta '{"model":"<MODELO-QUE-USAS>","input_tokens":0,"output_tokens":0}'
```

- Pon en `model` el modelo activo (p.ej. `gemini-3-pro`).
- Si conoces tokens consumidos, rellenalos; si no, dejalos en 0.
- Commits, archivos y LOC se miden con exactitud desde git.

Si `session-report` no esta en el PATH:
`python3 <ruta-al-kit>/bin/report.py` con los mismos argumentos.

Luego lee `analisis/sesiones/report-*.md` y resume al usuario. Para el acumulado
del dia: `session-report --daily`.
