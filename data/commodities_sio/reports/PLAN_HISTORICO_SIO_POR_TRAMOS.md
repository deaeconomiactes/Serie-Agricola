# Plan histórico SIO por tramos

## Objetivo

Preparar una ampliación histórica de SIO Granos sin confundir una ventana de consulta con la cobertura total de un año y sin alterar la serie SIO actualmente utilizada por el dashboard.

## Límite operativo

La consulta pública observada permite rangos de hasta **180 días**. Ese límite se toma como máximo operativo sugerido; no implica que cada tramo tenga datos completos ni que todos los años anteriores estén disponibles.

## Estrategia de tramos

1. Definir el período objetivo y los productos prioritarios.
2. Dividir el período en ventanas consecutivas inclusivas de hasta 180 días.
3. Si la interfaz o el endpoint generan dudas sobre los límites, usar una superposición mínima sólo para diagnóstico y resolverla mediante deduplicación documentada.
4. Ejecutar cada consulta de forma manual o controlada, sin scraping masivo.
5. Guardar los archivos originales y un registro de fecha solicitada, fecha recibida y estado de la consulta.
6. Auditar cada ventana por separado.
7. Consolidar únicamente después de revisar continuidad, duplicados, monedas, unidades, tipos de precio y calidad.

## Nombres de archivos esperados

Se recomienda identificar inicio y fin en el nombre:

- `SIO_exportar_operaciones_2024-01-01_2024-06-28.xlsx`
- `SIO_exportar_operaciones_2024-06-29_2024-12-25.xlsx`
- `SIO_exportar_operaciones_tramo_01_2024-01-01_2024-06-28.xlsx`

Los archivos se guardan localmente en `data/commodities_sio/raw/` y no se commitean. El CSV completo procesado queda en `data/commodities_sio/processed/` y también permanece fuera de Git por tamaño.

## Validaciones por tramo

Para cada archivo registrar:

- existencia, extensión y tamaño;
- encabezados y estructura;
- fecha mínima y máxima efectivamente recibidas;
- cantidad de filas leídas e integradas;
- commodities y productos faltantes;
- monedas, unidades y tipos de precio;
- precios cero, faltantes, negativos o no numéricos;
- identificadores `id_operacion_sio` y duplicados;
- procedencia, localidad, lugar de entrega y condición comercial cuando estén disponibles;
- fecha de descarga y evidencia de la consulta.

Una ventana que devuelva menos días de los solicitados, no tenga fecha válida o cambie de estructura debe quedar marcada para revisión y no incorporarse silenciosamente.

## Deduplicación y conflictos

Priorizar `id_operacion_sio` como clave. Cuando no exista, usar una clave compuesta con fecha, commodity, precio, moneda, unidad, volumen, procedencia, lugar de entrega y tipo de precio. Si dos filas comparten clave pero difieren en contenido, conservar ambas como conflicto y documentar la decisión; no descartar automáticamente una observación.

## Riesgos

- El límite de 180 días puede ser una regla de interfaz y no garantizar cobertura histórica real.
- Puede haber ventanas sin operaciones o con cobertura desigual por commodity.
- Puede cambiar la estructura de exportación, el significado de la fecha o la codificación.
- Una misma operación puede reaparecer en ventanas superpuestas o exportaciones repetidas.
- Moneda, unidad, condición comercial y tipo de precio pueden variar entre períodos.
- La consulta pública puede depender de sesión, permisos o disponibilidad temporal.
- La continuidad temporal no prueba comparabilidad económica si cambian definición, mercado o condiciones.

## Criterio para publicar

No incorporar los tramos al dashboard hasta verificar continuidad suficiente, deduplicación, comparabilidad metodológica, actualidad, permisos y trazabilidad. World Bank Pink Sheet puede aportar una serie mensual internacional separada, pero no debe completar ni rellenar huecos de SIO.

## Próximo paso

Realizar primero un piloto de dos ventanas consecutivas, generar sus reportes y comparar fechas, filas y series antes de solicitar el resto del período. Mantener la salida actual del dashboard sin cambios hasta cerrar esa auditoría.
