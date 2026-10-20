# MCBA: cobertura histórica y decisión de cutover

Fecha de verificación: 20/10/2026. Rama de trabajo: `codex/mcba-official-history`.
Auditoría sin cambio de cobertura productiva ni eliminación de archivos manuales.

## Resultado verificable

**No corresponde retirar MCBA manual del runtime todavía.** La ampliación ARS
anterior a 2026 queda `BLOCKED_BY_SOURCE`, no como error del pipeline. Tampoco
se habilita un cutover anual ni diario a partir de esta auditoría mensual.

El año más antiguo de un archivo oficial descargado es **2017**, en un catálogo
histórico de MAGyP sobre MCBA. Su CSV es mensual y está expresado en **USD/kg**:
516 filas de enero–diciembre de 2017 y 312 de enero–agosto de 2018. Incluye 61
precios vacíos y uno cero, conservados y marcados sin inventar valores. Tiene
producto, variedad y origen, sin el detalle de envase/calidad/tamaño/grado del
XLS diario. No documenta equivalencia con el modal diario en ARS ni un método de
conversión aplicable a esta migración. Se conserva RAW y NORMALIZED para auditoría;
**no se mezcla con el CSV ARS ni se publica como sustituto**.

La cobertura detallada compatible comprobada del Mercado Central comienza en
**2026**: 20 ZIP con XLS diarios de enero a octubre; última observación 19/10.
70.377 filas diarias normalizadas, 54.353 con detalle y precio positivo, y 3.723
series mensuales derivadas. Los ZIP son mensuales, pero las observaciones son
diarias: no se las llama promedio mensual oficial.

| Año | Cobertura oficial verificable | Filas | Uso productivo ARS |
|---|---|---:|---|
| 2017 | Enero–diciembre; CSV histórico USD | 516 | Excluido: moneda y método distintos |
| 2018 | Enero–agosto; CSV histórico USD | 312 | Excluido: moneda y método distintos |
| 2019–2023 | Sin enlaces equivalentes encontrados en el alcance revisado | — | Sin backfill acreditado |
| 2024 | Informes institucionales; sin XLS equivalente encontrado | — | 4.167 filas mensuales del archivo histórico |
| 2025 | Informes institucionales; sin XLS equivalente encontrado | — | 4.541 filas mensuales del archivo histórico |
| 2026 | Enero–octubre; ZIP con XLS diarios | 70.377 | Vista mensual derivada; octubre parcial |

La ausencia de un enlace encontrado **no prueba que el organismo no conserve
otros históricos**. No se afirma un año mínimo universal del sistema MCBA.

## Evidencia de descubrimiento

- [Índice oficial de precios mayoristas](https://www.mercadocentral.gob.ar/informaci%C3%B3n/precios-mayoristas):
  HTTP 200, 20 enlaces ZIP de 2026.
- [Sitemap oficial](https://www.mercadocentral.gob.ar/sitemap.xml): ambos índices
  enlazados se descargaron; contienen 4.993 y 223 URLs, analizadas localmente.
  No se descargaron todas esas páginas. Se revisaron muestras históricas
  pertinentes, además del índice vigente.
- Directorio padre confirmado de los ZIP: HTTP 403; no se reintentó, se evadió ni
  se enumeraron nombres de archivos por año.
- [Informe institucional de abril de 2024](https://mercadocentral.gob.ar/publicaciones/informe-monitoreo-federal-abril-2024):
  enlaza un PDF, sin ZIP/XLS equivalente. Un informe con otra definición del precio
  no reemplaza la serie detallada.
- [Relevamiento del 11/02/2022](https://mercadocentral.gob.ar/news/relevamiento-de-precios-mayoristas-del-110222):
  imagen asociada al Compromiso Social de Abastecimiento; sin planillas históricas
  equivalentes. No se interpreta como precio modal diario del mercado.
- [Catálogo histórico MAGyP MCBA](https://datos.magyp.gob.ar/dataset/precios-mayoristas-frutas-hortalizas/archivo/6dce1e87-7988-4eaf-b0e1-b3abbb3964da):
  CSV enlazado obtenido por HTTP 200; 828 filas en USD/kg. No se adivinó su URL.

El recolector reproducible realizó nueve requests secuenciales, sin retries,
separados por diez segundos. Guarda URL, procedencia del enlace, HTTP, timestamp,
SHA-256, tamaño y enlaces extraídos; no guarda HTML con formularios, cookies ni
sesiones. No hay límite artificial 2024–2026 en el inventario.

## Comparación con la carga manual

`MCBA_HISTORY_INVENTORY.json` incluye por año cobertura, filas, productos,
variedades, procedencias, unidades y comparación de precios. Su CSV resume la
cobertura, schema y calidad por año, incluidos años sin enlaces encontrados.

En 2026 hay 61.744 filas manuales de enero–agosto. La comparación diaria usa
fecha, rubro, producto, variedad, procedencia y envase, con códigos de envase de
la leyenda oficial y etiquetas sin acentos/punto final. No se inventan calidad,
tamaño ni grado ausentes en columnas estructuradas de la carga manual diaria.
Son 16.050 claves compartidas: 13.211 pares no ambiguos dentro del 1% y ratio
mediano 1.0; 2.839 claves ambiguas se excluyen. Otras 28.969 claves manuales no
empatan con esas reglas: pueden incluir diferencias de etiquetas o cobertura,
por lo que no se declaran reemplazadas a nivel diario.

En la **vista mensual ya aprobada**, enero–agosto de 2026 utiliza la agregación
del Mercado Central, excluyendo las filas manuales de los meses/rubros cubiertos
antes de filtros y cálculos. Septiembre y octubre amplían cobertura. No se
eliminan datos originales ni se modifica la prioridad del circuito diario MAGyP.

Para 2024–2025, los 24 meses/8.708 registros mensuales no tienen reemplazo
equivalente validado. Sigue siendo necesario **100% de ese histórico mensual**.
Como medida distinta, esas filas son **12,36% de las 70.452 filas MCBA manuales
de entrada** después del enrutamiento mensual. Ese porcentaje no autoriza a
retirar el archivo compartido del diario/anual ni del runtime completo.

No se calculan precios mensuales 2024–2025 desde datos diarios de otro año,
ni se rellenan huecos en ARS con el CSV USD. El dato vacío se conserva como vacío.

## Dashboard y próximos requisitos de cutover

Fuente institucional, cobertura y último período visibles. Se eliminan las
etiquetas técnicas legacy/fallback de los mensajes MCBA. La selección de años
históricos muestra fuente estática; las selecciones cubiertas conservan el estado
real de la publicación. La alerta no se deduce por edad del dato.

Con una selección íntegramente Mercado Central, la evolución no crea una rama
técnica adicional por fuente. Si conviven publicaciones con métodos distintos,
siguen identificables. No se alteran los cálculos económicos ni otros módulos.

Para habilitar un retiro futuro se necesitan enlaces oficiales reproducibles a
publicaciones equivalentes que cubran 2024–2025, comparación a igual grano,
unidades/moneda compatibles y regresiones aprobadas. Rige
[DATA_SOURCE_POLICY.md](DATA_SOURCE_POLICY.md).

## Reproducción

```text
python -m pip install -r scripts/mercado_central/requirements.txt
python scripts/mercado_central/discover_history.py --allow-web
python scripts/mercado_central/audit_history.py
python -m unittest discover -s tests/mercado_central -v
node --test tests/magyp_frontend/*.test.cjs
```

La auditoría offline requiere los RAW y ANALYTICAL locales de la captura MCBA
existente y la captura de descubrimiento. Verifica hashes de los ZIP y del CSV
candidato. El recolector nunca inicia descargas masivas ni altera outputs de
precios. Si aparecen otros enlaces, deben validarse con el pipeline de su formato
y pasar los controles de cutover antes de publicarse.
