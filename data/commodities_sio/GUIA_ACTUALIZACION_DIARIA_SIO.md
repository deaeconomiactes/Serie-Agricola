# Guía de actualización diaria SIO

## Objetivo

Programar una captura controlada de las últimas operaciones SIO y regenerar el histórico incremental y los agregados livianos del módulo Commodities.

El flujo usa una sola consulta a `GetOperaciones` por corrida, con `pPageSize=20` y `pCurrentPage=1`. No pagina, no hace scraping masivo y no representa un histórico completo.

## Ejecución local

Desde la raíz del repositorio:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\scripts\update_sio_daily.ps1"
```

El script ejecuta, en orden:

1. captura de un snapshot latest con `--allow-web --save-response`;
2. integración y deduplicación del histórico local;
3. auditoría de la corrida;
4. regeneración de CSV dashboard-ready.

Los archivos raw, el snapshot latest y el histórico completo permanecen locales e ignorados por Git. El navegador sólo consume los archivos agregados livianos de `data/commodities_sio/dashboard/`.

## Programador de tareas de Windows

Crear una tarea básica con frecuencia diaria durante el piloto.

Programa:

```text
powershell.exe
```

Argumentos:

```text
-ExecutionPolicy Bypass -File "RUTA_DEL_REPO\scripts\update_sio_daily.ps1"
```

Usar como directorio de inicio la raíz del repositorio si el Programador de tareas lo solicita. La ruta debe ser la ubicación real del repositorio en cada equipo; no está hardcodeada en el script.

Frecuencia recomendada:

- diaria durante el piloto;
- cada 3 o 6 horas si se busca capturar más operaciones recientes.

El script actualiza archivos locales y no ejecuta `git add`, `git commit`, `git push`, merge ni force push. Para que GitHub Pages refleje nuevos CSV, se necesita un commit/push controlado o un workflow separado.

## Limitaciones operativas

- Si el proceso no corre un día, puede perder operaciones que desaparezcan del snapshot siguiente.
- La cobertura histórica acumulada comienza cuando se inicia el monitoreo.
- La paginación de `GetOperaciones` no está validada y no se usa.
- El flujo no reemplaza la exportación manual para construir historia anterior ni al histórico local mensual.
- ARS y USD se conservan como series separadas; los precios cero quedan fuera de los agregados de precios.

## Verificación posterior

Revisar:

- `data/commodities_sio/reports/REPORTE_ACTUALIZACION_DIARIA_SIO.md`;
- `data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_RESUMEN.csv`;
- `data/commodities_sio/dashboard/COMMODITIES_SIO_DASHBOARD_ULTIMOS.csv`;
- que `git status` no muestre raw ni las bases completas.
