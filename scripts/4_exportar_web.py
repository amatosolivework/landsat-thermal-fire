"""Export web-ready assets to the portfolio repo.

Everything the /labs/incendio page needs, as static files:
  lst_<key>.png      colormapped LST (magma, fixed 20-65 °C), EPSG:3857
  val_<key>.png      8-bit value-encoded LST for the tooltip
                     (0 = nodata, 1-255 maps linearly to 20-65 °C)
  dnbr.png           classified burn severity, unburned transparent
  comparator_*.png   RGB vs LST crop of the burn scar (21 Jul, fire day 5)
  meta.json          lon/lat bounds, dates, legend, stats

Rasters are reprojected to EPSG:3857 so a MapLibre image source (linear in
mercator) aligns exactly, then downsampled 2x for the web.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from matplotlib import colormaps
from matplotlib.colors import to_rgba
from PIL import Image
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

D = config.DATA_DERIVED
LST_MIN, LST_MAX = 20.0, 65.0   # value-encoding + comparator scale
MAP_VMIN = 35.0                 # map layers: only anomalies are visible,
                                # keep them in the warm part of the ramp
DOWNSAMPLE = 2

LAYERS = {  # key -> (derived file, date label)
    "pre":      ("lst_20260714_pre_raw.tif", "2026-07-14"),
    "during1":  ("lst_20260721_during_raw.tif", "2026-07-21"),
    "during2":  ("lst_20260729_during_raw.tif", "2026-07-29"),
    "during3":  ("lst_20260730_during_raw.tif", "2026-07-30"),
    "post":     ("lst_20260807_post_raw.tif", "2026-08-07"),
}
DNBR_COLORS = ["#00000000", "#ffe082", "#ff9e40", "#e5484d", "#7c1d1d"]


def to_3857(path: Path) -> tuple[np.ndarray, rasterio.Affine, str]:
    """Reproject a derived raster to EPSG:3857, downsampled for the web."""
    with rasterio.open(path) as src:
        transform, w, h = calculate_default_transform(
            src.crs, "EPSG:3857", src.width, src.height, *src.bounds,
            dst_width=src.width // DOWNSAMPLE, dst_height=src.height // DOWNSAMPLE,
        )
        count = src.count
        dest = np.full((count, h, w), np.nan, dtype="float32")
        reproject(
            source=src.read().astype("float32"), destination=dest,
            src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
            dst_transform=transform, dst_crs="EPSG:3857", dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return (dest[0] if count == 1 else dest), transform, "EPSG:3857"


def bounds_lonlat(transform: rasterio.Affine, shape: tuple[int, int]) -> list:
    h, w = shape
    left, top = transform * (0, 0)
    right, bottom = transform * (w, h)
    w_, s, e, n = transform_bounds("EPSG:3857", "EPSG:4326", left, bottom, right, top)
    return [round(v, 6) for v in (w_, s, e, n)]


def save_colormapped(data: np.ndarray, out: Path,
                     alpha: np.ndarray | None = None,
                     vmin: float = LST_MIN, cmap: str = "magma") -> None:
    """Colormapped PNG. With `alpha` (0-1), thermally normal terrain fades
    out and the overlay reads as an organic heat blob on the basemap instead
    of a pasted scene-footprint trapezoid. Map layers use YlOrRd on a
    narrower scale: it starts light and warm, so even the coolest visible
    anomaly reads as heat on a light basemap (magma starts near black and
    reads as ink stains there); the comparator keeps magma's full drama."""
    norm = np.clip(np.nan_to_num(data, nan=vmin) - vmin, 0, LST_MAX - vmin)
    rgba = (colormaps[cmap](norm / (LST_MAX - vmin)) * 255).astype("uint8")
    if alpha is None:
        rgba[..., 3] = np.where(np.isfinite(data), 255, 0)
    else:
        a = np.where(np.isfinite(data), np.nan_to_num(alpha, nan=0.0), 0.0)
        rgba[..., 3] = (np.clip(a, 0, 1) * 255).astype("uint8")
    # palette-quantized PNG8: ~60% smaller than truecolor, no visible loss
    Image.fromarray(rgba).quantize(256, method=Image.Quantize.FASTOCTREE).save(
        out, optimize=True)


def anomaly_alpha(z: np.ndarray) -> np.ndarray:
    """Opacity ramp on the thermal z-score: invisible below 2σ, fully
    visible from 5σ. Slightly smoothstepped so edges feather naturally."""
    t = np.clip((z - 2.0) / 3.0, 0, 1)
    return (t * t * (3 - 2 * t)) * 0.92


def save_values(data: np.ndarray, out: Path) -> None:
    scaled = 1 + np.clip((data - LST_MIN) / (LST_MAX - LST_MIN), 0, 1) * 254
    vals = np.where(np.isfinite(data), scaled, 0).astype("uint8")
    Image.fromarray(vals, mode="L").save(out, optimize=True)


def save_rgb(chw: np.ndarray, out: Path) -> None:
    img = np.zeros((*chw.shape[1:], 4), dtype="uint8")
    for i in range(3):
        band = chw[i]
        lo, hi = np.nanpercentile(band, [2, 98])
        stretched = np.clip(np.nan_to_num(band, nan=lo) - lo, 0, hi - lo) / (hi - lo)
        img[..., i] = (stretched ** 0.8 * 255).astype("uint8")
    img[..., 3] = np.where(np.isfinite(chw[0]), 255, 0)
    Image.fromarray(img).quantize(256, method=Image.Quantize.FASTOCTREE).save(
        out, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).parent.parent.parent
                        / "portfolio" / "public" / "data" / "incendio")
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)

    shapes, bounds = set(), None
    for key, (fname, date_label) in LAYERS.items():
        lst, transform, _ = to_3857(D / fname)
        date = date_label.replace("-", "")
        z, _, _ = to_3857(D / f"zscore_{date}.tif")
        save_colormapped(lst, out / f"lst_{key}.png", alpha=anomaly_alpha(z),
                         vmin=MAP_VMIN, cmap="YlOrRd")
        save_values(lst, out / f"val_{key}.png")
        shapes.add(lst.shape)
        bounds = bounds_lonlat(transform, lst.shape)
        print(f"layer {key}: {lst.shape}  visible px: "
              f"{(anomaly_alpha(z) > 0.05).mean():.1%}", file=sys.stderr)

    dnbr, transform, _ = to_3857(D / "dnbr_class.tif")
    classes = np.round(np.nan_to_num(dnbr, nan=0)).astype("uint8")
    palette = np.array([[int(to_rgba(c)[i] * 255) for i in range(4)]
                        for c in DNBR_COLORS], dtype="uint8")
    Image.fromarray(palette[np.clip(classes, 0, 4)]).save(out / "dnbr.png", optimize=True)
    shapes.add(dnbr.shape)

    # comparator: tight crop of the burn scar. The during scene is chosen
    # automatically: path-201 scenes have their footprint diagonal crossing
    # the crop (a big white wedge in the image), so prefer whichever fire-day
    # scene covers the crop completely, and among those the earliest.
    scar_rows, scar_cols = np.where(classes > 0)
    pr, pc = int(0.12 * np.ptp(scar_rows)), int(0.12 * np.ptp(scar_cols))
    sl = np.s_[max(scar_rows.min() - pr, 0):scar_rows.max() + pr,
               max(scar_cols.min() - pc, 0):scar_cols.max() + pc]
    candidates = []
    for date in ("20260721", "20260729", "20260730"):
        rgb, _, _ = to_3857(D / f"rgb_{date}_during.tif")
        coverage = float(np.isfinite(rgb[0][sl]).mean())
        candidates.append((date, coverage, rgb))
    full = [c for c in candidates if c[1] > 0.999]
    date, coverage, rgb = full[0] if full else max(candidates, key=lambda c: c[1])
    # no scene covers the scar bbox completely (the westmost tail falls off
    # the path-200 footprint): trim the crop to the largest run of fully
    # valid columns/rows so the hero image has no white footprint wedge
    finite = np.isfinite(rgb[0][sl])
    col_ok = np.flatnonzero(finite.mean(axis=0) > 0.995)
    row_ok = np.flatnonzero(finite[:, col_ok[0]:col_ok[-1] + 1].mean(axis=1) > 0.995)
    sl = np.s_[sl[0].start + row_ok[0]:sl[0].start + row_ok[-1] + 1,
               sl[1].start + col_ok[0]:sl[1].start + col_ok[-1] + 1]
    # the scar runs SW->NE so the trimmed crop is very tall; frame the main
    # fire mass instead: window of ~1.05x the width, centred on the scar's
    # burned-pixel row centroid, so the hero image stays close to square
    h, w_px = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    target_h = int(1.05 * w_px)
    if h > target_h:
        scar_in = classes[sl] > 0
        centroid = int(np.round(np.average(np.arange(h),
                                           weights=scar_in.sum(axis=1) + 1e-6)))
        top = min(max(centroid - target_h // 2, 0), h - target_h)
        sl = np.s_[sl[0].start + top:sl[0].start + top + target_h, sl[1]]
    print(f"comparator: {date} (raw coverage {coverage:.1%}, framed to "
          f"{(sl[0].stop - sl[0].start)}x{(sl[1].stop - sl[1].start)} px)",
          file=sys.stderr)
    lst_cmp, _, _ = to_3857(D / f"lst_{date}_during_raw.tif")
    save_rgb(rgb[:, sl[0], sl[1]], out / "comparator_rgb.png")
    save_colormapped(lst_cmp[sl], out / "comparator_lst.png")
    from datetime import date as date_cls
    d = date_cls(int(date[:4]), int(date[4:6]), int(date[6:]))
    fire_day = (d - date_cls(*map(int, config.FIRE_START.split("-")))).days + 1
    comparator_meta = {"date": d.isoformat(), "fire_day": fire_day}

    stats = json.loads((D / "stats.json").read_text())
    meta = {
        "bounds": bounds,  # [w, s, e, n] lon/lat, identical for all layers
        "lst_scale": {"min": LST_MIN, "max": LST_MAX, "cmap": "magma"},
        "val_encoding": {"nodata": 0, "min": 1, "max": 255,
                         "lst_min": LST_MIN, "lst_max": LST_MAX},
        "layers": [{"key": k, "date": d, "role": k.rstrip("123")}
                   for k, (_, d) in LAYERS.items()],
        "comparator": comparator_meta,
        "dnbr_legend": [
            {"label": "low", "color": DNBR_COLORS[1]},
            {"label": "moderate-low", "color": DNBR_COLORS[2]},
            {"label": "moderate-high", "color": DNBR_COLORS[3]},
            {"label": "high", "color": DNBR_COLORS[4]},
        ],
        "stats": stats,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    # invariants
    total_mb = sum(f.stat().st_size for f in out.iterdir()) / 1e6
    assert len(shapes) == 1, f"layer shapes differ: {shapes}"
    assert total_mb < 6, f"export too heavy: {total_mb:.1f} MB"
    print(f"exported to {out} — {total_mb:.1f} MB total", file=sys.stderr)


if __name__ == "__main__":
    main()
