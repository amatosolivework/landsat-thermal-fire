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
LST_MIN, LST_MAX = 20.0, 65.0
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


def save_colormapped(data: np.ndarray, out: Path) -> None:
    norm = np.clip(np.nan_to_num(data, nan=LST_MIN) - LST_MIN, 0, LST_MAX - LST_MIN)
    rgba = (colormaps["magma"](norm / (LST_MAX - LST_MIN)) * 255).astype("uint8")
    rgba[..., 3] = np.where(np.isfinite(data), 255, 0)
    # palette-quantized PNG8: ~60% smaller than truecolor, no visible loss
    Image.fromarray(rgba).quantize(256, method=Image.Quantize.FASTOCTREE).save(
        out, optimize=True)


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
    for key, (fname, _) in LAYERS.items():
        lst, transform, _ = to_3857(D / fname)
        save_colormapped(lst, out / f"lst_{key}.png")
        save_values(lst, out / f"val_{key}.png")
        shapes.add(lst.shape)
        bounds = bounds_lonlat(transform, lst.shape)
        print(f"layer {key}: {lst.shape}", file=sys.stderr)

    dnbr, transform, _ = to_3857(D / "dnbr_class.tif")
    classes = np.round(np.nan_to_num(dnbr, nan=0)).astype("uint8")
    palette = np.array([[int(to_rgba(c)[i] * 255) for i in range(4)]
                        for c in DNBR_COLORS], dtype="uint8")
    Image.fromarray(palette[np.clip(classes, 0, 4)]).save(out / "dnbr.png", optimize=True)
    shapes.add(dnbr.shape)

    # comparator: crop of the burn scar (padded bbox), 21 Jul = fire day 5
    scar_rows, scar_cols = np.where(classes > 0)
    pr, pc = int(0.2 * np.ptp(scar_rows)), int(0.2 * np.ptp(scar_cols))
    sl = np.s_[max(scar_rows.min() - pr, 0):scar_rows.max() + pr,
               max(scar_cols.min() - pc, 0):scar_cols.max() + pc]
    rgb, _, _ = to_3857(D / "rgb_20260721_during.tif")
    lst21, _, _ = to_3857(D / "lst_20260721_during_raw.tif")
    save_rgb(rgb[:, sl[0], sl[1]], out / "comparator_rgb.png")
    save_colormapped(lst21[sl], out / "comparator_lst.png")

    stats = json.loads((D / "stats.json").read_text())
    meta = {
        "bounds": bounds,  # [w, s, e, n] lon/lat, identical for all layers
        "lst_scale": {"min": LST_MIN, "max": LST_MAX, "cmap": "magma"},
        "val_encoding": {"nodata": 0, "min": 1, "max": 255,
                         "lst_min": LST_MIN, "lst_max": LST_MAX},
        "layers": [{"key": k, "date": d, "role": k.rstrip("123")}
                   for k, (_, d) in LAYERS.items()],
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
