# as400-quality (Antigravity)

Regla para analizar la calidad del codigo AS/400 (IBM i) estilo SonarQube, 100% local.
Instala en `.antigravity/` del repo o en tu config global.

## Instruccion

Evalua RPG IV (fixed/mixed/fully-free), SQLRPGLE, CL, DDS y SQL en dos capas obligatorias.

**Capa estatica** — corré el scanner:
```bash
as400-quality src --json quality-reports/scan.json
# si no esta en PATH:
python3 <ruta-al-kit>/as400-quality/bin/analyze.py src --json -
```
Da metricas (LOC, densidad de comentarios, complejidad ciclomatica) e issues por archivo.
Exit code 1 si el quality gate da FAIL.

**Capa semantica** (no omitir):
- Cruzá cada `dcl-f` con su DDS antes de revisar: un nombre en mayusculas no declarado es
  valido si es campo externo del record format.
- Verificá `%EOF` tras READ, `%FOUND` tras CHAIN, variables sin inicializar, division por
  cero, `SQLCOD` tras EXEC SQL, SQL dinamico con parameter markers, credenciales hardcodeadas,
  duplicacion y complejidad.

**No generes falsos positivos**: en PUB400 el I/O nativo es deliberado; `GOTO` de error en CL
es idiomatico; los mega-archivos de prueba van fuera del gate del codigo real.

El entregable es un reporte consolidado (gate + Bug/Vulnerability/Smell + metricas + fixes
accionables con archivo:linea). Correr solo el script es resultado parcial.
