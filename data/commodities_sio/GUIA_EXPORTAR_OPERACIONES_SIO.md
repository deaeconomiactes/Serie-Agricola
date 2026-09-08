# Guía local: Exportar Operaciones de SIO

## Objetivo

Capturar de forma segura el request que genera el botón **EXPORTAR OPERACIONES**, sin ejecutar automatizaciones ni exponer información de sesión.

## Pasos

1. Abrir SIO Granos en el navegador.
2. Ir a **Operaciones Informadas**.
3. Abrir DevTools.
4. Ir a **Network** y filtrar por **Fetch/XHR**.
5. Limpiar la lista de Network.
6. Hacer clic una sola vez en **EXPORTAR OPERACIONES**.
7. Identificar el request generado, incluyendo endpoint, método, payload y tipo de respuesta.
8. Copiarlo como cURL o exportar un HAR.
9. Guardarlo sólo de forma local como `data/commodities_sio/devtools/exportar_operaciones.curl` o `data/commodities_sio/devtools/exportar_operaciones.har`.

## Seguridad

- No commitear cURL ni HAR.
- No exponer ni copiar cookies, tokens, credenciales o IDs de sesión.
- No ejecutar el cURL copiado sin revisarlo.
- Usar el analizador local para obtener un reporte sanitizado:

```powershell
python .\explorar_sio_granos.py --analyze-curl data\commodities_sio\devtools\exportar_operaciones.curl
python .\explorar_sio_granos.py --analyze-har data\commodities_sio\devtools\exportar_operaciones.har
```

Estos comandos no ejecutan cURL ni realizan llamadas de red. Si aparece un candidato de exportación, generan `reports/REPORTE_EXPORTACION_SIO.md` con la evidencia disponible.

## Descarga manual

Si la exportación depende de sesión, descargar el archivo desde el navegador y colocarlo, sin versionarlo, en `data/commodities_sio/raw/` con uno de estos nombres:

- `SIO_exportar_operaciones_*.xlsx`
- `SIO_exportar_operaciones_*.xls`
- `SIO_exportar_operaciones_*.csv`

Luego ejecutar `python .\integrar_commodities_sio.py` y `python .\auditar_commodities_sio.py`. La salida se conserva en `COMMODITIES_SIO_EXPORTACION_MANUAL.csv`, separada del piloto de GetOperaciones.

## Historia anterior por tramos

La consulta pública observada admite rangos de hasta 180 días. Para recuperar un período histórico mayor:

1. dividir el período en ventanas consecutivas de hasta 180 días;
2. guardar cada exportación con un nombre que identifique inicio y fin, por ejemplo `SIO_exportar_operaciones_2024-01-01_2024-06-28.xlsx`;
3. registrar para cada tramo el rango pedido, el rango recibido, filas, commodities, monedas, unidades y posibles errores;
4. auditar cada archivo antes de unirlo;
5. deduplicar por `id_operacion_sio` o por una clave compuesta, conservando conflictos para revisión;
6. verificar continuidad entre ventanas y recién entonces evaluar una base histórica.

No asumir que todo año anterior está disponible y no ejecutar scraping masivo. La ampliación no debe llegar al dashboard hasta validar continuidad, comparabilidad metodológica, permisos y ausencia de duplicados relevantes. Ver [PLAN_HISTORICO_SIO_POR_TRAMOS.md](reports/PLAN_HISTORICO_SIO_POR_TRAMOS.md).
