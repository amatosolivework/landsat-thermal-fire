"""Fetch the AOI window of every configured Landsat scene from Planetary Computer.

Instead of downloading full scenes (~500 MB each), this reads only the AOI
window from the remote Cloud-Optimized GeoTIFFs via HTTP range requests and
writes small local GeoTIFFs to data/raw/<scene_id>/<band>.tif.

Idempotent: existing non-empty outputs are skipped. Asset URLs are signed on
every run (Planetary Computer signatures expire — never cache them).
"""

import sys
from pathlib import Path

import planetary_computer
import pystac_client
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def fetch_band(href: str, out_path: Path) -> str:
    """Read the AOI window from a remote COG and write it locally."""
    if out_path.exists() and out_path.stat().st_size > 0:
        return "skip"
    with rasterio.open(href) as src:
        bounds = transform_bounds("EPSG:4326", src.crs, *config.AOI)
        window = from_bounds(*bounds, transform=src.transform)
        # the AOI may exceed the scene footprint (path 201 vs the eastern
        # AOI): clip the window to the raster, keep what overlaps
        full = rasterio.windows.Window(0, 0, src.width, src.height)
        window = window.intersection(full).round_offsets().round_lengths()
        if window.width <= 0 or window.height <= 0:
            return "no-overlap"
        data = src.read(1, window=window)
        transform = src.window_transform(window)
        profile = src.profile | {
            "height": data.shape[0],
            "width": data.shape[1],
            "transform": transform,
            "driver": "GTiff",
            "compress": "deflate",
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.tif")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(data, 1)
    tmp.rename(out_path)  # atomic-ish: no half-written files count as done
    return "fetched"


def main() -> None:
    catalog = pystac_client.Client.open(
        config.STAC_URL, modifier=planetary_computer.sign_inplace
    )
    ids = list(config.SCENES)
    items = {
        item.id: item
        for item in catalog.search(collections=[config.COLLECTION], ids=ids).items()
    }
    missing = set(ids) - set(items)
    if missing:
        sys.exit(f"ERROR: scenes not found in catalog: {sorted(missing)}")

    for scene_id, role in config.SCENES.items():
        item = items[scene_id]
        for band in config.BANDS_BY_ROLE[role]:
            if band not in item.assets:
                sys.exit(
                    f"ERROR: asset '{band}' missing in {scene_id}. "
                    f"Available: {sorted(item.assets)}"
                )
            out = config.DATA_RAW / scene_id / f"{band}.tif"
            status = fetch_band(item.assets[band].href, out)
            print(f"{status:>7}  {scene_id}  {band}", file=sys.stderr)

    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
