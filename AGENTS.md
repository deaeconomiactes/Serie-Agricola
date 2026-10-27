# Instrucciones para agentes — Serie Agrícola

## Contexto del proyecto

Este repositorio contiene un dashboard estático publicado con GitHub Pages, una interfaz en `index.html`/`app.js` y pipelines de datos en Python. GitHub Pages sirve CSV ya preparados; no ejecuta Python ni debe consultar APIs privadas desde el navegador.

Commodities agrícolas es un módulo separado de las cantidades y los precios mayoristas frutihortícolas. La pestaña está en `index.html` y su configuración, carga de CSV, filtros y visualizaciones están en `app.js`.

## Cómo trabajar

- Antes de editar, identifica el pipeline y la documentación que corresponden a la tarea. Lee sólo las guías pertinentes; no es necesario releer todo el repositorio para cambios acotados.
- El agente raíz define el alcance y los criterios de aceptación, e intenta resolver directamente las tareas pequeñas o bien delimitadas antes de delegar.
- Delega sólo cuando el trabajo sea realmente independiente y el beneficio esperado supere el costo de contexto y coordinación. No crees una cadena fija de planner, explorer, implementer, reviewer y tester.
- Por defecto, no delegues. Si hace falta, usa como máximo un subagente activo y una sola ronda de delegación por tarea. No pidas a agentes distintos que repitan el mismo análisis; asigna un único responsable por archivo y fija objetivo, alcance, restricciones y resultado esperado.
- Usa `explorer` para búsquedas acotadas de código, contexto y estructura; `researcher` para verificar una pregunta concreta en fuentes oficiales; `worker` con Luna para una implementación independiente y bien acotada. El agente raíz integra la entrega y valida el diff.
- Escala a `sol_specialist` con GPT-6.1 Sol Medium sólo para decisiones arquitectónicas, cambios transversales, pipelines complejos, debugging persistente o cuando Terra no alcance una solución satisfactoria. No uses Sol como paso obligatorio.
- No invoques `reviewer` con Astra automáticamente. Resérvalo para una petición manual del usuario o un problema excepcionalmente complejo que siga sin resolverse después de Sol.
- Los subagentes heredan los permisos de la sesión principal: el perfil del agente no crea un entorno aislado ni garantiza acceso de sólo lectura. Elige los permisos de la sesión antes de delegar; si una exploración o revisión debe ser técnicamente de sólo lectura, usa una sesión principal de sólo lectura.
- `.codex/config.toml` define el modelo predeterminado del proyecto y los valores iniciales de subagentes; los perfiles personalizados pueden fijar su propio modelo. Si el usuario selecciona manualmente otro modelo en Codex, respeta esa selección y no intentes volver al predeterminado.
- Conserva el contexto: no leas el repositorio completo sin una razón concreta; localiza primero los archivos relevantes y devuelve síntesis breves. Al delegar, pasa sólo objetivo, archivos, estado, restricciones, hallazgos y pregunta específica necesarios.
- Ajusta la verificación al riesgo: cambios pequeños requieren comprobaciones específicas; cambios transversales, una revisión más amplia. No ejecutes un reviewer independiente en cada modificación.
- No implementes una API cuando la tarea sea investigar o preparar arquitectura. Distingue hechos verificados, hipótesis y cuestiones pendientes.
- En una implementación, añade o actualiza verificaciones específicas para las transformaciones y ejecuta las comprobaciones pertinentes antes de integrar.

## Política de modelos y eficiencia

- Modelo principal predeterminado: GPT-6.1 Terra Medium para el trabajo cotidiano del repositorio.
- Luna es la opción habitual para búsquedas, triage, recopilación de contexto, documentación y cambios mecánicos o acotados.
- Sol es un escalamiento selectivo para las tareas complejas descritas arriba; Astra no se inicia automáticamente.
- Esta política busca reducir consumo innecesario, pero no garantiza una duración fija de sesión: los límites de uso dependen de la cuenta y del consumo acumulado en todos sus proyectos.

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
