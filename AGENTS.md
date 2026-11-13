# Instrucciones para agentes — Serie Agrícola

## Contexto del proyecto

Este repositorio contiene un dashboard estático publicado con GitHub Pages, una interfaz en `index.html`/`app.js` y pipelines de datos en Python. GitHub Pages sirve CSV ya preparados; no ejecuta Python ni debe consultar APIs privadas desde el navegador.

Commodities agrícolas es un módulo separado de las cantidades y los precios mayoristas frutihortícolas. La pestaña está en `index.html` y su configuración, carga de CSV, filtros y visualizaciones están en `app.js`.

## Cómo trabajar

- Antes de editar, identifica el pipeline y la documentación que corresponden a la tarea. Lee sólo las guías pertinentes; no es necesario releer todo el repositorio para cambios acotados.
- El agente principal conserva la responsabilidad de comprender, implementar, integrar, verificar y reportar.
- Implementa directamente cuando el objetivo esté claro. Delega sólo cuando el trabajo sea independiente y el beneficio esperado supere el costo de contexto y coordinación; no uses una cadena fija de planner, explorer, implementer, reviewer y tester.
- La delegación es opcional, no automática. Cuando aporte valor, usa hasta dos subagentes concurrentes y evita duplicar análisis o asignar varios agentes al mismo archivo.
- Usa `explorer` con Luna Low para búsquedas acotadas y lectura del repositorio; `critical-reviewer` con Sol High para revisar bajo demanda cambios de riesgo elevado; y `ui-reviewer` con Terra Medium cuando una revisión visual o de UX sea material para la tarea. Ningún perfil se invoca por rutina.
- Los perfiles son instrucciones para el agente, no límites técnicos de permisos. Los subagentes heredan los permisos de la sesión principal; usa permisos de solo lectura en la sesión si se requiere aislamiento técnico de escritura.
- `.codex/config.toml` limita la concurrencia, pero no fija el modelo principal ni un modelo global para subagentes. Respeta el modelo que el usuario seleccione manualmente en Codex.
- Conserva el contexto: no leas el repositorio completo sin una razón concreta; localiza primero los archivos relevantes y devuelve síntesis breves. Al delegar, pasa sólo objetivo, archivos, estado, restricciones, hallazgos y pregunta específica necesarios.
- Ajusta la verificación al riesgo: cambios pequeños requieren comprobaciones específicas; cambios transversales, una revisión más amplia. No ejecutes un reviewer independiente en cada modificación.
- No implementes una API cuando la tarea sea investigar o preparar arquitectura. Distingue hechos verificados, hipótesis y cuestiones pendientes.
- En una implementación, añade o actualiza verificaciones específicas para las transformaciones y ejecuta las comprobaciones pertinentes antes de integrar.

## Política de modelos y eficiencia

- El modelo principal depende de la selección manual del usuario en Codex; este repositorio no fuerza uno.
- Usa Luna Low para exploración acotada, Sol High para revisión de riesgos elevados y Terra Medium para revisión visual bajo demanda.
- No crees agentes para cambios triviales ni repitas verificaciones sin una razón basada en el riesgo.

## Integridad de series de precios

- Conserva cada fuente como una serie identificable. No combines series sólo porque comparten commodity o fecha: operaciones SIO, precios internos, pizarra BCR, FAS/FOB, índices y referencias internacionales representan conceptos distintos.
- Cada observación y agregado debe conservar trazabilidad hasta el origen, fecha de observación y actualización, mercado/plaza, tipo de precio, moneda, unidad y frecuencia. Mantén también los valores y etiquetas originales cuando derives valores normalizados.
- Las conversiones de nomenclatura, unidad, moneda o frecuencia deben tener reglas explícitas y verificables; documenta las entradas, la regla aplicada y los campos resultantes.
- Incorpora fuentes nuevas de manera aditiva. No pises históricos existentes ni uses una serie distinta para rellenar sus faltantes. Conserva el fallback a datos existentes si el pipeline lo permite; ante un error de actualización, preserva la última salida válida.
- No incluyas claves, tokens, cookies ni otras credenciales en el repositorio, logs, CSV o frontend. La descarga debe ocurrir fuera del navegador; usa variables de entorno o el gestor de secretos disponible.
- Los datos publicados deben poder auditarse desde su origen hasta los CSV de dashboard y la visualización. Conserva los CSV dashboard-ready livianos y deja los datos crudos o bases completas fuera de Git cuando así lo indique la guía de la fuente.

## Mapa del flujo de commodities

- **SIO diario:** `explorar_sio_granos.py` captura un snapshot reciente; `integrar_commodities_sio.py` lo integra y deduplica; `auditar_commodities_sio.py` genera controles; `preparar_commodities_dashboard.py` produce los CSV de `data/commodities_sio/dashboard/`. `.github/workflows/update-sio-commodities.yml` automatiza esta secuencia y publica sólo salidas livianas. El snapshot de últimas operaciones no es un histórico completo y su paginación no está validada.
- **Precios internos locales mensuales:** `descargar_commodities_local_mensual.py` obtiene o registra las publicaciones; `integrar_commodities_local_mensual.py`, `auditar_commodities_local_mensual.py` y `preparar_commodities_local_mensual_dashboard.py` procesan la serie separada de SIO.
- **BCR:** el flujo de `descargar_commodities_bcr.py`, `integrar_commodities_bcr.py` y `auditar_commodities_bcr.py` contempla descargas manuales y una futura API, sujeta a confirmar contrato, autorización y credenciales.
- **Interfaz:** `app.js` carga por separado los CSV SIO y locales mensuales desde `data/*/dashboard/`; no consume sus bases completas.

Para SIO, consulta `data/commodities_sio/README.md`, `GUIA_ACTUALIZACION_DIARIA_SIO.md` y `GUIA_GITHUB_ACTIONS_SIO.md`. Para APIs de commodities, consulta `FUENTES_COMMODITIES_AGRICOLAS.md`, `data/commodities_bcr/API_BCR_PLAN.md` y `data/commodities_bcr/FUENTES_API_COMMODITIES_COMPARATIVO.md`. Para fuentes locales mensuales e internacionales, consulta los README y planes dentro de sus respectivas carpetas.

## Investigación de fuentes externas

Prioriza organismos oficiales y proveedores institucionales. Para cada alternativa informa proveedor, cobertura de productos, geografía/mercado, frecuencia e historia disponible, unidades, definición/metodología del precio, autenticación, límites, estabilidad, documentación, licencia/redistribución y posibilidades de automatización. Separa lo comprobado de lo no documentado y cita la fuente original. No recomiendes convertir o combinar series antes de confirmar que su definición lo permite.
