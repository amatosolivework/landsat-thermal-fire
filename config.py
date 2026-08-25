"""Single source of truth for the La Mierla fire analysis.

Fire chronology (press-verified, 2026-08-25):
  - Detected 2026-07-16 13:55 local by a fire lookout (CMM: cmmedia.es
    "Última hora del incendio de La Mierla"). Spread NE through the
    Sierra Norte de Guadalajara.
  - Declared controlled 2026-08-03 after ~35,268 ha (vozpopuli / CMM).
  - Largest Spanish wildfire of 2026 (eldiario.es, moncloa.com, Aug 2026).
"""

# --- Area of interest (WGS84 lon/lat) --------------------------------------
# The fire ran ~60 km NE from La Mierla towards Atienza before control; the
# first, narrower AOI captured only its SW tail (dNBR 6.2 kha vs 35 kha
# official — caught by the pipeline invariant). Widened 2026-08-25.
AOI = (-3.55, 40.80, -2.70, 41.30)  # west, south, east, north

# NOTE: path 201 scenes do not cover the eastern part of this AOI; their
# windows are clipped to the scene footprint at ingestion and the missing
# area is NaN. dNBR (pre/post, both path 200) covers the full AOI.

# --- Common output grid -----------------------------------------------------
GRID_CRS = "EPSG:32630"  # UTM 30N
GRID_RES = 30            # metres

# --- Fire dates -------------------------------------------------------------
FIRE_START = "2026-07-16"
FIRE_CONTROLLED = "2026-08-03"
OFFICIAL_BURNED_HA = 35_268  # at control date; press figure, see docstring

# --- STAC -------------------------------------------------------------------
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "landsat-c2-l2"

# --- Scenes (all path 200/201, row 032 — row 032 fully covers the AOI) -----
# Verified <30% cloud against Planetary Computer on 2026-08-25.
# role: baseline  -> thermal-only, feeds the per-pixel z-score statistics
#       pre       -> last clean scene before ignition (also dNBR "pre")
#       during    -> fire active (Jul 16 – Aug 3)
#       post      -> after control (dNBR "post"; same path/row as "pre"
#                    on purpose, for geometric consistency)
SCENES = {
    "LC08_L2SP_201032_20260603_02_T1": "baseline",  # Jun 03, 0.1% cloud
    "LC09_L2SP_201032_20260611_02_T1": "baseline",  # Jun 11, 0.1%
    "LC08_L2SP_200032_20260612_02_T1": "baseline",  # Jun 12, 0.2%
    "LC09_L2SP_201032_20260627_02_T1": "baseline",  # Jun 27, 7.3%
    "LC08_L2SP_201032_20260705_02_T1": "baseline",  # Jul 05, 0.1%
    "LC09_L2SP_200032_20260706_02_T1": "baseline",  # Jul 06, 0.8%
    "LC09_L2SP_201032_20260713_02_T1": "baseline",  # Jul 13, 5.3%
    "LC08_L2SP_200032_20260714_02_T1": "pre",       # Jul 14, 0.0% — 2 days before ignition
    "LC08_L2SP_201032_20260721_02_T1": "during",    # Jul 21, 1.7% — fire day 5
    "LC09_L2SP_201032_20260729_02_T1": "during",    # Jul 29, 0.0% — fire day 13
    "LC08_L2SP_200032_20260730_02_T1": "during",    # Jul 30, 0.0% — fire day 14
    "LC09_L2SP_200032_20260807_02_T1": "post",      # Aug 07, 0.4% — 4 days after control
}

# Bands per role. Thermal + QA always; optical only where we tell the story.
BANDS_THERMAL = ["lwir11", "qa_pixel"]                     # ST_B10, QA_PIXEL
BANDS_OPTICAL = ["red", "green", "blue", "nir08", "swir22"]  # SR_B4/B3/B2/B5/B7
BANDS_BY_ROLE = {
    "baseline": BANDS_THERMAL,
    "pre":      BANDS_THERMAL + BANDS_OPTICAL,
    "during":   BANDS_THERMAL + BANDS_OPTICAL,
    "post":     BANDS_THERMAL + BANDS_OPTICAL,
}

# --- Landsat Collection 2 Level-2 constants --------------------------------
LST_SCALE, LST_OFFSET = 0.00341802, 149.0   # ST_B10 DN -> Kelvin
SR_SCALE, SR_OFFSET = 0.0000275, -0.2       # SR bands DN -> reflectance
# QA_PIXEL bits to mask: dilated cloud, cirrus, cloud, cloud shadow
QA_MASK_BITS = (1, 2, 3, 4)

# --- Analysis thresholds ----------------------------------------------------
ZSCORE_THRESHOLD = 3.0
DNBR_CLASSES = {          # USGS burn severity, lower bounds
    "high":          0.66,
    "moderate_high": 0.44,
    "moderate_low":  0.27,
    "low":           0.10,
}
DNBR_BURNED_MIN = 0.27    # "burned" for the official-figure comparison

# --- Physical sanity bounds (pipeline aborts outside these) ----------------
LST_VALID_C = (-20.0, 90.0)   # masked LST outside fire must stay in range
HA_TOLERANCE = (0.3, 3.0)     # detected/official ratio, order of magnitude

# --- Paths ------------------------------------------------------------------
from pathlib import Path
ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"
DATA_DERIVED = ROOT / "data" / "derived"
FIGURAS = ROOT / "figuras"
