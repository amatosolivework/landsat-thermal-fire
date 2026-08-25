# landsat-thermal-fire

Thermal analysis of the **La Mierla wildfire** (Guadalajara, Spain — July 2026,
~35,000 ha, the largest Spanish fire of 2026) using open Landsat 8/9 data:
STAC ingestion, land surface temperature, per-pixel anomaly detection and
dNBR burn severity.

> Personal learning project: I built this to understand the Earth-observation
> thermal pipeline end to end. Landsat's thermal band is 100 m / ~8-day
> revisit per path; commercial thermal constellations operate at another
> level entirely. This maps the problem, not their product.

**Status:** phase 001 (pipeline) complete — see `figuras/`. Web viewer and
write-up in progress.

## What it shows

- The fire zone at **17σ** above each pixel's June–July thermal baseline.
- In optical imagery the fire is a subtle dark patch, easy to mistake for
  terrain shadows; **in thermal it is unmissable** (`figuras/b_*.png`).
- **Four days after the fire was declared controlled, the scar still radiates
  at ~60 °C** (`figuras/a_*.png`) — thermal persistence monitoring in action.
- dNBR burn severity: **20,530 ha** at moderate-low severity or above vs
  ~35,268 ha officially affected — the gap itself is informative (official
  figures count the total perimeter; dNBR ≥ 0.27 excludes low-severity and
  unburned islands). `data/derived/stats.json` has the breakdown.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/1_buscar_escenas.py      # ~41 MB: AOI windows read
.venv/bin/python scripts/2_calcular_temperatura.py #   from remote COGs via
.venv/bin/python scripts/3_detectar_anomalias.py   #   HTTP range requests
.venv/bin/python scripts/figuras.py
```

No credentials needed — scene search and data access go through
[Microsoft Planetary Computer](https://planetarycomputer.microsoft.com)'s
public STAC API. `config.py` is the single source of truth (AOI, scenes,
thresholds); every scene choice is annotated with its role and cloud cover.

The pipeline validates physical invariants at every step (LST ranges,
detected-vs-official area within order of magnitude, grid consistency) and
aborts loudly when one fails — in thermal remote sensing a wrong number
usually *looks* perfectly fine.

## Honest limitations

- Landsat ST is an L2 product: the USGS already applies emissivity and
  atmospheric correction. I consume it, I don't reimplement it.
- No smoke-penetration claim: none of the three during-fire morning
  acquisitions shows a dense plume over the front, so this dataset can't
  demonstrate it (and LWIR does not penetrate *cloud* at all).
- The eastern third of the area has only 2 baseline observations (path
  geometry), so the z-score map is restricted to where statistics are solid;
  full-extent area accounting relies on dNBR (same path/row pre & post).
- 30 m grid resamples a native 100 m thermal band — fine structure in the
  LST maps is interpolation, not information.
