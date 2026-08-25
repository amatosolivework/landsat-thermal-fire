# STATE — landsat-thermal-fire

**Actualizado:** 2026-08-25

## Qué es esto
Análisis térmico del incendio de La Mierla (Guadalajara, ago-2026) con Landsat 8/9,
como pieza de candidatura a prácticas en Aistech Space. Spec completo en
`docs/superpowers/specs/2026-08-25-landsat-thermal-fire-design.md` — leerlo antes de tocar nada.

## Estado actual
- Spec APROBADO por Alex (2026-08-25).
- Disponibilidad de escenas VERIFICADA contra Planetary Computer (36 escenas <30% nube,
  triplete antes/durante/después identificado — ver §2 del spec).
- Fase 001 PLANIFICADA: `.planning/phases/001-pipeline/001-01-PLAN.md` (T1–T7).
  Ejecución no empezada. Primera tarea: T1, confirmar cronología del incendio en prensa.

## Restricción de calendario
Todo publicado antes de la **primera semana de septiembre de 2026** (envío de mensajes
LinkedIn a Aistech; ver `Projects/Practicas UB/mensajes-aistech-sdg.md`).

## Decisiones tomadas (no reabrir sin motivo)
- Repo separado del portfolio; frontera = ficheros estáticos exportados a
  `portfolio/public/data/incendio/`. Sin backend.
- Demo estático, no mini-ALEX vivo. Caso: La Mierla (plan B: Larouco/Uña de Quintana 2025).
- No reimplementar corrección de emisividad: usar LST del producto USGS L2 y explicarlo.
- Repo privado hasta que el README esté terminado; público en fase 003.

## Próximo paso
Ejecutar fase 001 siguiendo el plan, T1 → T7 en orden. El criterio que decide todo
está en T6-(b): si la figura RGB-vs-térmico del 14-ago no muestra el frente a través
del humo, parar y activar el plan B del spec antes de tocar la fase 002.
