# MCBA: vista mensual desde Mercado Central

## Fuente y semántica

Los enlaces se descubren por HTTP desde la
[página oficial de precios mayoristas](https://www.mercadocentral.gob.ar/informaci%C3%B3n/precios-mayoristas).
No se construyen URLs por suposición. Al 20/10/2026 hay 20 ZIP publicados para
enero–octubre de 2026: frutas y hortalizas.

Los ZIP contienen XLS BIFF2 **diarios**, con 14 columnas:
`ESP VAR PROC ENV KG CAL TAM GRADO MA<fecha> MO<fecha> MI<fecha> MAPK MOPK MIPK`.
La [leyenda oficial](https://mercadocentral.gob.ar/img/Precios-referentes.jpg)
define máximo, modal y mínimo, y sus valores por kilo. Se usa **MOPK**, modal
publicado por kilo. KG es peso del envase; no es volumen transado.

Los XLS no incluyen una columna monetaria. ARS se asigna explícitamente por
contexto documentado MCBA en pesos por kilo, con referencia a
<https://ssma.magyp.gob.ar/frutas.preciospromediof.aspx> y regla trazable en
`currency_basis`; no se efectúa conversión. `currency_raw` permanece vacío en
NORMALIZED. Las etiquetas y celdas originales se conservan.

## Método mensual explícito

Cada serie conserva producto, variedad, origen, envase, peso de envase,
calidad, tamaño, grado, moneda y unidad. No se mezclan esas dimensiones.
Se eliminan duplicados exactos únicamente para agregar. Si un día tiene varias
cotizaciones distintas para la misma serie, se toma su media aritmética diaria;
luego se toma la media aritmética de los días observados, sin ponderar por volumen.
`multiple_quotes_days` registra esos casos. No se interpolan faltantes.

La frecuencia es **mensual derivada de observaciones diarias oficiales de Mercado
Central**, no mensual oficial MAGyP. La fecha del período identifica el mes; la
última observación real está en `last_observation_date`. Octubre es parcial.
Los resúmenes `Prom.Esp.` se conservan en NORMALIZED y no se agregan como detalle.

## Capas y responsabilidades

- `scripts/mercado_central/update_mcba_monthly.py`: descubrir, capturar, validar,
  normalizar y publicar la vista mensual.
- `scripts/mercado_central/validate_mcba_monthly.py`: cobertura, anomalías y
  comparación con fuentes existentes.
- `config/mercado_central_codes.json`: equivalencias documentadas de códigos.
- `data/mercado_central/`: datos de esta fuente; su README distingue qué publicar.
- `mcba-monthly.js`: verifica hash/esquema y adapta el CSV a la interfaz existente.
- `tests/mercado_central/` y `tests/magyp_frontend/central-monthly.test.cjs`:
  contratos y regresiones de la integración.

RAW conserva URL, nombre original, timestamp, SHA-256, tamaño, status HTTP,
contenido permitido y versión del parser. Los ZIP y JSONL completos quedan fuera
de Git. El CSV mensual conserva linaje hasta los ZIP y miembros utilizados.

Sólo se interpretan XLS diarios RF/RH en la raíz del ZIP. Archivos adjuntos
ajenos a precios no se extraen ni ejecutan; se informa únicamente su cantidad.
Hay planillas del 04/05 dentro de ZIP rotulados abril: se conserva la fecha real
validada por nombre del XLS y encabezado, sin forzar el mes del ZIP.

## Ejecución

Desde la raíz del repositorio:

```text
python -m pip install -r scripts/mercado_central/requirements.txt
python scripts/mercado_central/update_mcba_monthly.py --year 2026 --as-of 2026-10-20 --allow-web
python scripts/mercado_central/validate_mcba_monthly.py
python scripts/magyp/build_price_freshness.py
```

Para reproducir desde RAW local sin red, sustituir `--allow-web` por `--replay`.
Si no cambia el contenido de los ZIP ni la versión del parser, el resultado es
`NO_OP_ALREADY_CURRENT`. Toda modificación futura de las reglas de normalización
requiere incrementar la versión del parser para reconstruir la vista.

Validación offline:

```text
python -m unittest discover -s tests/mercado_central -v
python -m unittest discover -s tests/magyp_common -v
python -m unittest discover -s tests/magyp_mcba -v
node --test tests/magyp_frontend/*.test.cjs
git diff --check
```

## Dashboard, fallback y automatización

MCBA diario sigue usando MAGyP. MCBA mensual usa esta vista para los meses y rubros
cubiertos; conserva legacy para los no cubiertos. No se rellenan silenciosamente
productos ausentes dentro de un mes/rubro cubierto. Corrientes permanece intacto.
La interfaz identifica el método derivado y muestra frescura de esta fuente.

El workflow `update-mcba-monthly-central.yml` prepara ejecución manual y una
revisión por día hábil, a las 12:15 Argentina. Usa HTTP en Linux, sin browser.
Valida antes de publicar, permite sólo salidas dashboard/metadata/reporte y
dispara `deploy.yml` explícitamente después de un push exitoso. Comparte la
serialización de escritores existente. No ha sido ejecutado remotamente en esta
rama sin publicar.

Sin enlaces nuevos: `NO_PUBLICATION`; mismos hashes: `NO_OP_ALREADY_CURRENT`.
Fallo de red: `SOURCE_UNAVAILABLE`. Esquema/contenido inválido: `PIPELINE_ERROR`.
Se conserva siempre el último CSV y checksum válidos; nunca se publica un vacío.

## Verificación de la captura inicial

70.377 filas diarias normalizadas, 54.353 de detalle con precio positivo y
3.723 series mensuales; último dato 19/10/2026. Enero, junio y octubre se revisaron
para ambos rubros. El reporte JSON contiene el catálogo de ZIP, días, filas y
anomalías por período.

El mensual legacy termina en diciembre de 2025: no hay período común para una
comparación mensual de precios. Se conserva como histórico/fallback.
En el solapamiento diario con MAGyP hay 1.027 pares no ambiguos comparables;
todos difieren menos del 1%, con ratio mediano 1.0. Siete claves ambiguas se
excluyen de esa comparación. Para cotejar etiquetas sólo se ignoran acentos,
mayúsculas y punto final; no se equiparan definiciones económicas distintas.
La coincidencia no convierte el modal MOPK en el “Promedio x Kg.” de MAGyP.

Evidencia reproducible: `data/mercado_central/reports/MCBA_MONTHLY_VALIDATION.json`.
