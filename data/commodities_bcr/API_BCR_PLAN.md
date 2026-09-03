# Plan prudente de API BCR

## Objetivo

Preparar una futura descarga automatizada de Precios de Pizarra / Precios Cámara de BCR/Cámara Arbitral sin acoplarla al navegador ni asumir endpoints que no hayan sido confirmados por la institución.

## Estrategia

1. Confirmar con BCR/Cámara Arbitral si existe una API o descarga estructurada autorizada. Si se dispone de acceso GIX, documentar la modalidad, alcance, límites y condiciones de uso.
2. Configurar la URL base y el endpoint de precios mediante variables de entorno. El repositorio no contiene endpoints sensibles ni tokens por defecto.
3. Autenticar con `Bearer` cuando la API entregue un token. Si el proveedor requiere usuario y contraseña, usarlos únicamente desde variables de entorno o un gestor seguro para obtener el token.
4. Ejecutar la descarga desde `descargar_commodities_bcr.py`, un job local o un backend autorizado. `app.js` no realiza llamadas a BCR y nunca recibe credenciales.
5. Guardar la respuesta original en `data/commodities_bcr/raw/`, integrar a CSV procesado y auditar fechas, unidades, moneda, tipo de precio y procedencia antes de publicar.

## Variables esperadas

Ver [.env.example](../../.env.example): `BCR_API_BASE_URL`, `BCR_API_LOGIN_ENDPOINT`, `BCR_API_PRECIOS_CAMARA_ENDPOINT`, `BCR_API_KEY`, `BCR_API_SECRET`, `BCR_API_TOKEN`, `BCR_API_USE_AUTH` y `BCR_COMMODITIES_DEFAULT_DAYS_BACK`. Se conservan `BCR_API_PRICES_ENDPOINT`, `BCR_API_USER` y `BCR_API_PASSWORD` por compatibilidad, pero se prefieren `api_key`/`secret` o token si la documentación de BCR/GIX los utiliza.

El endpoint se deja vacío hasta confirmarlo. La ausencia de endpoint o de credenciales no es un error: el script informa que debe usarse la descarga manual.

El downloader opera en modo manual por defecto y no hace llamadas de red. Una consulta API requeriría `--source api --allow-api`, endpoint, token Bearer o credenciales API confirmadas, identificadores `bcr_id_grano` confirmados y autorización. Si el token dura 24 horas, debe renovarse fuera del repositorio y nunca guardarse en raw/ ni en Git.

## Seguridad y trazabilidad

- Nunca guardar usuario, contraseña, api_key, secret, token o archivos `.env` en Git.
- Nunca imprimir secretos; el modo `dry-run` sólo muestra presencia y valores enmascarados.
- No inventar `bcr_id_grano`; los identificadores pendientes quedan vacíos en el catálogo.
- No llamar a la API sin configuración explícita y suficiente.
- Conservar fecha de descarga, URL no sensible, nombre del archivo original y respuesta sin alterar cuando las condiciones de uso lo permitan.
- Auditar antes de utilizar el CSV en un dashboard, verificando que la fuente sea pizarra/Cámara y que la serie sea homogénea.

## Fallback manual

Si no hay API estable o credenciales autorizadas, descargar desde la interfaz oficial de BCR/Cámara Arbitral y colocar los archivos en `data/commodities_bcr/raw/`. La automatización puede retomarse cuando exista un canal estructurado y autorizado.
