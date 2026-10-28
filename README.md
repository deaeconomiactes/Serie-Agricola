# Serie Agrícola

Plataforma de información agropecuaria orientada al seguimiento de mercados, análisis económico y toma de decisiones. [Dashboard público](https://deaeconomiates.github.io/Serie-Agricola/).

## Módulos

- **Cantidades transadas:** toneladas de frutas y hortalizas registradas en 2024–2025, con mercados y procedencias de la base integrada. La fuente es estática y no acredita actualización automática ni cobertura exhaustiva.
- **Precios mayoristas:** MCBA diario de MAGyP, vista mensual derivada de observaciones diarias de Mercado Central y serie estática de Corrientes. La cobertura y frecuencia varían por fuente; el mensual derivado no es una publicación mensual oficial.
- **Commodities agrícolas:** precio interno MAGyP, pizarra/cámara, FAS, FOB y futuros externos. SIO presenta operaciones como una fuente independiente; sus snapshots recientes no constituyen un histórico completo.
- **Carnes:** faena, producción y peso medio de fuentes oficiales, con series históricas secundarias identificadas como finalizadas cuando corresponde. La cobertura depende de la métrica y la fuente.

## Principios de datos

El flujo distingue **RAW → NORMALIZED → ANALYTICAL → DASHBOARD**. Se priorizan fuentes oficiales, se conserva trazabilidad y no se mezclan metodologías incompatibles. Una actualización fallida preserva la última salida válida; no se inventan datos faltantes.

## Automatización

GitHub Actions actualiza commodities MAGyP, SIO, MCBA y la vista mensual derivada de Mercado Central; otro workflow construye y publica GitHub Pages. MCBA depende de un runner Windows self-hosted. Existe además un diagnóstico manual Chromium. Ver [operación](docs/OPERACION_WORKFLOWS.md).

Los estados describen resultados diferentes: `UPDATED` (salida nueva), `NO_OP_ALREADY_CURRENT` (ya vigente), `NO_PUBLICATION` (sin publicación nueva), `SOURCE_UNAVAILABLE` (fuente inaccesible), `PIPELINE_ERROR` (error de procesamiento o publicación) y `HISTORICAL_ENDED` (serie histórica finalizada). Cada flujo utiliza los estados que corresponden a su fuente.

## Stack y estructura

HTML, CSS y JavaScript con Chart.js; Python para pipelines y construcción; GitHub Actions y GitHub Pages para automatización y publicación.

```text
index.html, app.js y módulos JS/CSS   Interfaz
assets/                              Recursos visuales
config/                              Configuración de fuentes
scripts/                             Pipelines, constructores y validadores
data/                                Publicaciones, catálogos y auditorías
tests/                               Regresiones y fixtures
docs/                                Documentación técnica
.github/workflows/                   Automatización
```

## Desarrollo local y tests

Desde la raíz, ejecutar `python -m http.server 8767` y abrir `http://localhost:8767/`. Para reproducir el paquete de Pages se necesitan Node, los inputs versionados y el secreto de desencriptación de cantidades utilizado por el workflow; consultar [operación](docs/OPERACION_WORKFLOWS.md).

Las suites Python se ejecutan por área, por ejemplo `python -m unittest discover -s tests/magyp_common -v`; las áreas adicionales están bajo `tests/`. Frontend: `node --test tests/magyp_frontend/*.cjs`. El builder de Mayoristas es `python scripts/mayoristas/build_dashboard.py`.

## Documentación y limitaciones

El [índice técnico](docs/README.md) reúne arquitectura, fuentes, operación y evidencia histórica. Las fuentes difieren en cobertura, frecuencia y definición; las capturas recientes no garantizan historia completa. Cantidades y algunas series de carnes y Corrientes son estáticas o históricas. La disponibilidad de MCBA depende también del runner y de la fuente externa.
