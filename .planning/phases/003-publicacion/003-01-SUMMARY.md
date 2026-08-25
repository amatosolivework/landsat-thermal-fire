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
