# ROADMAP — landsat-thermal-fire

Objetivo: repo público + post + página `/labs/incendio` desplegados antes de la
primera semana de septiembre de 2026. Spec: `docs/superpowers/specs/2026-08-25-landsat-thermal-fire-design.md`.

## Fases

### 001-pipeline
Scripts 1–3: ingesta STAC (Planetary Computer), LST en °C con máscara de nubes,
z-score + dNBR. Salida: `data/derived/` + figuras estáticas + `stats.json`.
**Done cuando:** los invariantes físicos pasan y las figuras muestran la historia
(línea base limpia, fuego activo visible a través del humo, cicatriz en dNBR).

### 002-export-y-web
Script 4 (export PNG+JSON al portfolio) + página `/labs/incendio` en el repo portfolio
(comparador RGB/térmico, mapa MapLibre, números). MapLibre = única dependencia nueva.
**Done cuando:** la página funciona en local con datos reales y pasa el criterio de
los 30 segundos.

### 003-publicacion
Post MDX en el blog, README final del repo con instrucciones de regeneración,
repo a público, deploy en Vercel.
**Done cuando:** los tres enlaces (post, página, repo) están vivos y revisados.

## Orden y dependencias
001 → 002 → 003, estrictamente secuencial. El trabajo en el repo portfolio (002-003)
sigue las convenciones de ese repo, no las de este.
