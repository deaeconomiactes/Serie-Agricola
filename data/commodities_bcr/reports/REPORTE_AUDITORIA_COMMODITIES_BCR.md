# Auditoría de commodities agrícolas BCR

## 1. Resumen ejecutivo

Se auditaron **0 registros** de `C:\Users\acer\Oficina\Serie-Agricola\data\commodities_bcr\processed\COMMODITIES_BCR_INTEGRADO.csv`. Se detectaron **0 commodities**, **0 archivos de origen** y **0 precios válidos**.

El rango de fechas válidas es **n/d** a **n/d**. Años disponibles: **n/d**. Frecuencias detectadas: **Sin determinar**.

La auditoría corresponde exclusivamente a la capa exploratoria de BCR/Cámara Arbitral. No se cruza con cantidades ni precios frutihortícolas.

## 2. Fuente y alcance

La fuente piloto es BCR / Cámara Arbitral de Cereales, específicamente descargas manuales de precios de pizarra. El alcance esperado son commodities agrícolas/granos, no precios frutihortícolas. El integrador no realiza scraping ni llamadas de red.

## 3. Cobertura temporal

- Filas totales: 0.
- Archivos origen: 0.
- Registros con fecha válida: 0.
- Rango: n/d a n/d.
- Años: n/d.
- Meses distintos: 0.

El detalle por año y por commodity-año se encuentra en `RESUMEN_COBERTURA_COMMODITIES_BCR.csv`.

## 4. Cobertura por commodity

No hay registros para resumir.

## 5. Calidad de precios

- Precios válidos (> 0): 0.
- Precios cero: 0.
- Precios negativos: 0.
- Precios faltantes o no numéricos: 0.
- Registros con moneda válida: 0.
- Registros con unidad válida: 0.
- Outliers por commodity usando IQR (1,5 × IQR), conservados y no eliminados: 0.

Los casos individuales se encuentran en `CASOS_PROBLEMATICOS_COMMODITIES_BCR.csv`.

## 6. Series utilizables

- Series Alta: 0.
- Series Media: 0.
- Series Baja: 0.

La clasificación usa las claves commodity, mercado, tipo de precio, moneda, unidad y frecuencia. Alta requiere al menos 30 observaciones, 20 fechas distintas y más de 90% de precios válidos; Media requiere al menos 10 observaciones, 5 fechas distintas y más de 70%; el resto es Baja.

## 7. Problemas detectados

Se detectaron **0 registros problemáticos**. Las categorías pueden superponerse: fecha faltante/inválida, precio faltante/no numérico, cero, negativo, moneda o unidad faltante y outlier IQR. Los outliers no se eliminan automáticamente porque requieren revisión metodológica.

## 8. Recomendación para futura incorporación al dashboard

Mantener commodities como tercer módulo independiente y comenzar, si se aprueba el piloto, con una única serie homogénea de precios de pizarra BCR. Mostrar fuente, mercado Rosario, moneda, unidad, condición comercial y fecha de actualización. No publicar una serie hasta validar una muestra histórica, cobertura, permisos de uso y estabilidad del formato descargado.

## 9. Limitaciones metodológicas

- Estos datos corresponden a commodities agrícolas/granos.
- No deben mezclarse directamente con frutas y hortalizas.
- No representan cantidades transadas.
- No deben cruzarse con precios frutihortícolas para inferir causalidad.
- La unidad, moneda y condición comercial deben conservarse.
- Precio de pizarra, FOB/FAS, disponible y futuros no deben mezclarse como si fueran el mismo tipo de precio.

El valor por defecto del integrador para descargas BCR sin columnas explícitas es ARS y $/Tn, y queda anotado como supuesto pendiente de validación. Las fechas mensuales o anuales no se convierten artificialmente en fechas diarias.
