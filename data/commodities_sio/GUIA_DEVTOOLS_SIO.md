# Guía DevTools SIO Granos

Esta guía sirve únicamente para diagnosticar el request real de paginación de la grilla pública de SIO Granos. No habilita una descarga masiva ni integración al dashboard.

## Captura controlada

1. Abrir la consulta pública de SIO Granos en el navegador.
2. Abrir las herramientas de desarrollo del navegador (DevTools).
3. Ir a la pestaña **Network**.
4. Filtrar por **Fetch/XHR**.
5. Cargar la grilla de **Operaciones Informadas**.
6. Hacer clic en la página 2 de la grilla.
7. Identificar el request hacia `GetOperaciones` o un endpoint equivalente.
8. Copiar, si están disponibles y no contienen datos sensibles:
   - Request URL.
   - Request Method.
   - Headers relevantes.
   - Payload, Form Data o Request Body.
   - Response Preview, sólo si no contiene datos sensibles.
9. Como alternativa, usar **Copy as cURL** o exportar un archivo **HAR**.

## Manejo seguro del diagnóstico

- No subir capturas con datos sensibles.
- No commitear HAR, cURL reales, JSON, HTML o JavaScript de diagnóstico.
- Antes de compartir un HAR o cURL, eliminar cookies, tokens, autorizaciones, IDs de sesión y credenciales.
- Guardar los archivos locales en `data/commodities_sio/devtools/`; Git ignora `.har`, `.curl`, `.txt` y `.json` de esa carpeta.
- Usar la captura sólo para diagnóstico técnico del payload de paginación.

## Análisis local

Los siguientes comandos no ejecutan el HAR ni el cURL y no realizan llamadas web:

```powershell
python .\explorar_sio_granos.py --analyze-har data\commodities_sio\devtools\sio_paginacion.har
python .\explorar_sio_granos.py --analyze-curl data\commodities_sio\devtools\getoperaciones_page2.curl
```

El resultado se escribe en `data/commodities_sio/reports/REPORTE_REQUEST_DEVTOOLS_SIO.md` con headers y payload sanitizados. Si la captura revela que la sesión o cookies son obligatorias, no automatizar la consulta: conservar la descarga manual como alternativa.
