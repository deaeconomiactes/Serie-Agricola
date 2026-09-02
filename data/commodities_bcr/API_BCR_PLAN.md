# Plan de automatización API BCR

## Objetivo

Preparar una ruta de automatización para las descargas de commodities BCR sin acoplarla al navegador ni introducir credenciales en el dashboard. La fuente piloto sigue siendo BCR / Cámara Arbitral de Cereales y la referencia prioritaria son los precios de pizarra o precios Cámara.

## Estrategia propuesta

1. Ejecutar un descargador local en Python o un backend controlado.
2. Consultar una API BCR/GIX sólo si el equipo dispone de credenciales, autorización y documentación vigente.
3. Enviar autenticación mediante token Bearer cuando el contrato de la API lo requiera.
4. Guardar la descarga original en `data/commodities_bcr/raw/` y generar el CSV limpio en `processed/`.
5. Ejecutar la integración y la auditoría antes de publicar cualquier dato.
6. Mantener la descarga manual como fallback cuando no haya API, credenciales o un formato estable.

El descargador incluido en esta etapa detecta configuración y arma el plan de consulta, pero no consume endpoints no confirmados ni realiza llamadas HTTP implícitas. La implementación del adaptador concreto debe esperar la confirmación oficial del endpoint, parámetros, formato, límites y permisos de uso.

## Credenciales y seguridad

- Nunca guardar usuarios, contraseñas, tokens o secretos en el repositorio.
- Usar variables de entorno o un gestor de secretos del entorno de ejecución.
- El archivo `.env` es local y está ignorado; `.env.example` contiene únicamente nombres de variables vacíos.
- Nunca imprimir credenciales completas. Los diagnósticos deben enmascarar usuario, contraseña y token.
- Si se usa Bearer, construir `Authorization: Bearer <token>` sólo dentro del proceso de descarga y nunca incorporarlo a logs, CSV, reportes o frontend.
- No exponer credenciales en `app.js`, `index.html`, `styles.css` ni en ningún recurso servido al navegador.

## Modos de operación

### API

El script `descargar_commodities_bcr.py` entra en modo API cuando detecta una URL base y una configuración de autenticación suficiente. El uso real queda condicionado a validar el contrato API BCR/GIX. La llamada deberá ejecutarse desde Python local o backend, con timeout, control de errores, registro de fecha de descarga y validación del archivo recibido.

### Manual

Si faltan credenciales o configuración, descargar manualmente desde BCR/Cámara Arbitral y colocar los archivos originales en `raw/`. Luego ejecutar:

```powershell
python .\integrar_commodities_bcr.py
python .\auditar_commodities_bcr.py
```

## Controles antes de automatizar

- confirmar que la API/GIX es la fuente autorizada para precios de pizarra o precios Cámara;
- confirmar si el precio es local, disponible, FOB/FAS, cierre o futuro;
- verificar productos, unidades, monedas, frecuencia, fechas y paginación;
- revisar límites, licencia, redistribución interna y retención de datos;
- probar primero en `--dry-run` y con una ventana corta;
- conservar respuesta original, metadatos y fecha de descarga para auditoría;
- detener la automatización ante cambios de esquema o respuestas incompletas.

## Flujo de publicación

La API o la descarga manual nunca deben alimentar directamente el navegador. El flujo previsto es:

`fuente BCR → raw → integración → processed → auditoría → revisión → dashboard futuro`

Commodities permanece como tercera familia separada de cantidades y precios mayoristas frutihortícolas.
