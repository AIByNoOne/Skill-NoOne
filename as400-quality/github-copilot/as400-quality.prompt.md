---
mode: agent
description: Analisis de calidad de codigo AS/400 (IBM i) estilo SonarQube, 100% local.
---

# /as400-quality (GitHub Copilot)

Evalua la calidad del codigo IBM i (RPG IV fixed/mixed/fully-free, SQLRPGLE, CL, DDS, SQL)
en dos capas **obligatorias**: estatica (script) + semantica (tu lectura). Sin servicios externos.

## Capa estatica
```bash
as400-quality src --json quality-reports/scan.json
# si no esta en PATH:
python3 <ruta-al-kit>/as400-quality/bin/analyze.py src --json -
```
Devuelve metricas (LOC, densidad de comentarios, complejidad ciclomatica) e issues `[auto]`
por archivo. Exit code 1 si el quality gate da FAIL (hay BLOCKER/CRITICAL).

## Capa semantica (no omitir)
1. **Cruzá cada `dcl-f` con su DDS** antes de revisar: un nombre en mayusculas no declarado
   es valido si es campo externo del record format. No lo marques como bug sin verificar.
2. Revisá: `%EOF` tras READ, `%FOUND` tras CHAIN, variables sin inicializar, division por
   cero, `SQLCOD` tras EXEC SQL; SQL dinamico con parameter markers (`?`), credenciales
   hardcodeadas; duplicacion, anidamiento, numeros magicos, subrutinas vs subprocedimientos.

## Reglas de contexto (no generar falsos positivos)
- I/O nativo en vez de EXEC SQL en PUB400 es deliberado: no marcar.
- `GOTO` en CL hacia etiqueta de error tras `MONMSG`: idiomatico, no penalizar.
- Mega-archivos/fuentes de prueba: reportar aparte, fuera del gate del codigo real.

## Salida
Reporte consolidado: quality gate, conteo Bug/Vulnerability/Smell, metricas por archivo y
recomendaciones accionables (archivo:linea + fix). Correr solo el script es resultado parcial.

> Nota: instala este prompt file en `.github/prompts/` del repo.
