---
name: session-report
description: Genera un reporte preciso de la sesion de trabajo (tokens por modelo, skills usadas, archivos creados/modificados, lineas de codigo, commits de git, si compilo y si testeo, resumen narrativo y lista de tareas). Desde el transcript JSONL, con CSV maestro y consolidado diario. Usar cuando el usuario pida documentar/medir una sesion, un resumen de consumo, o el consolidado diario.
---

# session-report (Claude Code)

Documenta una sesion con datos **exactos** leidos del transcript JSONL en disco.
La aritmetica la hace el script Python; el resumen narrativo lo generas tu.

## Pasos

### 1. Ejecutar el script
```bash
python3 ~/.claude/skills/session-report/report.py
```
El script imprime la ruta al `.md` generado.

### 2. Leer el reporte generado
Lee el archivo `.md` que devolvio el script. Contiene:
- Tokens exactos por modelo
- Archivos creados/modificados y LOC
- Commits de git (si hay repo)
- Compilaciones y tests detectados
- **Solicitudes del usuario** — los mensajes reales del transcript

### 3. Generar el resumen narrativo
Con los datos del reporte (especialmente "Solicitudes del usuario",
"Objetos creados y modificados" y "Commits"), genera DOS secciones en
español claro y conciso:

**## Resumen de trabajo**
Parrafo de 3-5 lineas describiendo QUE se hizo en la sesion: el objetivo
principal, las herramientas o skills construidas, decisiones tomadas.
Escrito para que alguien que no estuvo en la sesion entienda el resultado.

**## Tareas realizadas**
Lista de checkboxes con cada tarea completada, de lo mas concreto a lo mas
general. Basate en los archivos creados, commits y solicitudes del usuario.
Formato:
- [x] Descripcion concreta de la tarea
- [x] Otra tarea

### 4. Insertar el resumen en el reporte
Usa Edit para:
a) Insertar las dos secciones generadas justo despues de la linea
   `- **Turnos de usuario:**` y antes de `## Tokens y modelos`.
b) Eliminar el bloque `<!-- RESUMEN_PENDIENTE -->` y los comentarios
   que le siguen hasta el segundo `---`.

### 5. Responder al usuario
Resume en 3-4 lineas: que se hizo, cuantos tokens, archivos/LOC generados.

## Otros modos
```bash
# Transcript especifico:
python3 ~/.claude/skills/session-report/report.py /ruta/transcript.jsonl

# Consolidado diario:
python3 ~/.claude/skills/session-report/report.py --daily 2026-06-01
```

## Salida
- `analisis/sesiones/report-<sessionId>.md` — reporte completo con resumen
- `analisis/sesiones/sessions-log.csv` — log acumulado
- `analisis/sesiones/diario/<fecha>.md` — consolidado del dia

## Precision
- Exacto: tokens, modelo, archivos, LOC, commits (git numstat).
- Heuristico: compilo/testeo (patron de comando + salida).
- Narrativo: generado por Claude basado en los datos del transcript.
- El hook `SessionEnd` corre el script automaticamente al cerrar la sesion.
