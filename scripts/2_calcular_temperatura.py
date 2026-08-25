"""Turn raw AOI windows into analysis-ready rasters on a common grid.

Per scene:
  lst_<date>_<role>_raw.tif     LST in °C, no mask (smoke is often QA-flagged
                                as cloud; during a fire the unmasked band IS
                                the signal, so we always keep it)
  lst_<date>_<role>_masked.tif  LST in °C, cloud/shadow masked to NaN
  rgb_<date>_<role>.tif         surface reflectance RGB (optical roles only)
  nbr_<date>_<role>.tif         (NIR-SWIR2)/(NIR+SWIR2) (optical roles only)

All outputs share one grid: EPSG:32630, 30 m, snapped to the AOI. The pipeline
aborts loudly if any physical invariant fails.
"""

import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject, transform_bounds

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

NODATA = float("nan")


def build_grid() -> dict:
    """Common target grid: AOI bounds in UTM 30N snapped to 30 m."""
    w, s, e, n = transform_bounds("EPSG:4326", config.GRID_CRS, *config.AOI)
    res = config.GRID_RES
    w, s = np.floor(w / res) * res, np.floor(s / res) * res
    e, n = np.ceil(e / res) * res, np.ceil(n / res) * res
    width, height = round((e - w) / res), round((n - s) / res)
    return {
        "crs": config.GRID_CRS,
        "transform": rasterio.transform.from_origin(w, n, res, res),
        "width": width,
        "height": height,
    }


def to_grid(path: Path, grid: dict, resampling: Resampling) -> np.ndarray:
    """Read a raw band and reproject it onto the common grid (float32, NaN out)."""
    with rasterio.open(path) as src:
        dest = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
        reproject(
            source=src.read(1).astype("float32"),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=0,  # Landsat C2 DN 0 = nodata for all bands we use
            dst_transform=grid["transform"],
            dst_crs=grid["crs"],
            dst_nodata=np.nan,
            resampling=resampling,
        )
    return dest


def write(path: Path, data: np.ndarray, grid: dict, count: int = 1) -> None:
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": count,
        "crs": grid["crs"],
        "transform": grid["transform"],
        "width": grid["width"],
        "height": grid["height"],
        "nodata": NODATA,
        "compress": "deflate",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data if data.ndim == 3 else data[np.newaxis, :, :])


def qa_cloud_mask(qa: np.ndarray) -> np.ndarray:
    """True where QA_PIXEL flags dilated cloud / cirrus / cloud / shadow."""
    bits = np.nan_to_num(qa, nan=0).astype("uint16")
    mask = np.zeros(bits.shape, dtype=bool)
    for bit in config.QA_MASK_BITS:
        mask |= (bits >> bit) & 1 == 1
    return mask


def check(condition: bool, message: str) -> None:
    if not condition:
        sys.exit(f"INVARIANT FAILED: {message}")


def main() -> None:
    grid = build_grid()
    print(f"grid: {grid['width']}x{grid['height']} @ {config.GRID_RES} m "
          f"{config.GRID_CRS}", file=sys.stderr)
    shapes = set()

    for scene_id, role in config.SCENES.items():
        date = scene_id.split("_")[3]
        raw = config.DATA_RAW / scene_id
        out = config.DATA_DERIVED

        lst = to_grid(raw / "lwir11.tif", grid, Resampling.bilinear)
        lst = lst * config.LST_SCALE + config.LST_OFFSET - 273.15  # DN -> °C
        qa = to_grid(raw / "qa_pixel.tif", grid, Resampling.nearest)
        cloudy = qa_cloud_mask(qa)
        masked = np.where(cloudy, np.nan, lst)

        write(out / f"lst_{date}_{role}_raw.tif", lst, grid)
        write(out / f"lst_{date}_{role}_masked.tif", masked, grid)
        shapes.add(lst.shape)

        # --- physical invariants ------------------------------------------
        valid = masked[np.isfinite(masked)]
        check(valid.size > 0, f"{scene_id}: no valid pixels after masking")
        lo, hi = config.LST_VALID_C
        if role == "during":  # active fire may legitimately exceed the cap
            check(valid.min() > lo, f"{scene_id}: LST min {valid.min():.1f} < {lo}")
        else:
            check(lo < valid.min() and valid.max() < hi,
                  f"{scene_id}: LST range [{valid.min():.1f}, {valid.max():.1f}] "
                  f"outside [{lo}, {hi}]")
        pct_masked = 100 * cloudy.mean()
        print(f"{scene_id}  {role:8}  LST [{valid.min():6.1f}, {valid.max():6.1f}] °C"
              f"  masked {pct_masked:4.1f}%", file=sys.stderr)

        # --- optical products ---------------------------------------------
        if role in ("pre", "during", "post"):
            sr = {
                b: to_grid(raw / f"{b}.tif", grid, Resampling.bilinear)
                * config.SR_SCALE + config.SR_OFFSET
                for b in config.BANDS_OPTICAL
            }
            rgb = np.stack([sr["red"], sr["green"], sr["blue"]])
            write(out / f"rgb_{date}_{role}.tif", rgb, grid, count=3)
            nbr = (sr["nir08"] - sr["swir22"]) / (sr["nir08"] + sr["swir22"])
            write(out / f"nbr_{date}_{role}.tif", nbr, grid)
            # water mask (QA bit 7): dNBR over reservoirs is a classic false
            # positive — water must be excluded from burn severity downstream
            water = (np.nan_to_num(qa, nan=0).astype("uint16") >> 7) & 1
            write(out / f"water_{date}_{role}.tif", water.astype("float32"), grid)

    check(len(shapes) == 1, f"output grids differ: {shapes}")
    print("done — all invariants passed", file=sys.stderr)


if __name__ == "__main__":
    main()
