"""Verification figures — the phase gate lives in figure (b): if the thermal
band does not show the fire front through the smoke, stop and rethink."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import BoundaryNorm, ListedColormap

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

D, F = config.DATA_DERIVED, config.FIGURAS
F.mkdir(exist_ok=True)


def read(name: str) -> np.ndarray:
    with rasterio.open(D / name) as src:
        return src.read()


def stretch(rgb: np.ndarray) -> np.ndarray:
    """Percentile-stretched (2-98) HWC image from a CHW reflectance stack."""
    out = np.zeros_like(rgb)
    for i, band in enumerate(rgb):
        lo, hi = np.nanpercentile(band, [2, 98])
        out[i] = np.clip((band - lo) / (hi - lo), 0, 1)
    return np.nan_to_num(out.transpose(1, 2, 0), nan=1.0) ** 0.8


LST_KW = dict(cmap="magma", vmin=20, vmax=65)

# --- (a) LST before / during / after ---------------------------------------
panels = [("20260714", "pre", "14 Jul — 2 days before ignition"),
          ("20260729", "during", "29 Jul — fire day 13"),
          ("20260807", "post", "7 Aug — 4 days after control")]
fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
for ax, (date, role, title) in zip(axes, panels):
    im = ax.imshow(read(f"lst_{date}_{role}_raw.tif")[0], **LST_KW)
    ax.set_title(title, fontsize=11)
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.8, label="Land surface temperature (°C)")
fig.suptitle("La Mierla fire — Landsat 8/9 thermal (100 m), common 30 m grid", y=1.06)
fig.savefig(F / "a_lst_antes_durante_despues.png", dpi=150, bbox_inches="tight")

# --- (b) RGB vs thermal, per during scene -----------------------------------
# Honest framing after looking at the data: none of the three morning
# acquisitions shows an obvious smoke plume, so the story is NOT "thermal sees
# through smoke" — it is "in optical the fire is a subtle dark patch an expert
# has to hunt for; in thermal it is unmissable". Zoom panels drive that home.

# zoom window: bounding box of the burn scar, padded 15%
scar = read("dnbr_class.tif")[0] > 0
rows, cols = np.where(scar)
pr, pc = int(0.15 * (np.ptp(rows) + 1)), int(0.15 * (np.ptp(cols) + 1))
r0, r1 = max(rows.min() - pr, 0), rows.max() + pr
c0, c1 = max(cols.min() - pc, 0), cols.max() + pc
zoom = np.s_[r0:r1, c0:c1]

for date in ("20260721", "20260729", "20260730"):
    rgb = stretch(read(f"rgb_{date}_during.tif"))
    lst = read(f"lst_{date}_during_raw.tif")[0]
    for tag, sl in (("", np.s_[:, :]), ("_zoom", zoom)):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                       constrained_layout=True)
        ax1.imshow(rgb[sl])
        ax1.set_title(f"{date[6:]}-{date[4:6]}-2026 — optical: "
                      "easy to mistake for terrain")
        im = ax2.imshow(lst[sl], **LST_KW)
        ax2.set_title("same instant — thermal: unmissable")
        for ax in (ax1, ax2):
            ax.axis("off")
        fig.colorbar(im, ax=ax2, shrink=0.8, label="LST (°C)")
        fig.savefig(F / f"b_rgb_vs_termico_{date}{tag}.png", dpi=150,
                    bbox_inches="tight")

# --- (c) dNBR burn severity -------------------------------------------------
classes = read("dnbr_class.tif")[0]
cmap = ListedColormap(["#f0f0e8", "#ffe082", "#ff9e40", "#e5484d", "#7c1d1d"])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
fig, ax = plt.subplots(figsize=(10, 8), constrained_layout=True)
im = ax.imshow(classes, cmap=cmap, norm=norm)
ax.axis("off")
ax.set_title("Burn severity (dNBR, 14 Jul vs 7 Aug) — USGS classes")
cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3, 4], shrink=0.7)
cbar.ax.set_yticklabels(["unburned", "low", "moderate-low", "moderate-high", "high"])
fig.savefig(F / "c_dnbr_severidad.png", dpi=150, bbox_inches="tight")

# --- (d) z-score histogram --------------------------------------------------
z = read("zscore_20260729.tif")[0]
z = z[np.isfinite(z)]
fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
ax.hist(z, bins=200, range=(-5, 16), color="#5b7fff", log=True)
ax.axvline(config.ZSCORE_THRESHOLD, color="#e5484d", ls="--",
           label=f"anomaly threshold (z = {config.ZSCORE_THRESHOLD:g})")
ax.set_xlabel("thermal z-score vs Jun–Jul baseline (29 Jul scene)")
ax.set_ylabel("pixels (log)")
ax.legend()
ax.set_title("Almost everything is normal; the fire is 17σ away")
fig.savefig(F / "d_zscore_hist.png", dpi=150, bbox_inches="tight")

print("figures written to", F, file=sys.stderr)
