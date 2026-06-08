---
name: as400-quality
description: Analiza la calidad del codigo AS/400 (IBM i) estilo SonarQube, 100% local y sin servicios externos. Clasifica fuentes RPG IV (fixed/mixed/fully-free), SQLRPGLE, CL, DDS y SQL; calcula metricas (LOC, densidad de comentarios, complejidad ciclomatica), detecta bugs/vulnerabilidades/code smells con un scanner determinista y los complementa con revision semantica, aplica un quality gate y genera un reporte consolidado. Usar cuando el usuario pida "revisar calidad del codigo", "analizar codigo RPG", "code review AS/400", "buscar bugs o vulnerabilidades", "metricas de complejidad", "quality gate", "deuda tecnica", "como SonarQube", "linter RPG", o evaluar .rpgle/.sqlrpgle/.clle/.pf/.lf/.dspf/.prtf/.sql.
---

# as400-quality (Claude Code)

Calidad de codigo IBM i estilo SonarQube, **100% local** — sin SonarQube Enterprise
(que cobra por RPG/COBOL) ni servicios en la nube. Cubre RPG IV (fixed/mixed/fully-free),
SQLRPGLE, CL/CLLE, DDS (PF/LF/DSPF/PRTF) y SQL/400.

El analisis combina **dos capas, ambas obligatorias**:

1. **Estatica** — `analyze.py`: clasifica cada fuente, calcula metricas y aplica las
   reglas detectables por patron. Repetible; devuelve exit code segun el quality gate
   (integrable en CI/CD).
2. **Semantica** — vos (Claude): leés el codigo y razonás lo que el regex no puede ver
   (bugs de logica, SQL injection real, duplicacion, cross-reference RPG<->DDS).

> Correr solo el script es un resultado **parcial**. No reportes "PASS" basandote solo en
> `analyze.py`. El entregable final siempre es el reporte consolidado (Paso 5) que fusiona
> ambas capas.

## Flujo de trabajo

### Paso 1 — Alcance
Por defecto `src/`. Si el usuario nombra archivo/carpeta, usá esa ruta.

### Paso 2 — Analisis estatico
```bash
as400-quality src --json quality-reports/scan.json
# si no esta en PATH:
python3 ~/.claude/skills/as400-quality/analyze.py src --json quality-reports/scan.json
# JSON crudo a stdout (para pipes/CI):
as400-quality src --json -
```
El JSON trae, por archivo: lenguaje, formato, metricas, procedimientos e issues `[auto]`
(`rule`, `severity`, `line`, `message`). Exit code 1 si el gate da FAIL.

### Paso 3 — Revision semantica (obligatoria)
**Mapa de campos externos primero:** para cada `dcl-f`, abrí su DDS (`extdesc('LIB/FILE')`)
y anotá los campos del record format. Un nombre en MAYUSCULAS no declarado **es valido** si
existe como campo externo — nunca lo marques como bug sin antes cruzar el DDS.
> Ej.: `issnchk.rpgle` usa `TOTAL`/`CHKCHAR`/`ISSN7`/`ISSNFULL` sin `dcl-s`; cruzando con
> `issnout.pf` se confirma que son campos del record format → no es bug.

Luego recorré cada archivo (priorizá mayor complejidad y los que tienen issues `[auto]`)
aplicando el checklist de su lenguaje (mas abajo). Confirmá cada hallazgo leyendo el codigo;
si dudás, marcalo **"a revisar"**, no como bug. No re-reportes lo que ya vio el scanner.

### Paso 4 — Reglas de contexto (evitar falsos positivos)
- **PUB400**: I/O nativo en vez de `EXEC SQL` es deliberado (no corre el precompilador SQL). No marcar.
- **`GOTO` en CL** hacia etiqueta `ERROR` tras `MONMSG`: idiomatico, no penalizar.
- **Mega-archivos / fuentes de prueba** (concatenados, generados): reportar aparte y no dejar
  que dominen el gate del codigo real.
- **Campos externos de DDS**: nunca marcar como "no declarado" sin cruzar el DDS.

### Paso 5 — Reporte consolidado
Generá `quality-reports/AS400-QUALITY-<fecha>.md` y mostrá el resumen en el chat:
```markdown
# Reporte de Calidad AS/400 — <fecha>
## Resumen ejecutivo
- Quality Gate: PASS | WARN | FAIL
- Archivos: N | Lineas de codigo: N
- Bugs: N · Vulnerabilidades: N · Code Smells: N
- Reliability: A-E · Security: A-E · Maintainability: A-E
## Hallazgos por severidad
(tabla: Severidad | Regla | Archivo:Linea | Descripcion | Como arreglar)
## Metricas por archivo
(tabla: Archivo | Lenguaje/Formato | LOC | Complejidad | Densidad comentarios | Issues)
## Detalle y recomendaciones
(por archivo: explicacion + fix sugerido con snippet)
## Notas de contexto
(que se excluyo del gate y por que)
```
Si el usuario lo pide, ofrecé aplicar los fixes.

---

## Catalogo de reglas

IDs: `AS4-<tipo>-<nombre>`. Severidades: **BLOCKER > CRITICAL > MAJOR > MINOR > INFO**.
`[auto]` = lo detecta el scanner; `[sem]` = lo razonás vos leyendo el codigo.

### RPG IV / ILE / SQLRPGLE
| ID | Sev | Det | Que busca |
|----|-----|-----|-----------|
| AS4-BUG-NOSQLCHECK | MAJOR | auto | `EXEC SQL` ejecutable sin evaluar `SQLCOD`/`SQLSTT` despues. |
| AS4-BUG-TABS | MAJOR | auto | TAB en fuente fixed/mixed: corrompe el alineamiento por columnas. |
| AS4-BUG-NOEOF | CRITICAL | sem | `READ`/`READE` en bucle sin chequear `%EOF`. |
| AS4-BUG-CHAINNOFOUND | MAJOR | sem | `CHAIN`/`SETLL` sin verificar `%FOUND`/`%EQUAL`. |
| AS4-BUG-UNINIT | MAJOR | sem | Variable/acumulador usado sin inicializar. |
| AS4-BUG-DIVZERO | MAJOR | sem | Division sin proteger divisor cero. |
| AS4-BUG-NOMONITOR | MINOR | sem | Conversion/I-O riesgoso sin `MONITOR`/`ON-ERROR`. |
| AS4-VUL-SQLCONCAT | CRITICAL | auto | SQL armado con concatenacion de strings → SQL injection. |
| AS4-VUL-DYNSQL | MAJOR | auto | `EXECUTE IMMEDIATE`/`PREPARE`: usar parameter markers (`?`). |
| AS4-VUL-HARDCREDS | CRITICAL | sem | Usuario/clave/perfil embebido en el fuente. |
| AS4-VUL-CMDINJ | MAJOR | sem | `QCMDEXC`/`system()` con string desde entrada externa. |
| AS4-SMELL-GOTO | MAJOR | auto | `GOTO`/`CABxx` en RPG: usar IF/DOW/DOU/LEAVE/ITER. |
| AS4-SMELL-DEPOPCODE | MINOR | auto | Opcodes legacy (MOVE/MOVEL/MOVEA/Z-ADD/Z-SUB): modernizar con EVAL/BIFs. |
| AS4-SMELL-CASXX | MINOR | auto | `CASxx` deprecado: usar SELECT/WHEN/OTHER. |
| AS4-SMELL-DSPLY | MINOR | auto | `DSPLY`: resto de depuracion. |
| AS4-SMELL-DFTACTGRP | MAJOR | auto | `DFTACTGRP(*YES)` fuerza OPM; preferir `(*NO) ACTGRP(...)`. |
| AS4-SMELL-COMPLEXITY | MAJOR/MINOR | auto | Complejidad ciclomatica alta (umbral 15/30). |
| AS4-SMELL-LONGPROC | MAJOR/MINOR | auto | Procedimiento/subrutina largo (umbral 100/200 LOC). |
| AS4-SMELL-LOWCOMMENT | MINOR | auto | Densidad de comentarios < 8%. |
| AS4-SMELL-DUPCODE | MAJOR | sem | Bloques de logica duplicados. |
| AS4-SMELL-DEEPNEST | MINOR | sem | Anidamiento de IF > 4 niveles. |
| AS4-SMELL-SUBRVSPROC | MINOR | sem | Subrutina que convendria como subprocedimiento tipado. |
| AS4-SMELL-MAGICNUM | MINOR | sem | Numeros/strings magicos en vez de `DCL-C`. |
| AS4-SMELL-NOPROTO | MINOR | sem | `CALL`/`CALLP` sin prototipo (`DCL-PR`). |
| AS4-STYLE-LINELEN | MINOR | auto | Linea > 100 columnas (riesgo de truncado). |
| AS4-INFO-TODO | INFO | auto | Marcador TODO/FIXME/HACK/XXX. |

### CL / CLLE
| ID | Sev | Det | Que busca |
|----|-----|-----|-----------|
| AS4-BUG-NOMONMSG | MAJOR | auto | Programa CL sin ningun `MONMSG`. |
| AS4-BUG-MONMSGTOOWIDE | MINOR | sem | `MONMSG MSGID(CPF0000)` global que oculta errores especificos. |
| AS4-VUL-CLQCMDEXC | MAJOR | sem | `QCMDEXC` con comando armado desde variable. |
| AS4-SMELL-NOSTRUCT | MINOR | sem | Saltos en vez de IF/ELSE/DO/SELECT. |
| AS4-SMELL-CLGOTO | INFO | sem | `GOTO` en CL: aceptable para errores; **no penalizar** salvo abuso. |
| AS4-STYLE-VARLEN | INFO | sem | Variables CL deben empezar con `&` y ≤ 11 chars. |

### DDS (PF/LF/DSPF/PRTF)
| ID | Sev | Det | Que busca |
|----|-----|-----|-----------|
| AS4-SMELL-NOTEXT | MINOR | auto | Sin `TEXT`/`COLHDG`: campos sin documentar. |
| AS4-BUG-TABS | MAJOR | auto | TAB en DDS: corrompe columnas. |
| AS4-SMELL-NOKEY | MINOR | sem | LF/PF por clave sin `K` cuando el uso lo requiere. |
| AS4-SMELL-FIELDREF | MINOR | sem | Campos inline en vez de `REF`/`REFFLD`. |

### SQL embebido
| ID | Sev | Det | Que busca |
|----|-----|-----|-----------|
| AS4-VUL-SQLCONCAT | CRITICAL | auto | Concatenacion en sentencia → SQL injection. |
| AS4-SMELL-SELECTSTAR | MINOR | sem | `SELECT *` en produccion. |
| AS4-BUG-NOCOMMIT | MINOR | sem | Actualizaciones sin estrategia de commit clara. |

---

## Metricas y quality gate

| Metrica | Calculo |
|---------|---------|
| `lines_code` | total − blancos − comentarios (NCLOC). |
| `comment_density_pct` | `lines_comment / lines_code * 100`. Apuntar ≥ 15-20% en logica de negocio. |
| `cyclomatic_complexity` | `1 +` puntos de decision (IF/ELSEIF/WHEN/DOW/DOU/FOR/CASxx/MONITOR/AND/OR/GOTO). |
| `procedures[].code_lines` | LOC entre `DCL-PROC`/`END-PROC` o `BEGSR`/`ENDSR`. |

Deteccion de comentarios: free=`//` ; fixed/mixed=`*` en col 7 ; CL=`/*` ; DDS=`*` en col 7 ; SQL=`--`.

Umbrales (en `analyze.py`): COMPLEXITY 15/30 · LONGPROC 100/200 · LOWCOMMENT 8% · LINELEN 100.

**Quality gate:** PASS (0 issues) · WARN (issues pero sin BLOCKER/CRITICAL) · FAIL (≥1 BLOCKER/CRITICAL).
Exit code 1 solo en FAIL → corta el build en CI/CD.

**Ratings A-E:** A=0 · B=≥1 MINOR · C=≥1 MAJOR · D=≥1 CRITICAL · E=≥1 BLOCKER (por dimension:
Reliability=bugs, Security=vuln, Maintainability=smells).

---

## Checklist semantico (reproducible)

**RPG** — Fiabilidad: `%EOF` tras READ · `%FOUND` tras CHAIN · variables inicializadas ·
division protegida · MONITOR en conversiones/IO · `SQLCOD` tras EXEC SQL.
Seguridad: parameter markers en SQL dinamico · sin credenciales hardcodeadas · QCMDEXC sin input externo.
Mantenibilidad: sin duplicacion · anidamiento ≤ 4 · subproc vs subr · constantes con nombre · prototipos.

**CL** — `MONMSG` presente · no demasiado amplio · QCMDEXC seguro · estructurado · GOTO de error OK.

**DDS** — TEXT/COLHDG · K en archivos por clave · REF a field reference file.

**SQL** — sin `SELECT *` · estrategia de commit · sin concatenacion de valores.

Formato de cada hallazgo: `[SEV] REGLA archivo:linea` + **Que** / **Por que** / **Fix** (snippet si ayuda).

## Integracion con otras skills
- **as400-developer / as400-compiler / as400-tester** (repo as400-discovery): reescribir,
  gatear antes de compilar, complementar con tests funcionales.
- **git-flow**: para versionar los cambios de calidad con Conventional Commits.

## Limitaciones honestas
- Complejidad y densidad son aproximaciones por patron (señal, no auditoria exacta).
- Las reglas `[sem]` dependen de tu lectura: sé concreto y no inventes hallazgos.
- Es analisis estatico; para validar comportamiento usá tests (as400-tester).
