# Diccionario de esquemas MAGyP — v1

**Contrato DASHBOARD actual: mcba-dashboard-v3.** DAILY/DETAIL/LATEST añaden
`product_raw`, `variety_raw`, `origin_raw`, `package_raw`, `kg_raw`,
`raw_sha256`, `capture_id`, `capture_timestamp`, `schema_version`,
`parser_version`, `price_unit_raw`, `volume`, `data_source`,
`source_status` y `last_update`. No cambia el grano canónico ni el parser XLSX.
En esta salida currency=ARS, price_unit=kg y volume=null; ARS/kg legado se conserva
en price_unit_raw sin conversión numérica. SUMMARY registra versión, conteos y estado
mensual no operativo; UPDATE_STATUS informa fallo de actualización sin alterar precios.
El frontend usa detail, valida hashes del marcador y separa fuentes al graficar períodos mixtos.

**Fase 3:** contrato v2 conservado. Nuevos RAW usan currency=ARS, price_unit=kg y
currency_evidence=documented. Manifests/filas legadas preservan su evidencia y
unidad ARS/kg; equivalencia de etiqueta explícita en diagnóstico, sin conversión
numérica. `MCBA_MAGYP_DETAIL.csv` contiene exclusivamente observation_level=detail.
Kg unknown exige volume/volume_unit null y se valida antes de publicar. Consultar
`MCBA_PRODUCTION_POLICY.md` para agregados/matching A/B/C y calendario desconocido.

**Fase 2: contrato canónico vigente v2.** La tabla original se conserva como referencia;
los campos siguientes se añaden sin eliminar dimensiones ni modificar RAW legado.

| name | layer | type | description | source mapping | nullable | economic meaning | warnings |
|---|---|---|---|---|---|---|---|
| observation_level | NORMALIZED/ANALYTICAL/DASHBOARD | enum detail/species_summary/unknown | Nivel de observación | Variedad Prom.Esp.; especie presente | no | Evita sumar resumen y detalle | Fórmula del resumen no documentada |
| kg_semantics_status | NORMALIZED/ANALYTICAL/DASHBOARD | enum documented/inferred/unknown | Evidencia de Kg | unknown por defecto | no | No volumen identificado | volume sigue null incluso Kg=0 |
| currency_evidence | NORMALIZED/ANALYTICAL/DASHBOARD | enum documented/contextual/unknown | Evidencia de denominación | Manifest y encabezados oficiales | no | Pesos locales → ARS explícito | ARS no viene como código ISO del XLSX |
| product_raw | NORMALIZED/ANALYTICAL | string | Producto original | Especie | sí | Producto publicado | No corregir RAW |
| variety_raw | NORMALIZED/ANALYTICAL | string | Variedad original | Variedad | sí | Variedad publicada | ¥ se preserva si regla no validada |
| origin_raw | NORMALIZED/ANALYTICAL | string | Origen original | Procedencia | sí | Geografía publicada | No identificar provincia/localidad sin evidencia |
| origin_normalized | NORMALIZED/ANALYTICAL/DASHBOARD | string | Origen textual + alias validated | Procedencia/diccionario | sí | Etiqueta controlada | observed/manual_review no se aplica |
| package_raw | NORMALIZED/ANALYTICAL | string | Envase original | Envase | sí | Presentación publicada | Sin inferir Kg del bulto |
| coverage_days | DASHBOARD MONTHLY | integer | Días distintos de esa combinación observados | ANALYTICAL | no | Cobertura muestral | No número de registros |
| expected_days | DASHBOARD MONTHLY | integer | Días de publicación esperados | Calendario oficial futuro | sí | Denominador cobertura | null si no documentado |
| coverage_ratio | DASHBOARD MONTHLY | number | coverage_days/expected_days | Calendario oficial futuro | sí | Completitud | null con denominador desconocido |
| aggregation_status | DASHBOARD MONTHLY | enum | partial_period | Estado de piloto | no | Agregado parcial | No equivale a mensual oficial |
| expected_days_basis | DASHBOARD MONTHLY | string | Motivo del denominador desconocido | official_publication_calendar_unverified | no | Calendario | No supone días hábiles oficiales |
| acquisition_classification | RAW manifest | enum | HTTP_AUTONOMOUS/BROWSER_AUTOMATION_REQUIRED/MANUAL_ONLY | Adaptador | sí | Método de adquisición | None legado; no confundir automatización con HTTP puro |
| request_count | RAW manifest | integer | Requests oficiales enviados en ejecución | Adaptador | sí | Control de carga | Incluye recursos UI; descargas validadas por límite |

Manifest añade currency_evidence además de acquisition_classification/request_count.
Contrato market_price_observation-v2, parser mcba-xlsx-2.0.0; RAW v1 se admite sin alterar
versiones originales. Matching registra matching_rule/candidate_references y mantiene
ambiguos sin asignación. Regla precio tolerancia 0.011; no ranking por cercanía.

## market_price_observation (MCBA)

Cada campo NORMALIZED se conserva en ANALYTICAL. Null significa no informado o no parseable; nunca cero implícito.
No se incluyen credenciales, estado GeneXus ni campos HTML. La tabla documenta capa, tipo, mapeo, nulabilidad y semántica.

| name | layer | type | description | source mapping | nullable | economic meaning | warnings |
|---|---|---|---|---|---|---|---|
| observation_id | NORMALIZED → ANALYTICAL | string | hash técnico reproducible de fuente/fila/ocurrencia | Derivado | no | Identidad de observación, no oficial | Incluye valores de precio; no contrato |
| source | NORMALIZED → ANALYTICAL | string | mcba | Registro | no | Proveedor identificable | No mezclar series |
| source_family | NORMALIZED → ANALYTICAL | string | market_price_observation | Registro | no | Cotización mayorista | No equivale a evento SIO |
| market | NORMALIZED → ANALYTICAL | string | Mercado Central de Buenos Aires | Contexto oficial | no | Plaza | No viene como columna XLSX |
| market_normalized | NORMALIZED → ANALYTICAL | string | MCBA | Contexto oficial | no | Plaza canónica | Regla contextual fija para este adaptador |
| observation_date | NORMALIZED → ANALYTICAL | date ISO | Fecha publicada | Fecha | sí | Día cotizado | Inválida null + flag; no fecha de captura |
| observation_datetime | NORMALIZED → ANALYTICAL | datetime ISO | Instante económico si informado | No informado | sí | Hora de cotización | No inventar medianoche UTC |
| period | NORMALIZED → ANALYTICAL | string YYYY-MM | Mes de observación | observation_date | sí | Período calendario | No convierte diario a mensual |
| frequency | NORMALIZED → ANALYTICAL | string | daily | Export diario | no | Frecuencia de observación | Continuidad no probada |
| date_precision | NORMALIZED → ANALYTICAL | string | day | Fecha | no | Resolución temporal | No confundir ancla mensual Excel |
| product | NORMALIZED → ANALYTICAL | string | Etiqueta original de especie | Especie | sí | Producto | No corregir abreviaturas |
| product_normalized | NORMALIZED → ANALYTICAL | string | NFKC/mayúsculas/espacios | Especie | sí | Etiqueta canónica textual | No diccionario botánico |
| variety | NORMALIZED → ANALYTICAL | string | Etiqueta original de variedad | Variedad | sí | Variedad o resumen | Prom.Esp. no es una variedad económica |
| variety_normalized | NORMALIZED → ANALYTICAL | string | NFKC/mayúsculas/espacios | Variedad | sí | Variedad textual | Sin corregir ¥ a ñ |
| origin | NORMALIZED → ANALYTICAL | string | Procedencia original | Procedencia | sí | Origen informado | No identificar provincia por suposición |
| origin_province | NORMALIZED → ANALYTICAL | string | Provincia validada futura | No derivado | sí | Geografía | Requiere diccionario |
| origin_locality | NORMALIZED → ANALYTICAL | string | Localidad validada futura | No derivado | sí | Geografía | Procedencia puede ser país/provincia/localidad |
| package | NORMALIZED → ANALYTICAL | string | Envase original | Envase | sí | Presentación | No kg de bulto implícitos |
| package_normalized | NORMALIZED → ANALYTICAL | string | NFKC/mayúsculas/espacios | Envase | sí | Presentación textual | No cambia códigos |
| quality | NORMALIZED → ANALYTICAL | string | Calidad original | Calidad | sí | Grado comercial | No colapsar calidades |
| quality_detail | NORMALIZED → ANALYTICAL | string | Detalle adicional reservado | No informado adicional | sí | Calidad adicional | Tamaño y Grado tienen columnas propias |
| type | NORMALIZED → ANALYTICAL | string | Tipo original | Tipo | sí | Frutas/Hortalizas | No tipo operación |
| size | NORMALIZED → ANALYTICAL | string | Tamaño original | Tamaño | sí | Calibre/tamaño | Puede ser etiqueta o número |
| grade | NORMALIZED → ANALYTICAL | string | Grado original | Grado | sí | Atributo adicional | Puede describir producción/color/condición; semántica pendiente |
| currency | NORMALIZED → ANALYTICAL | string ISO | ARS por contexto oficial | Manifest/encabezado público | sí | Moneda | No columna explícita del XLSX |
| price_unit | NORMALIZED → ANALYTICAL | string | ARS/kg por encabezado promedio x Kg | Manifest/encabezado | sí | Denominador precio | No convertir Kg ni envase |
| price_min | NORMALIZED → ANALYTICAL | number | Mínimo si informado | No informado | sí | Cotización mínima | No derivar del promedio |
| price_max | NORMALIZED → ANALYTICAL | number | Máximo si informado | No informado | sí | Cotización máxima | No derivar del promedio |
| price_average | NORMALIZED → ANALYTICAL | number | Promedio publicado parseado | Promedio x Kg. | sí | Cotización promedio | Ponderación no documentada |
| price_modal | NORMALIZED → ANALYTICAL | number | Modal si informado | No informado | sí | Cotización modal | No derivar del promedio |
| price | NORMALIZED → ANALYTICAL | number | Alias de precio promedio para este adaptador | Promedio x Kg. | sí | Cotización | Nunca mezclar con min/modal ni SIO |
| volume | NORMALIZED → ANALYTICAL | number | Volumen comercial validado | No informado validado | sí | Cantidad negociada | Kg no se mapea a volumen |
| volume_unit | NORMALIZED → ANALYTICAL | string | Unidad volumen | No informado | sí | Denominador cantidad | Kg ambiguo |
| source_record_id | NORMALIZED → ANALYTICAL | string | ID oficial si publicado | No exportado | sí | Identidad proveedor | Hash técnico no sustituye ID oficial |
| capture_id | NORMALIZED → ANALYTICAL | string | ID de versión RAW | Manifest | no | Versión adquirida | UTC + UUID; no ID económico |
| capture_timestamp | NORMALIZED → ANALYTICAL | datetime UTC | Ingreso a RAW | Manifest.captured_at_utc | no | Actualización | Puede ser posterior a descarga del navegador |
| raw_sha256 | NORMALIZED → ANALYTICAL | string SHA256 | Hash de bytes originales | Manifest.sha256 | no | Trazabilidad | No hash de fila |
| source_url | NORMALIZED → ANALYTICAL | URL | Origen oficial estable | Manifest.endpoint | no | Trazabilidad | Sin sesión/tokens |
| schema_version | NORMALIZED → ANALYTICAL | string | market_price_observation-v1 | Constante parser | no | Contrato | Cambio exige revisión |
| parser_version | NORMALIZED → ANALYTICAL | string | mcba-xlsx-1.0.0 | Constante parser | no | Transformación | Reprocesamiento explícito |
| parse_warnings | NORMALIZED → ANALYTICAL | array string | Advertencias interpretativas | Parser | no | Límites semánticos | No eliminar silenciosamente |
| quality_flags | NORMALIZED → ANALYTICAL | array string | Controles de calidad | Parser | no | Usabilidad | Extremo diagnóstico no descarta |
| original_dimensions | NORMALIZED → ANALYTICAL | object | Once valores fuente completos | XLSX | no | Grano original | Fechas serializadas ISO; bytes exactos en RAW |
| price_raw | NORMALIZED → ANALYTICAL | number/string | Valor original precio | Promedio x Kg. | sí | Auditoría precio | Preserva precio inválido |
| kg_raw | NORMALIZED → ANALYTICAL | number/string | Valor original Kg | Kg | sí | Dato ambiguo | No bulto ni volumen confirmado |
| source_row_number | NORMALIZED → ANALYTICAL | integer | Fila física workbook | XLSX | no | Auditoría | No ID oficial |
| record_kind | NORMALIZED → ANALYTICAL | enum | detail/species_summary | Variedad=Prom.Esp. | no | Nivel de observación | Nunca mezclar detalle y resumen |
| currency_basis | NORMALIZED → ANALYTICAL | enum | official_context/not_reported | Manifest | no | Procedencia moneda | Contextual explícita |
| unit_basis | NORMALIZED → ANALYTICAL | enum | export_header_and_currency_context/not_reported | Manifest | no | Procedencia unidad | No asumir en otras fuentes |
| dimension_key | NORMALIZED → ANALYTICAL | string SHA256 | Hash dimensiones económicas exactas | Derivado | no | Candidato a serie | No asume unicidad |
| record_fingerprint | NORMALIZED → ANALYTICAL | string SHA256 | Hash valores originales completos | Derivado | no | Igualdad observación | No hash RAW ni ID oficial |

## Campos exclusivos de ANALYTICAL

| name | layer | type | description | source mapping | nullable | economic meaning | warnings |
|---|---|---|---|---|---|---|---|
| valid_for_price_series | ANALYTICAL | boolean | Usable para serie de precios | flags bloqueantes | no | Precio interpretable | No prueba representatividad, comparabilidad mensual ni ausencia de extremos |
| reason | ANALYTICAL | string | valid o flags bloqueantes separados por ; | quality_flags | no | Motivo de clasificación | Se conserva la observación excluida |

## Manifest RAW

| name | layer | type | description | source mapping | nullable | economic meaning | warnings |
|---|---|---|---|---|---|---|---|
| source | RAW manifest | string | ID fuente | Registro | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| source_family | RAW manifest | enum | Familia económica | Registro | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| endpoint | RAW manifest | URL | Origen estable | Consulta oficial | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| request_method | RAW manifest | string | Método transporte observado | HTTP/null import | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| public_parameters | RAW manifest | object | date_from/date_to ISO | Ventana solicitada y validada | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| captured_at_utc | RAW manifest | datetime UTC | Ingreso a RAW | Reloj UTC | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| http_status | RAW manifest | integer | Status HTTP | Respuesta HTTP/null import | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| content_type | RAW manifest | string | Header informado | HTTP/null import | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| encoding | RAW manifest | string | Encoding declarado | Binario XLSX=null | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| byte_size | RAW manifest | integer | Tamaño payload | len(bytes) | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| sha256 | RAW manifest | string | Integridad exacta | SHA-256 bytes | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| schema_version | RAW manifest | string | Contrato | Parser | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| parser_version | RAW manifest | string | Versión parser | Parser | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| record_count | RAW manifest | integer | Filas datos | Parser XLSX | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| validation_status | RAW manifest | enum | validated | Validaciones | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| capture_id | RAW manifest | string | Identificador captura | UTC + UUID | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| acquisition_mode | RAW manifest | enum | browser_export_import/http_export | Capturador | no | Procedencia/validación | No persistir sesiones; null transporte no observado |
| currency | RAW manifest | string | Moneda contextual | Encabezado oficial | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| price_unit | RAW manifest | string | Unidad contextual | Encabezado export | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| context_evidence_url | RAW manifest | URL | Evidencia moneda/unidad | Referencia pública | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |
| response_url | RAW manifest | URL | URL pública de descarga si observada | HTTP export | sí | Procedencia/validación | No persistir sesiones; null transporte no observado |

## DASHBOARD

DAILY: dimensiones completas + date/price/observation_id/source_url/updated_at/quality_flags; sólo válidos.
LATEST: mismo esquema, último día por todas las dimensiones (Prom.Esp. separado).
MONTHLY: dimensiones completas + period/price_median/observation_count/observed_days/coverage_status/method/source_url/updated_at.
SUMMARY: source/rows_analytical/valid_rows/date_min/date_max/observed_days/detail_rows/summary_rows/quality_flags/source_url/updated_at.

| name | layer | type | description | source mapping | nullable | economic meaning | warnings |
|---|---|---|---|---|---|---|---|
| date | DASHBOARD | date ISO | Día cotización | observation_date | no | Cotización diaria | Una muestra no acredita un histórico continuo |
| updated_at | DASHBOARD | datetime UTC | Última captura usada | capture_timestamp | no | Actualización | Una muestra no acredita un histórico continuo |
| price_median | DASHBOARD | number | Mediana observaciones del período | Precios diarios válidos | no | Referencia parcial, no oficial mensual | Una muestra no acredita un histórico continuo |
| observation_count | DASHBOARD | integer | Número observaciones | Conteo | no | Soporte muestral | Una muestra no acredita un histórico continuo |
| observed_days | DASHBOARD | integer | Días distintos presentes | Fechas analíticas | no | Cobertura parcial | Una muestra no acredita un histórico continuo |
| coverage_status | DASHBOARD | string | partial_unverified | Constante | no | Continuidad no validada | Una muestra no acredita un histórico continuo |
| method | DASHBOARD | string | median_observed_daily_prices | Constante | no | Método de agregación | Una muestra no acredita un histórico continuo |
| rows_analytical | DASHBOARD | integer | Filas totales | ANALYTICAL | no | Cobertura | Una muestra no acredita un histórico continuo |
| valid_rows | DASHBOARD | integer | Filas usables | valid_for_price_series | no | Cobertura utilizable | Una muestra no acredita un histórico continuo |
| date_min | DASHBOARD | date ISO | Primera fecha válida | ANALYTICAL | no | Extremo observado | Una muestra no acredita un histórico continuo |
| date_max | DASHBOARD | date ISO | Última fecha válida | ANALYTICAL | no | Extremo observado | Una muestra no acredita un histórico continuo |
| detail_rows | DASHBOARD | integer | Conteo detail | record_kind | no | Grano detallado | Una muestra no acredita un histórico continuo |
| summary_rows | DASHBOARD | integer | Conteo species_summary | record_kind | no | Resúmenes oficiales | Una muestra no acredita un histórico continuo |

quality_flags en SUMMARY es objeto flag→conteo; en DAILY/LATEST es array JSON en una celda CSV.
El resto de campos publicados utiliza el mismo mapeo/semántica del modelo canónico.

## Familias reservadas (contratos conceptuales, no implementados)

| Modelo | Grano requerido | Campos a validar | Estado |
|---|---|---|---|
| commodity_reference_price | fuente/plaza/tipo precio/fecha/posición/vencimiento o embarque | proveedor, posición raw, moneda, unidad, metodología, circular, intervalo, tipo ajuste, trazabilidad | Sin parser común implementado; FOB previo preservado |
| transaction_event | evento/operación oficial/versionado temporal | ID oficial evento/contrato, fecha operación/publicación, Compraventa/Canje, estado, rectificación/anulación, volumen/unidad, moneda/tipo precio, plaza y última instancia | SIO avanzado pausado |
| livestock_transaction_event | evento oficial por definición futura | ID oficial, especie/categoría, mercado, cantidad/peso/unidad, precio/tipo/moneda, estado y versión | Reservado |

No se crean campos poblados para estas familias antes de validar su fuente. SourceFetcher/Normalizer son Protocol; RawManifest/ValidationResult/PublishResult son dataclasses comunes.

## Flags y reglas

price_missing (null/no parseable), price_zero, price_negative, currency_missing, unit_missing, product_missing, date_missing, origin_missing, duplicate_candidate (dimension_key repetida dentro de captura), extreme_value_candidate (factor 10 frente a mediana de grupo ≥5).
origin_missing y extremo no bloquean automáticamente la serie; los demás bloquean. Advertencias: kg_semantics_unverified, official_record_id_not_exported, currency_from_official_context, currency_context_transfer_requires_confirmation (Hortalizas), date_parse_failed, price_parse_failed, suspicious_source_character_preserved.

Cada regla es específica del adaptador MCBA; no se aplica como conversión universal a referencias FOB/FAS ni a eventos SIO.
