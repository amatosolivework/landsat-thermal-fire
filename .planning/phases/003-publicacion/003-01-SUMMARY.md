# SUMMARY 003-01 — publicación

**Fase completada:** 2026-08-25 · **PROYECTO CERRADO** (criterio spec §8 cumplido)

## Los tres enlaces vivos (verificados en producción, 200 + render + tooltip OK)

- Visor: https://alexmatosolive.com/labs/incendio
- Post: https://alexmatosolive.com/blog/watching-a-wildfire-in-thermal
- Repo público: https://github.com/amatosolivework/landsat-thermal-fire

## Qué se hizo

- Post MDX en inglés (voz de los posts existentes): el porqué del térmico, el
  pipeline, los dos bugs que cazaron los invariantes (AOI pequeña, agua como
  "quemada"), el reencuadre honesto del humo, y los enlaces.
- README final con las 3 figuras clave embebidas y enlaces a página y post.
- Repo creado público en `amatosolivework` vía gh-axi y pusheado.
- Portfolio pusheado → deploy automático de Vercel; página, post y datos
  estáticos verificados en producción con navegador real (readout "50.1 °C").
- Mensajes de LinkedIn actualizados: eliminada la frase de emisividad,
  añadidos resultados reales (La Mierla, 17σ, cicatriz a 60 °C, URLs) y una
  nota de qué NO prometer en entrevista.

## Estado final del proyecto

Pipeline reproducible en 4 comandos + venv. Deuda consciente: basemap Carto en
runtime; página no enlazada en la nav del sitio (accesible vía post y URL).
Posible evolución futura (no planificada): más incendios, serie temporal,
procesado de Sentinel-3 para revisita diaria.

## Retoque post-cierre (feedback de Alex, mismo día)

Los overlays a raster completo se veían como trapecios "pegados" (footprint de
escena) y el scroll de trackpad secuestraba el zoom. Cambios:
- Alpha por píxel horneado en el PNG desde el z-score (smoothstep 2σ→5σ):
  solo se dibuja lo anómalo; pre queda vacío a propósito (0,0% visible,
  29-jul 5,7%, post 2,0%). Copy añadido bajo el mapa explicándolo.
- Paleta de mapa YlOrRd (35–65 °C) — magma empieza en negro y sobre basemap
  claro leía como manchas de tinta. Comparador sigue en magma 20–65.
- `cooperativeGestures: true` — el scroll pasa a la página; zoom con ⌘+scroll.
- Script 3 ahora emite z-score también para pre/post.
