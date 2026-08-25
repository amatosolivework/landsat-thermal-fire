# SUMMARY 001-01 — pipeline

**Fase completada:** 2026-08-25 · **Gate T6-(b): PASADO** (con reencuadre de la tesis)

## Resultados

- 12 escenas ingeridas (7 baseline, 1 pre, 3 during, 1 post), 41 MB vía lectura
  de ventanas AOI sobre COGs remotos (desviación del plan: no se bajan escenas
  completas — mejor, y demuestra COG en el código).
- LST °C en grid común 32630/30 m; invariantes físicos OK en las 12.
- z-score: máx **17,1σ** (21-jul). Anomalía unión 11.834 ha.
- dNBR (14-jul vs 7-ago, mismo path/row, agua enmascarada): **20.530 ha**
  ≥ moderate-low vs 35.268 oficiales (ratio 0,58, explicado en stats.json).
- 9 figuras en `figuras/`; la clave es la secuencia antes/durante/después y el
  zoom RGB-vs-térmico.

## Desviaciones del plan

1. **Cronología real ≠ estimada** (T1): fuego 16-jul → 3-ago, no 9-12 ago.
   Escenas reasignadas por completo. La tarea T1 existía exactamente para esto.
2. **AOI ampliada** tras fallo (correcto) del invariante de hectáreas: el fuego
   corrió ~60 km NE hacia Atienza; la caja inicial solo veía la cola SW
   (6.155 ha). Nueva AOI [-3.55, 40.80, -2.70, 41.30]; ingesta con clipping de
   ventana al footprint de escena.
3. **La tesis del humo NO se sostiene** con estas adquisiciones (pasadas
   matinales, sin pluma densa visible). Historia reencuadrada a: "en óptico el
   fuego es una mancha sutil; en térmico es inconfundible a 17σ, y la cicatriz
   sigue a ~60 °C cuatro días después del control". **Los mensajes de LinkedIn
   (`Practicas UB/mensajes-aistech-sdg.md`) deben revisarse**: quitar "ver a
   través del humo" y "corrigiendo por emisividad".
4. Agua enmascarada en dNBR (bit 7 QA) tras detectar embalses como falsos
   positivos "high severity".
5. Invariante de baseline usable relajado a >45% (geometría de paths en la AOI
   ampliada); documentado en código y README.

## Pendiente que hereda la fase 002

- Export web (script 4) + página `/labs/incendio` en el portfolio.
- Verificación completa de regeneración desde cero (`rm -rf data/` + 4 scripts)
  hecha una vez durante el debugging de la AOI — repetir al cierre de 003 si
  cambia algo del pipeline.
