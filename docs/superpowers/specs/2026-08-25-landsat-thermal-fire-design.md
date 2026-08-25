# Diseño: análisis térmico del incendio de La Mierla con Landsat

**Fecha:** 2026-08-25 · **Estado:** aprobado en conversación, pendiente de revisión escrita
**Repo:** `landsat-thermal-fire` (este) · **Consumidor:** `portfolio` (repo hermano)

## 1. Propósito

Demostrar dominio del pipeline de observación térmica de la Tierra —ingesta STAC, cálculo de temperatura de superficie, detección de anomalías, visualización web— como pieza de candidatura a prácticas en Aistech Space. El proyecto replica en miniatura, con datos abiertos de Landsat, el tipo de producto que Aistech construye con su constelación Hydra.

**Audiencias y artefactos:**

| Audiencia | Artefacto | Qué debe transmitir |
|---|---|---|
| CEO / no técnico | Página `/labs/incendio` en el portfolio | La historia en 30 segundos: el térmico ve a través del humo |
| CTO / técnico | Este repo, público al terminar | Código limpio, pipeline reproducible, criterio |
| Ambos | Post MDX en el blog del portfolio | Proceso, hallazgos y limitaciones dichas en voz alta |

**Posicionamiento obligatorio:** esto se presenta como "lo hice para entender vuestro problema", nunca como "hice lo vuestro". Landsat: 100 m térmico, revisita 8 días por path. Hydra: decenas de metros, revisita de horas. La diferencia se dice explícitamente en el post y el README.

## 2. Caso de estudio (verificado)

**Incendio de La Mierla, Sierra Norte de Guadalajara, agosto de 2026.** Mayor incendio del año en España: >32.000 ha (fuentes: eldiario.es, moncloa.com, 15-20 ago 2026). Fecha exacta de inicio: confirmar en prensa durante implementación (estimado 9–12 ago).

**Área de interés (AOI):** bbox `[-3.45, 40.85, -3.05, 41.10]` (WGS84), ajustable al perímetro real durante implementación.

**Disponibilidad de escenas — VERIFICADA el 2026-08-25** contra Microsoft Planetary Computer (`landsat-c2-l2`). La AOI cae en el solape de los paths WRS-2 200 y 201 (rows 031/032) → revisita efectiva 3–4 días. 36 escenas <30% nube entre jun–ago 2026. Triplete seleccionado (provisional):

| Rol | Fecha | Escena | Nube |
|---|---|---|---|
| Línea base (antes) | 2026-08-06 / 07 | `LC08_L2SP_201032_20260806` · `LC09_L2SP_200032_20260807` | 0,4–1,2% |
| Fuego activo (durante) | 2026-08-14 | `LC09_L2SP_201032_20260814` | 18,1% (**probablemente humo clasificado como nube — es la tesis del proyecto**) |
| Cicatriz (después) | 2026-08-23 | `LC09_L2SP_200032_20260823` | 19,7% |
| Línea base histórica | jun–jul 2026 | ~6 escenas limpias (0–10% nube) | para la media pre-incendio del z-score |

**Plan B (si el triplete falla al inspeccionarlo):** incendios de Larouco (Ourense) o Uña de Quintana (Zamora), agosto 2025 — un año de archivo garantiza escenas, se pierde el "durante" reciente.

## 3. Arquitectura

```
Microsoft Planetary Computer (STAC, público, sin credenciales para búsqueda;
                              assets firmados vía planetary_computer.sign())
        |
   [1] buscar_escenas.py       -> data/raw/          GeoTIFFs por escena/banda
   [2] calcular_temperatura.py -> data/derived/      LST en °C, nubes enmascaradas
   [3] detectar_anomalias.py   -> data/derived/      máscaras z-score, dNBR, stats
   [4] exportar_web.py         -> ../portfolio/public/data/incendio/   PNG+JSON
        |
   portfolio: /labs/incendio (MapLibre) + content/blog/*.mdx
```

**Frontera dura:** Python ↔ web es un directorio de ficheros estáticos. Sin backend, sin base de datos, sin servicios vivos. El portfolio no ejecuta nada; Python no sabe que existe la web.

**Reglas de peso:** `data/` está gitignoreado (GBs de GeoTIFF). Al portfolio solo llegan PNGs con paleta + JSON (<10 MB total). El README documenta cómo regenerar `data/` desde cero.

## 4. Contratos de los scripts

Cada script: una responsabilidad, lee disco / escribe disco, ejecutable y depurable por separado. Config compartida (AOI, fechas, escenas elegidas) en `config.py` o `config.toml` — un único punto de verdad.

1. **`1_buscar_escenas.py`** — consulta STAC por AOI+fechas, filtra nube, descarga solo bandas necesarias: ST_B10 (térmica L2, ya en Kelvin escalado), ST_QA, QA_PIXEL, SR_B4/B3/B2 (RGB), SR_B5 (NIR), SR_B7 (SWIR2, para NBR). Idempotente: no re-descarga lo que ya existe.
2. **`2_calcular_temperatura.py`** — aplica factores de escala del producto Collection 2 L2 (`ST_B10 * 0.00341802 + 149.0` → K → °C), enmascara nube/sombra con QA_PIXEL, recorta a AOI, reproyecta a grid común. Nota: L2 ya trae LST con corrección de emisividad del USGS — el post lo explica en vez de reimplementarlo (honestidad > teatro).
3. **`3_detectar_anomalias.py`** — z-score por píxel contra media/σ de la línea base jun–jul; umbral configurable (default z>3). dNBR (NBR_antes − NBR_después) para el perímetro quemado, clases estándar USGS. Salidas: máscaras + `stats.json` (ha detectadas, T máx, comparación con cifra oficial).
4. **`4_exportar_web.py`** — rásteres → PNG con paleta perceptual (magma para LST) + JSON con bounds geográficos, fechas, leyenda y stats. Flag `--out` apunta al portfolio.

**Testing:** al ser un análisis one-shot, no hay suite formal; cada script valida invariantes físicos al terminar (LST en rango −20…+90 °C fuera del fuego; % píxeles enmascarados reportado; ha dentro de orden de magnitud de la cifra oficial) y aborta ruidosamente si fallan. Errores: fail-fast, nada de fallbacks silenciosos.

## 5. Página `/labs/incendio` (portfolio)

Tres bloques en orden:

1. **Comparador deslizante** RGB vs térmico de la escena del 14-ago (el humo tapa / el térmico ve). Componente propio ligero (dos `<img>` + clip-path + input range), sin dependencia nueva.
2. **Mapa MapLibre** — capa LST como image overlay georreferenciado, selector antes/durante/después, tooltip con °C del píxel (lookup en un array descargado, no tile server).
3. **Números** — ha detectadas vs cifra oficial, T máx, y una línea sobre por qué difieren.

MapLibre GL JS es la única dependencia nueva del portfolio. Página estática (`generateStaticParams` no aplica; es una ruta única). Tema/estética: heredar el sistema del portfolio existente.

## 6. Post MDX

`content/blog/` siguiendo el formato de los 7 posts existentes. Estructura: por qué (Aistech/Hydra como disparador, mencionado con elegancia) → cómo (STAC, LST, z-score, dNBR, con figuras del repo) → hallazgos (el humo-vs-térmico como clímax) → **limitaciones** (100 m, 8 días, USGS ya hace la corrección de emisividad, mi cifra vs la oficial) → qué haría con más tiempo. Enlace prominente al repo.

## 7. Fuera de alcance (deliberado)

Backend · BD · ingesta en vivo · tasking · ML · múltiples incendios · tiempo real · tile server · reimplementar la corrección atmosférica/emisividad del USGS.

## 8. Criterios de éxito

1. Un no-técnico entiende la página en 30 segundos sin leer.
2. `git clone` + README → cualquier técnico regenera todo con una secuencia documentada de comandos.
3. Cifra de ha propia vs oficial comparadas y explicadas.
4. Publicado: repo público + post + página desplegada en Vercel, antes del envío de mensajes (primera semana de septiembre).

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| La escena del 14-ago no muestra fuego activo (fecha de inicio distinta) | Confirmar cronología en prensa; hay escena 200031/032 cada 3-4 días; peor caso: la historia se cuenta con antes/después + dNBR |
| "Nube" del QA enmascara el humo y borra la señal | Usar QA con criterio: mostrar también la banda térmica sin máscara en la zona del fuego |
| Assets firmados de Planetary Computer caducan | `planetary_computer.sign()` en cada ejecución; nada de URLs cacheadas |
| No terminar antes de septiembre | El alcance ya es el mínimo con historia completa; si aprieta, cae primero el tooltip de °C, luego el selector de fechas — nunca el comparador |

## 10. Fases (GSD)

- **001-pipeline**: scripts 1–3 funcionando, figuras estáticas generadas, invariantes pasando.
- **002-export-y-web**: script 4, página `/labs/incendio` en el portfolio.
- **003-publicacion**: post MDX, README final, repo a público, deploy.
