# Auditoría de funcionamiento de Commodities

Fecha de auditoría: 2026-10-02T09:46:54-03:00. Rama: codex/auditar-funcionamiento-commodities.

## Objetivo

Comprobar los datos del dashboard, la separación entre SIO Granos y el histórico local mensual, las reglas de filtros y series, el workflow de actualización y los CSV servidos por localhost y GitHub Pages.

## Fuentes revisadas

Se leyeron todos los CSV SIO indicados y todos los CSV del directorio dashboard local mensual. El script también revisó app.js y update-sio-commodities.yml. Los recursos publicados se comparan por campos y filas para no confundir diferencias de BOM o fin de línea con cambios de contenido.
La validación cubre los snapshots y CSV dashboard-ready versionados; no reconstruye la transformación desde archivos fuente originales.

| Fuente | Archivo | Bytes | Filas | Columnas | Fechas | Precios cero | Nulos críticos |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| SIO Granos | COMMODITIES_SIO_DASHBOARD_DIARIO.csv | 27651 | 120 | 18 | 2026-09-09 a 2026-10-01 | 0 filas / 0 celdas | 0 |
| SIO Granos | COMMODITIES_SIO_DASHBOARD_MENSUAL.csv | 2691 | 18 | 18 | 2026-09 a 2026-10 | 0 filas / 0 celdas | 0 |
| SIO Granos | COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv | 1179 | 13 | 12 | 2026-09-25 a 2026-10-01 | 0 filas / 0 celdas | 0 |
| SIO Granos | COMMODITIES_SIO_DASHBOARD_RESUMEN.csv | 768 | 1 | 16 | 2026-09-09 a 2026-10-01 | 0 filas / 0 celdas | 0 |
| SIO Granos | COMMODITIES_SIO_DASHBOARD_SEMAFORO.csv | 1240 | 18 | 10 | 2026-09 a 2026-10 | 0 filas / 0 celdas | 0 |
| SIO Granos | COMMODITIES_SIO_HISTORICO_SNAPSHOTS_LIVIANO.csv | 141550 | 323 | 23 | 2026-09-09 a 2026-10-01 | 0 filas / 0 celdas | 0 |
| Histórico local mensual | COMMODITIES_LOCAL_MENSUAL_DASHBOARD_MENSUAL.csv | 150030 | 668 | 17 | 2020-01 a 2026-08 | 0 filas / 0 celdas | 0 |
| Histórico local mensual | COMMODITIES_LOCAL_MENSUAL_DASHBOARD_RESUMEN.csv | 729 | 1 | 14 | 2020-01-01 a 2026-08-01 | 0 filas / 0 celdas | 0 |
| Histórico local mensual | COMMODITIES_LOCAL_MENSUAL_DASHBOARD_SEMAFORO.csv | 156726 | 668 | 18 | 2020-01 a 2026-08 | 0 filas / 0 celdas | 0 |
| Histórico local mensual | COMMODITIES_LOCAL_MENSUAL_DASHBOARD_ULTIMOS.csv | 3789 | 17 | 14 | 2024-05 a 2026-08 | 0 filas / 0 celdas | 0 |

## Estado SIO Granos

- 323 filas, 323 IDs únicos, 0 filas con ID repetido; 2026-09-09 a 2026-10-01.
- Histórico previo al commit SIO b9a98c3cee49: 308 → 323 filas; IDs agregados=15, IDs quitados=0.
- El snapshot liviano conserva operacion=Anulación, Contrato, Rectificación (Anulación: 3; Contrato: 310; Rectificación: 10); incluye columna tipo_operacion=False. Mercado poblado en 0/323 snapshots; grupos diarios con más de un tipo de operación=9, mensuales=5; grupos mensuales con mezcla de condición=0, mercado=0.
- Operaciones válidas para serie en el snapshot: 323/323.
- La serie del dashboard actual cubre del 9 de septiembre al 1 de octubre de 2026. No hay un baseline anterior al 9 de septiembre en el snapshot versionado; la cobertura representa el piloto incremental observado.
- El resumen contiene fecha de actualización del dashboard, última captura, última operación y fechas mínima/máxima de operación.
- SIO no tiene plazas pobladas en el campo mercado; procedencia y lugar de entrega son metadatos separados.
- El filtro SIO visible usa tipo_precio=Precio Hecho. El campo tipo_operacion mapeado por el integrador no se conserva en el CSV liviano ni en los agregados usados por app.js. Por eso no se pueden filtrar Compraventa o Canje desde el dashboard.
- El campo operacion sí conserva Contrato/Rectificación/Anulación en el snapshot liviano, pero el preparador agrupa por tipo_precio y omite operacion en las series. Las 323 filas positivas incluyen operaciones de los tres estados. Los agregados diarios mezclan esos estados; no se presume aquí una regla de reversión/exclusión sin definición metodológica.
- La serie mensual SIO tampoco conserva mercado ni condicion_comercial en sus claves/campos. En esta captura mercado está vacío; no se detectó mezcla de mercado en los datos actuales. La cantidad de grupos que mezcla más de un valor de condición se muestra arriba.

## Estado Histórico local mensual

- 668 agregados mensuales, 2020-01-01 a 2026-08-01; commodities=Cebada forrajera, Girasol, Maíz, Soja, Sorgo, Trigo; plazas=Argentina / mercado interno — B.BLANCA, Argentina / mercado interno — CORDOBA, Argentina / mercado interno — DARSENA, Argentina / mercado interno — QUEQUEN, Argentina / mercado interno — ROSARIO.
- La fuente es mensual, en ARS por TN, con tipo Precio interno mensual y plazas Rosario, Córdoba, Dársena, Quequén y Bahía Blanca.
- Los CSV de resumen y agregados están completos para las columnas críticas; las observaciones con precio cero no aparecen en las series finales.

## Validación de filtros

- **OK — Rutas de fuentes separadas:** SIO y local mensual usan directorios y listas de CSV distintas.
- **OK — Sentinela Todos:** El filtro Todos se trata como comodín en commodityIsAll.
- **OK — Plaza Rosario por defecto:** El histórico local prefiere Rosario si está disponible.
- **OK — Frecuencia mensual local:** La fuente mensual fuerza la frecuencia mensual.
- **OK — Precios positivos:** Las filas usadas por el filtro principal y últimos precios requieren precio mayor que cero.
- **OK — Estado metodológico plaza:** La combinación local de todos los commodities y todas las plazas presenta un aviso.
- **OK — Destrucción y recreación Chart.js:** Se destruye la instancia previa antes de crear el siguiente gráfico.
- **Requiere corrección — Filtro SIO por tipo de operación:** SIO debe conservar el campo Tipo (tipo_operacion) y exponerlo como filtro, separado de tipo_precio.

- Verificación interactiva registrada:
  - Interacción local observada el 2026-10-02: SIO abrió con frecuencia mensual, ARS y TN; los KPIs mostraron 6 commodities y 180 operaciones con precio positivo, con gráfico mensual visible.
  - Interacción local observada el 2026-10-02: Maíz en SIO mostró evolución mensual. El único valor del filtro técnico fue Precio Hecho; no estuvieron disponibles Compraventa ni Canje.
  - Interacción local observada el 2026-10-02: el histórico local abrió en Rosario, ARS, TN y mensual; mostró 5 commodities, 343 observaciones y KPIs con datos.
  - Interacción local observada el 2026-10-02: Maíz + todas las plazas mostró una comparación por plaza y 3 registros más recientes disponibles para esa combinación.
  - Interacción local observada el 2026-10-02: todos los commodities + todas las plazas mostró el aviso para seleccionar plaza/mercado; el filtro permitió salir del estado.
  - GitHub Pages observada el 2026-10-02: ambas fuentes cargaron y mostraron KPIs; la navegación a Cantidades y Precios Mayoristas y el regreso a Commodities funcionaron sin errores de consola.

## Validación de fechas

- SIO: 2026-09-09 a 2026-10-01. La comparación de IDs entre snapshots consecutivos verifica la retención de filas previas y la incorporación incremental.
- Histórico local: 2020-01-01 a 2026-08-01; fecha de actualización reportada: 2026-09-09.
- La lógica de variación mensual SIO compara con la fila anterior disponible sin exigir el mes calendario inmediato anterior. Huecos encontrados en el dashboard actual: 0; no se observan huecos en el período disponible. Si aparece un hueco, la variación y el semáforo pueden representar varios meses como si fueran mensuales.
- En el workflow, la captura se agenda diariamente a las 13:30 UTC, equivalente a 10:30 de Argentina (UTC-3); GitHub puede iniciar con demora.

## Validación de monedas y unidades

- SIO: monedas observadas ARS y USD; unidad TN. Los agregados conservan moneda y unidad como dimensiones independientes.
- Histórico local: ARS y TN en todos los datos disponibles.
- app.js selecciona ARS y TN por defecto cuando la fuente ofrece esos valores. La interfaz no agrega valores de monedas o unidades diferentes en una misma fila.

## Validación de precios cero

- SIO: 0 celdas precio cero en archivos de series finales.
- Histórico local: 0 celdas precio cero en archivos de series finales.
- Celdas de precio cero en series dashboard-ready: 0. La captura versionada conserva indicadores de elegibilidad; app.js requiere precio mayor que cero antes de usar filas para KPIs, gráfico y últimos precios.

## Validación de GitHub Actions

- OK — workflow_dispatch: Permite disparo manual.
- OK — schedule diario: Expresión cron observada: 30.
- OK — horario documentado: Comentario documenta 10:30 de Argentina (UTC-3).
- OK — una consulta SIO: run_update_latest contiene una sola llamada HTTP y declara máximo 1 request.
- OK — sin paginación ni exportación manual: El workflow usa el snapshot latest y no activa paginación ni exportación manual.
- OK — sin publicar raw ni bases: El git add no incluye data/raw ni data/processed.
- OK — sólo salidas livianas: Publica CSV de dashboard y reportes livianos indicados.
- OK — permisos mínimos observables: contents: write es el único permiso declarado para permitir commit y push.
- OK — falla preserva salidas: Una captura no integrable no reemplaza snapshots y el paso de publicación se omite ante fallo.
- OK — sin cambios se omiten commits: Si no hay diff staged, el workflow termina sin crear commit.
- Requiere corrección — Publicación automática en Pages: El workflow SIO hace git push con las credenciales predeterminadas de checkout y Pages sólo escucha push a main. GitHub documenta que los commits publicados con GITHUB_TOKEN no disparan otros workflows ni una compilación de Pages.
- Observación — Escritura atómica de snapshots: Los archivos de snapshot se escriben directamente y en secuencia; una interrupción durante la escritura puede dejar el conjunto parcial.
- Observación — Orden de validación dashboard: El validador opcional se ejecuta antes del generador; si existe, revisa los CSV previos y no las salidas de esta corrida.
- Observación — Reconciliación de IDs existentes: Al repetir un ID, la integración conserva la primera fila y descarta una posterior aunque haya cambiado; no hay IDs repetidos en la captura auditada.

- Estado de runs recientes: Runs consultados=10 (9 del workflow SIO). Último run SIO: #25 completed/success (2026-10-01T18:56:38Z, schedule). Último exitoso: #25 (2026-10-01T18:56:38Z). Última falla visible: #21 (2026-09-27T17:50:48Z); paso: integrar snapshot e histórico liviano.
- La falla del 27 de septiembre de 2026 ocurrió en integración: el log reporta una fila leída y cero operaciones integrables porque el mapeo posicional quedó pendiente de validación. La etapa de auditoría, regeneración y publicación no se ejecutó; el integrador indicó que preservó las salidas anteriores.

## Validación local y GitHub Pages

- Localhost: HTTP 200; CSV comparados por contenido: 10/10.
- GitHub Pages: HTTP 200; CSV comparados por contenido: 10/10.
- Verificación interactiva de navegador: las fuentes SIO y local cargaron; el histórico abrió por defecto en Rosario; los KPIs mostraron datos; no se observaron errores de consola.
- Las filas y los campos de los CSV publicados coinciden con los del checkout. El control HTTP confirmó los recursos de commodities con respuesta 200.

## No regresión en otros módulos

- En localhost y GitHub Pages, los botones Cantidades transadas y Precios mayoristas abrieron sus vistas y permitieron volver a Commodities. No aparecieron errores de consola en la navegación.

## Observaciones

1. Requiere corrección el filtro de SIO: el dashboard sólo lleva tipo_precio (Precio Hecho) hasta las series; pierde tipo_operacion en la salida liviana y no muestra Compraventa/Canje. Corregirlo requiere propagar esa dimensión por la preparación de CSV y definir el agrupamiento correspondiente; no se aplicó durante una auditoría que prohíbe cambios metodológicos.
2. El flujo de actualización hace un commit/push con las credenciales predeterminadas de actions/checkout. Pages sólo se activa por push a main o por ejecución manual. GitHub documenta que los pushes hechos con GITHUB_TOKEN no activan otro workflow ni una compilación de Pages ([documentación oficial](https://docs.github.com/en/actions/concepts/security/github_token)). Los archivos servidos hoy coinciden con el checkout, pero una actualización diaria futura no publicará automáticamente esos CSV sin otro disparador válido.
3. El snapshot conserva 310 Contrato, 10 Rectificación y 3 Anulación, pero los agregados cuentan las 323 como observaciones positivas. Debe acordarse cómo tratar rectificaciones y anulaciones antes de interpretar conteos, volumen o medianas como operaciones vigentes; no se aplicó una regla nueva durante esta auditoría.
4. La variación mensual se calcula contra la fila anterior sin comprobar continuidad de meses. Los datos actuales no tienen huecos; una serie futura incompleta puede alimentar un semáforo que compare períodos no consecutivos.
5. La actualización escribe los CSV de snapshots secuencialmente sin archivos temporales ni reemplazo atómico. No hubo corrupción en los datos observados, pero una interrupción durante el guardado podría dejar sólo una parte actualizada.
6. La deduplicación mantiene la primera versión de un ID y descarta versiones posteriores con el mismo ID. No hay IDs repetidos en la captura auditada, pero una rectificación de origen bajo el mismo ID no reemplazaría el dato persistido.
7. El validador opcional de actualización dashboard corre antes de regenerar los archivos; si se incorpora, su ubicación actual valida la corrida anterior.
8. El rango SIO comienza el 9 de septiembre de 2026. La historia creció incrementalmente frente al snapshot padre, aunque no hay baseline anterior al inicio de cobertura.
9. Se observó una falla de integración el 27 de septiembre; las corridas posteriores incluidas en la consulta terminaron exitosamente.

## Conclusión

**Estado general: Requiere corrección.** Las fuentes SIO y local se cargan por separado, los CSV publicados coinciden con el checkout y las series finales no contienen precios cero. Hay defectos en los filtros/dimensiones del SIO y el commit automático no dispara Pages; además, la cobertura versionada empieza el 9 de septiembre de 2026.

## Consistencia de archivos dashboard-ready

- **OK — SIO snapshots → mensual:** Snapshot válido → mensual: 323 operaciones; faltantes=0, excedentes=0.
- **OK — Histórico local mensual → semáforo:** Claves mensual/semaforo: mensual=668, semáforo=668, diferencias=0.
- **OK — Histórico local mensual → últimos:** Último mensual por serie: esperado=17, publicado=17, diferencias=0.
- **OK — Precios cero fuera de series finales:** SIO=0 celdas cero; local mensual=0 celdas cero.
- **OK — CSV localhost/GitHub Pages vs checkout:** Local coincidente=10/10; Pages coincidente=10/10.

## Columnas críticas vacías

La tabla inicial resume los conteos por archivo. Los campos opcionales de variación no se tratan como críticos.
