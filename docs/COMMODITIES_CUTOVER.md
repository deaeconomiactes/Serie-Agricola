# Cierre del cutover de Commodities — 21/10/2026

La auditoría partió de main actualizado después del run productivo exitoso
[39608556397](https://github.com/deaeconomiactes/Serie-Agricola/actions/runs/39608556397).
No se rehizo el backfill ni se modificaron precios, prioridades o metodología.

## Pendiente encontrado y cierre

El retiro anterior era condicional: un fallo del histórico oficial podía volver
a cargar el archivo local, mostrar su selector y emplearlo como contingencia.
Además, Pages empaquetaba la carpeta manual completa. Se retiraron esas rutas,
el selector HTML inicial y las ramas exclusivas del archivo manual.

Los 668/668 registros internos comparados siguen cubiertos, con cero diferencias
de precio. `data/commodities_local_mensual/` conserva sus originales para auditoría;
no se solicita desde el frontend y se excluye del paquete Pages. El reporte de
frescura conserva su registro inactivo, sin leer sus CSV en el updater productivo.
Si falla el histórico se mantiene el bundle corriente oficial válido; si fallan
ambos, se informa ausencia de datos y no se reactiva la fuente retirada.

## Fuentes y cobertura comprobada

| Familia | Histórico verificado | Frecuencia / moneda / unidad |
|---|---|---|
| Precio interno MAGyP | 01/1996–09/2026 | Mensual publicado; ARS/TN |
| Pizarra/Cámara MAGyP | 02/01/2018–19/10/2026 | Diario cuando publica; ARS/TN |
| FAS D.E.C. | 16/01/2007–20/10/2026 | Diario cuando publica; granos ARS/TN, aceites sin identificar |
| FOB SSPM | 04/01/1993–21/01/2025 | Índice calendario diario; USD/TN |
| FOB API corriente | Último dato 19/10/2026 | Diario cuando publica; moneda/unidad sin identificar |
| Futuros externos | 02/01/1995–20/10/2026 | Diario cuando publica; USD/TN, por vencimiento |

Las vistas mensuales de las familias diarias son derivadas. No se presentan como
mensuales publicados. SSPM y API FOB tienen identidades distintas; no se crea una
continuidad entre ambas. Futuros mantiene cada vencimiento y tipo de publicación,
sin roll. Los huecos y exclusiones documentados del histórico se conservan.

La revisión independiente de la unión real encontró cero duplicados por
`series_id + fecha/mes` y confirmó prioridad corriente en las coincidencias
compatibles. La carga histórica original y `commodity-history.js` no cambiaron.

## Frescura y tamaño del frontend

`PRICE_FRESHNESS_STATUS.json` mantiene cobertura histórica separada del estado
corriente. Internos, Pizarra, FAS y futuros: UPDATED. FOB: NO_PUBLICATION, conserva
el dato del 19/10. La serie SSPM finalizada en 2025 sigue VALIDATED_BACKFILL,
sin error por su fecha final. Las capturas exitosas corrientes de las cuatro
familias actualizadas corresponden al 21/10; FOB conserva la del 21/10 13:11 UTC.

CSV corrientes, bytes: internal 258148; board 118087; fas 334275; fob 1471954;
futures 789069. Histórico: 105 archivos, 33655742 bytes totales, máximo 1267526
bytes por archivo. El total no se descarga de una vez: mensual preparado y detalle
diario por año, con caché acotada. El navegador no solicita RAW/NORMALIZED completos
ni el archivo manual retirado. No se redujo la granularidad de las capas originales.

## Validación

- 74 tests Python y 63 frontend aprobados.
- 1122415 filas de vistas históricas verificadas por schema, SHA, dimensiones y conteos.
- Edge: 14 selecciones de fuente/año, con filas, producto, plaza, moneda, unidad y
  frecuencia válidos; cero duplicados visibles y cero errores JavaScript.
- Internos: 1996, 2000, 2010, 2020, 2026. Pizarra: 2018/2026. FAS: 2007/2026.
  FOB: 1993/2025/2026. Futuros: 1995/2026.
- Prueba enfocada en Commodities: los payloads ajenos de cantidades/mayoristas se
  omiten en esa sesión; sus regresiones se verifican por separado en los tests.
- Pruebas de paquete Pages: excluye el archivo retirado, conserva originales y
  outputs ajenos byte por byte; rechaza destino recursivo o preexistente.
- Actionlint y `git diff --check` aprobados.

El cambio prepara el próximo despliegue; no ejecuta un deploy ni un merge.
