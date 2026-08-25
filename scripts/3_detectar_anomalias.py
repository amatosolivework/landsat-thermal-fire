"""Detect the fire: per-pixel thermal z-scores and dNBR burn severity.

Outputs (data/derived/):
  baseline_mean.tif / baseline_std.tif   per-pixel LST stats, Jun-Jul scenes
  zscore_<date>.tif                      (LST - mean) / std, during scenes
  anomaly_<date>.tif                     z > threshold, 1/0
  dnbr.tif                               NBR_pre - NBR_post
  dnbr_class.tif                         USGS severity class (0-4)
  stats.json                             the numbers the story hangs on
"""

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

D = config.DATA_DERIVED


def read(name: str) -> np.ndarray:
    with rasterio.open(D / name) as src:
        return src.read(1)


def write_like(name: str, data: np.ndarray) -> None:
    with rasterio.open(D / next(iter(sorted(D.glob("lst_*_raw.tif")))).name) as ref:
        profile = ref.profile
    with rasterio.open(D / name, "w", **profile) as dst:
        dst.write(data.astype("float32"), 1)


def check(condition: bool, message: str) -> None:
    if not condition:
        sys.exit(f"INVARIANT FAILED: {message}")


def scenes_by_role(role: str) -> list[tuple[str, str]]:
    """[(date, scene_id)] for a role, in date order."""
    pairs = [(s.split("_")[3], s) for s, r in config.SCENES.items() if r == role]
    return sorted(pairs)


def main() -> None:
    px_ha = (config.GRID_RES ** 2) / 10_000  # 30 m px -> 0.09 ha

    # --- per-pixel baseline statistics (masked LST: clouds must not pollute) --
    stack = np.stack(
        [read(f"lst_{d}_baseline_masked.tif") for d, _ in scenes_by_role("baseline")]
    )
    n_valid = np.isfinite(stack).sum(axis=0)
    with np.errstate(invalid="ignore"):  # all-NaN pixels are expected off-footprint
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(stack, axis=0)
            std = np.nanstd(stack, axis=0)
    # pixels with <3 clean observations or degenerate std are unusable.
    # Most baseline scenes are path 201, which does not reach the eastern AOI:
    # the z-score map is only computed where the statistics are solid, and the
    # full-extent hectare comparison is carried by dNBR (path 200 pre/post).
    usable = (n_valid >= 3) & (std > 0.5)
    mean[~usable], std[~usable] = np.nan, np.nan
    write_like("baseline_mean.tif", mean)
    write_like("baseline_std.tif", std)
    check(usable.mean() > 0.45, f"only {usable.mean():.0%} of pixels have a usable baseline")

    # --- z-scores (RAW lst: smoke may be QA-flagged) -------------------------
    # during scenes drive the anomaly accounting; pre/post get a z raster too
    # so the web overlay can fade to transparent wherever nothing is anomalous
    anomaly_union = np.zeros(mean.shape, dtype=bool)
    z_stats = {}
    for role in ("pre", "during", "post"):
        for date, _ in scenes_by_role(role):
            lst = read(f"lst_{date}_{role}_raw.tif")
            z = (lst - mean) / std
            write_like(f"zscore_{date}.tif", z)
            if role != "during":
                continue
            anomaly = np.where(np.isfinite(z), z > config.ZSCORE_THRESHOLD, False)
            write_like(f"anomaly_{date}.tif", anomaly)
            anomaly_union |= anomaly
            z_stats[date] = {
                "anomaly_ha": round(float(anomaly.sum() * px_ha)),
                "z_max": round(float(np.nanmax(z)), 1),
                "lst_max_c": round(float(np.nanmax(lst)), 1),
            }
            print(f"during {date}: {z_stats[date]}", file=sys.stderr)

    # --- dNBR: pre (Jul 14) vs post (Aug 7), same path/row -------------------
    (pre_date, _), (post_date, _) = scenes_by_role("pre")[0], scenes_by_role("post")[0]
    dnbr = read(f"nbr_{pre_date}_pre.tif") - read(f"nbr_{post_date}_post.tif")
    # reservoirs produce spurious high dNBR — mask water out of severity
    water = (read(f"water_{pre_date}_pre.tif") > 0) | (
        read(f"water_{post_date}_post.tif") > 0)
    dnbr[water] = np.nan
    write_like("dnbr.tif", dnbr)

    classes = np.zeros(dnbr.shape, dtype="float32")  # 0 = unburned
    severity_ha = {}
    bounds = sorted(config.DNBR_CLASSES.items(), key=lambda kv: kv[1])
    for i, (label, lower) in enumerate(bounds, start=1):
        upper = bounds[i][1] if i < len(bounds) else np.inf
        in_class = np.isfinite(dnbr) & (dnbr >= lower) & (dnbr < upper)
        classes[in_class] = i
        severity_ha[label] = round(float(in_class.sum() * px_ha))
    write_like("dnbr_class.tif", classes)

    burned = np.isfinite(dnbr) & (dnbr >= config.DNBR_BURNED_MIN)
    burned_ha = float(burned.sum() * px_ha)
    ratio = burned_ha / config.OFFICIAL_BURNED_HA

    # --- invariants -----------------------------------------------------------
    lo, hi = config.HA_TOLERANCE
    check(lo <= ratio <= hi,
          f"burned {burned_ha:.0f} ha vs official {config.OFFICIAL_BURNED_HA} "
          f"(ratio {ratio:.2f} outside [{lo}, {hi}])")
    t_fire = max(s["lst_max_c"] for s in z_stats.values())
    t_base = float(np.nanmax(mean))
    check(t_fire > t_base, f"fire max {t_fire} not above baseline mean max {t_base}")

    stats = {
        "fire": {"start": config.FIRE_START, "controlled": config.FIRE_CONTROLLED,
                 "official_burned_ha": config.OFFICIAL_BURNED_HA,
                 "official_source": "CMM / Vozpópuli press, Aug 2026"},
        "detected": {
            "burned_ha_dnbr": round(burned_ha),
            "ratio_vs_official": round(ratio, 2),
            "severity_ha": severity_ha,
            "anomaly_union_ha": round(float(anomaly_union.sum() * px_ha)),
            "by_scene": z_stats,
        },
        "baseline": {"scenes": len(stack), "mean_max_c": round(t_base, 1),
                     "usable_pixels_pct": round(100 * float(usable.mean()), 1)},
        "grid": {"crs": config.GRID_CRS, "res_m": config.GRID_RES},
        "note": ("dNBR area includes only moderate-low severity and above "
                 "(dNBR >= 0.27); the official figure counts total affected "
                 "perimeter, so a detected/official ratio below 1 is expected."),
    }
    (D / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(json.dumps(stats["detected"] | {"official": config.OFFICIAL_BURNED_HA},
                     indent=2), file=sys.stderr)
    print("done — all invariants passed", file=sys.stderr)


if __name__ == "__main__":
    main()
