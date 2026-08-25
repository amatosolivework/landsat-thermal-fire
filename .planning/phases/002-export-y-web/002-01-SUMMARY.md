# SUMMARY 002-01 — export y web

**Fase completada:** 2026-08-25 · verificada en navegador real (Playwright)

## Resultados

- `scripts/4_exportar_web.py` → `portfolio/public/data/incendio/`: 5 capas LST
  (magma 20–65 °C, PNG8 cuantizado), 5 PNGs de valores para el tooltip, dNBR
  clasificado, par del comparador, `meta.json`. **2,6 MB total** (invariante <6 MB;
  el primer intento dio 7,4 y se cuantizó a paleta).
- Página `/labs/incendio` en el portfolio (commit `edaf21a`): comparador
  óptico/térmico con deslizador, mapa MapLibre con selector de 5 fechas +
  severidad con leyenda, readout de °C al hover (PNG de valores decodificado en
  canvas — sin backend), fila de números, sección "What this is — and isn't".
  Única dependencia nueva: maplibre-gl.
- Build de producción limpio; página prerenderizada estática.

## Bugs encontrados y arreglados durante la verificación

1. `import maplibregl from` → namespace import (el ESM de v6 no tiene default).
2. Tipo de `coordinates` de image source: tupla de 4, no array.
3. **fitBounds inicial desviado ~1° al sur**: el contenedor vive dentro del
   wrapper animado `Reveal` y su tamaño en construcción no es el final.
   Fix: `resize()` + `fitBounds()` explícitos en el evento `load`.
4. Falso negativo en el test del tooltip: los eventos sintéticos no disparan
   maplibre; con ratón real de Playwright el readout funciona ("50.1 °C").

## Deuda asumida (consciente)

- Basemap de tiles de Carto: dependencia externa en runtime (solo el fondo;
  las capas de datos son estáticas propias). Aceptable para una página de labs.
- La página no está enlazada desde la navegación del sitio — se enlazará desde
  el post MDX en la fase 003.

## Pendiente que hereda la fase 003

Post MDX, README final del repo, repo a GitHub público, deploy Vercel,
y revisar los mensajes de LinkedIn (humo/emisividad — ver SUMMARY 001).
