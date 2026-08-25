# STATE — landsat-thermal-fire

**Actualizado:** 2026-08-25

## Qué es esto
Análisis térmico del incendio de La Mierla (Guadalajara, ago-2026) con Landsat 8/9,
como pieza de candidatura a prácticas en Aistech Space. Spec completo en
`docs/superpowers/specs/2026-08-25-landsat-thermal-fire-design.md` — leerlo antes de tocar nada.

## Estado actual
- Spec APROBADO por Alex (2026-08-25).
- **Fase 001 COMPLETADA** (2026-08-25): pipeline entero funcionando, gate T6-(b)
  pasado. Ver `001-01-SUMMARY.md` — hay 5 desviaciones documentadas, las gordas:
  cronología real del fuego era 16-jul→3-ago (no agosto), AOI ampliada tras
  fallo correcto del invariante de ha, y la tesis del humo reencuadrada a
  "sutil en óptico / inconfundible en térmico + cicatriz caliente post-control".
- ⚠️ Los mensajes LinkedIn en `Practicas UB/mensajes-aistech-sdg.md` mencionan
  "ver a través del humo" y "corrigiendo por emisividad" — revisar antes de enviar.

## Restricción de calendario
Todo publicado antes de la **primera semana de septiembre de 2026** (envío de mensajes
LinkedIn a Aistech; ver `Projects/Practicas UB/mensajes-aistech-sdg.md`).

## Decisiones tomadas (no reabrir sin motivo)
- Repo separado del portfolio; frontera = ficheros estáticos exportados a
  `portfolio/public/data/incendio/`. Sin backend.
- Demo estático, no mini-ALEX vivo. Caso: La Mierla (plan B: Larouco/Uña de Quintana 2025).
- No reimplementar corrección de emisividad: usar LST del producto USGS L2 y explicarlo.
- Repo privado hasta que el README esté terminado; público en fase 003.

- **Fase 002 COMPLETADA** (2026-08-25): export 2,6 MB + página `/labs/incendio`
  funcionando y verificada en navegador (portfolio commit `edaf21a`).
- **Fase 003 COMPLETADA — PROYECTO CERRADO** (2026-08-25). Los tres enlaces
  vivos y verificados en producción:
  visor https://alexmatosolive.com/labs/incendio ·
  post https://alexmatosolive.com/blog/watching-a-wildfire-in-thermal ·
  repo https://github.com/amatosolivework/landsat-thermal-fire
  Mensajes LinkedIn actualizados con resultados reales (⚠️ resuelto).

## Próximo paso
Ninguno en este repo. Lo que queda es de la campaña de prácticas (fuera de este
repo): enviar los mensajes la primera semana de septiembre —
ver `Projects/Practicas UB/mensajes-aistech-sdg.md`.
