# Commodities locales mensuales

## Propósito

Esta carpeta prepara una fuente histórica mensual de precios de commodities agrícolas argentinos, priorizando la publicación oficial de Secretaría de Agricultura / Mercados Agropecuarios **“Evolución de Precios Internos de los Principales Granos”**.

El objetivo previsto es aportar contexto histórico local al módulo Commodities. La fuente no está cargada todavía: el pipeline genera encabezados y reportes sin datos cuando no existe un archivo en `raw/`.

## Diferencias metodológicas

- **SIO Granos:** operaciones informadas, con fecha, condición, moneda y unidad propias. No es una serie mensual de precios internos y se mantiene en `data/commodities_sio/`.
- **Precios internos mensuales:** referencias mensuales del mercado argentino en ARS/TN cuando la publicación declara explícitamente pesos argentinos por tonelada. La tabla se conserva por plaza/puerto dentro de `mercado`.
- **FAS teórico:** referencia de paridad/capacidad de pago para exportación; no es una operación SIO ni necesariamente un precio transado local.
- **FOB oficial:** referencia de exportación, normalmente en USD por tonelada y originalmente diaria. Si se usa como alternativa, se agrega a mensual con una regla documentada —por defecto, mediana diaria— y queda identificado como FOB oficial mensualizado.
- **World Bank Pink Sheet:** referencia internacional mensual. No reemplaza precios locales argentinos y queda fuera de este pipeline.

Nunca se mezclan en una misma serie, mediana, variación o ranking SIO, precios internos, FAS, FOB y World Bank. Cada registro debe conservar `fuente`, `mercado`, `tipo_precio`, `moneda`, `unidad` y `frecuencia`.

## Estructura

- `raw/`: descargas originales locales; no se versionan.
- `processed/`: integración normalizada completa; se regenera localmente y no se versiona por defecto.
- `dashboard/`: agregados mensuales livianos que pueden consumir las vistas visuales.
- `reports/`: auditorías, cobertura y comparación metodológica.

## Configuración segura

La configuración versionada de ejemplo está en `fuentes_local_mensual_config.example.json` e incluye las URLs públicas confirmadas de la serie 2020–2025 y el informe actual para 2026. El archivo local `fuentes_local_mensual_config.json` tiene prioridad y queda ignorado por Git para permitir ajustes controlados.

La descarga también puede recibir la configuración mediante `.env` o el entorno:

```text
LOCAL_MENSUAL_SOURCE_URL=
LOCAL_MENSUAL_SOURCE_NAME=
LOCAL_MENSUAL_RAW_FILENAME=
LOCAL_MENSUAL_MARKET=
LOCAL_MENSUAL_TIPO_PRECIO=
LOCAL_MENSUAL_CURRENCY=
LOCAL_MENSUAL_UNIT=
LOCAL_MENSUAL_INPUT_FREQUENCY=auto
LOCAL_MENSUAL_AGGREGATE_METHOD=median
```

Las URLs sólo se usan con `--allow-web`, para una descarga controlada por año. Sin esa opción no hay llamadas de red. No se inventan URLs, credenciales, precios ni cobertura.

## Flujo recomendado

```powershell
python .\descargar_commodities_local_mensual.py --dry-run --years 2020,2021,2022,2023,2024,2025,2026
python .\descargar_commodities_local_mensual.py --allow-web --years 2020,2021,2022,2023,2024,2025,2026
python .\integrar_commodities_local_mensual.py
python .\auditar_commodities_local_mensual.py
python .\preparar_commodities_local_mensual_dashboard.py
```

Si no existe una URL oficial estable, coloque manualmente una descarga autorizada en `raw/` y ejecute desde la integración. Para fuentes diarias como FOB, indique `--input-frequency diaria` y documente si se usó `median` o `mean`.

El descargador guarda el HTML y un registro de año/fecha en `raw/` y no realiza scraping masivo. El integrador transforma los dos bloques de la tabla ancha (trigo/maíz/sorgo y soja/girasol/cebada forrajera) a formato largo; `S/C` y celdas vacías quedan fuera sin inventar valores.

No incorporar la salida al dashboard hasta revisar procedencia, licencia, cobertura, fechas, monedas, unidades, tipo de precio, duplicados y continuidad mensual. La fuente local mensual se muestra separada de SIO mediante el selector de fuente; World Bank, FOB y FAS no se cargan en esta etapa.
