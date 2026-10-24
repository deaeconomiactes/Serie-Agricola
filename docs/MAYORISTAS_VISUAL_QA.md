# QA de adopción visual · Mayoristas

final result: passed

## Evidencia conjunta

Referencia de lenguaje: Carnes aprobado, captura `C:/Users/acer/Oficina/carnes-ui-evidence/reference-rebuild/msedge-1440-slaughter.png`. Implementación: `mayoristas-after/msedge-1440-monthly.png` bajo el mismo directorio base. Comparación conjunta `mayoristas-after/design-system-comparison.png`: cada vista conserva 1440 × 1050 px de viewport, densidad 1; se añaden sólo etiquetas de identificación. Se inspeccionaron juntas tras las correcciones.

No se busca igualdad de layouts: Mayoristas conserva sus preguntas de precio y comparación, su metadata y sus propios datasets. El antes/después del módulo completo está en `mayoristas-after/comparison-1440.png` y `comparison-900.png`, y en la galería `mayoristas-review.html`. No se rediseña Carnes.

## Hallazgos corregidos

- [P2] La primera grilla dejaba un hueco junto a variaciones y extendía demasiado el chart de mercados. Se explicitó la celda de mercado y el tamaño del cuerpo de los charts; evidencia posterior en captura mensual completa.
- [P2] Una regla de cifras de KPI ampliaba indebidamente fecha y conteos de metadata. Se fijó su escala compacta; las tres cifras principales conservan la jerarquía ejecutiva.
- [P2] El padding heredado duplicaba el margen superior. Se acotó el padding a la región principal y se compactó el hero sin una imagen o texto ornamental obligatorio.
- [P2] La revisión independiente encontró un disclosure de cambios vacío en diaria. Se deriva su visibilidad exclusivamente de la de sus dos cards existentes. El navegador Chrome verifica la desaparición al pasar a diario MCBA.

## Superficies y estados

- Tipografía: Inter y escala del sistema; labels, títulos, unidades y cifras alineados; metadata menor que el precio. Los valores extremos no se confunden con un intervalo de confianza.
- Espacios/grid: rail 176/150 px, gutters y radios del piloto, grilla analítica flexible; a 900 evoluciones y rankings se apilan; a 640 rail horizontal y tabla con scroll propio.
- Colores: fondo/panel/inset/menta del piloto; acentos de símbolos funcionales y paleta de charts existente. Sin nuevos semáforos ni umbrales.
- Assets: marca e iconos existentes, sin recursos rasterizados de la interfaz ni nuevo hero fotográfico. Carnes conserva su imagen y su layout.
- Copy: información económica preservada, fuente/unidad visibles, alcance de promedio y extremos aclarado, comparación de fuentes separada de procedencia. Matriz mensual conservada bajo demanda, sin afirmar una estacionalidad histórica no calculada.
- Interacción: nav abre y enfoca secciones; Más filtros y Escape, dropdown superior a charts, metodología, tabla, búsqueda y paginación; charts ocultos sólo reciben resize al abrir un detalle. Estados problemáticos siguen visibles fuera de disclosures.

## Validación

18 tests focales Node aprobados. Entrega y corrupción/selección tardía verificadas en Edge/Chrome, con 3 solicitudes iniciales y 849.526 bytes. Snapshot mensual exacto antes/después de filas, KPIs, datasets y matriz. JS de cálculos/loaders y archivos aprobados de Carnes byte idénticos al respaldo. Sin errores JS ni desborde global en pruebas de navegador a 1440/1000/900/640.

No quedan hallazgos P0/P1/P2. Refinamiento P3 posible: futura extracción técnica de tokens compartidos cuando se integren más módulos; no es necesaria para mantener el piloto aprobado.


## Cierre definitivo

Ver [cierre visual y funcional del 24/10/2026](MAYORISTAS_CIERRE_VALIDACION_2026-10-24.md), con capturas nuevas, ajustes menores, pruebas y recomendación de integración.
