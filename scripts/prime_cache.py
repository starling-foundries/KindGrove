#!/usr/bin/env python3
"""Populate data_cache/temporal/<site>/ without the notebook UI.

Same search, thresholds and cache layout as mangrove_workflow_marimo.py's "Load Temporal Data"
cell, so the notebooks find the scenes instantly afterwards. Usage:

    uv run python scripts/prime_cache.py "Can Gio Biosphere Reserve" [--max-cloud 30]
"""
from __future__ import annotations

import argparse
import json
import sys
import shutil
import warnings
from datetime import datetime
from pathlib import Path

import burin_core as bc
import numpy as np
import rioxarray
import stackstac

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the repo root, for earthsearch
import earthsearch as es  # noqa: E402
import xarray as xr
from pystac_client import Client

warnings.filterwarnings("ignore")

STUDY_SITES = {
    "Thor Heyerdahl Climate Park": {"west": 94.462, "east": 94.502, "south": 17.044, "north": 17.082},
    "Can Gio Biosphere Reserve": {"west": 106.73, "east": 107.05, "south": 10.35, "north": 10.68},
    "Sundarbans": {"west": 89.325, "east": 89.595, "south": 21.865, "north": 22.135},
    "Wunbaik Reserved Forest": {"west": 94.3, "east": 94.7, "south": 16.6, "north": 16.9},
}
RANK_RESOLUTION = 8  # 3.5 km cells: enough to rank scene footprints against a bbox before any download


def rank_by_coverage(items, aoi_tree):
    """Candidates ordered by how much of the study area their STAC footprint covers (in 5% steps),
    then by cloud cover. This is the 2025 report's first recommendation, "filter scenes by bbox
    overlap percentage before download", done from catalog geometry alone: no pixels are read."""
    index = bc.Index()
    for it in items:
        index.add(it.id, bc.Tree.from_geojson(it.geometry, RANK_RESOLUTION))
    fraction = {h["key"]: h["fraction_of_query"] for h in index.query(aoi_tree)}
    ranked = [(fraction.get(it.id, 0.0), it) for it in items if fraction.get(it.id, 0.0) > 0.0]
    ranked.sort(key=lambda fi: (-round(fi[0] * 20) / 20, fi[1].properties.get("eo:cloud_cover", 100)))
    return ranked


TIME_WINDOWS = [
    ("Initial (2017)", "2017-01-01", "2017-12-31"),
    ("Pre-Cyclone Amphan", "2020-05-01", "2020-05-19"),
    ("Post-Cyclone Amphan", "2020-06-05", "2020-12-31"),
    ("Current (2024)", "2024-01-01", "2024-12-31"),
]


def boa_shift(item) -> float:
    """Reflectance shift that undoes a doubly applied BOA offset.

    Processing baseline >= 04.00 (Jan 2022) added a +1000 offset to L2A pixel values, declared
    in STAC `raster:bands` as offset -0.1 at scale 0.0001. Earth Search re-delivers those scenes
    with the offset already removed (`earthsearch:boa_offset_applied: true`) but keeps the
    declaration, and stackstac's rescale applies it again, so red reflectance comes out negative
    and NDVI overshoots. Adding the offset back recovers reflectance; older scenes need nothing."""
    if not item.properties.get("earthsearch:boa_offset_applied"):
        return 0.0
    band = item.assets["red"].extra_fields.get("raster:bands", [{}])[0]
    return -float(band.get("offset", 0.0))


def process(item, bbox, scene_dir: Path) -> dict | None:
    scene_dir.mkdir(parents=True, exist_ok=True)
    files = {b: scene_dir / f"{b}.tif" for b in ("red", "green", "nir")}
    if all(f.exists() for f in files.values()):
        bands = {b: rioxarray.open_rasterio(f).values[0] for b, f in files.items()}
    else:
        data = stackstac.stack([item], assets=["red", "green", "nir"], epsg=4326, resolution=0.0005,
                               bounds_latlon=bbox, chunksize=(1, 1, 512, 512), gdal_env=es.GDAL_ENV).compute()
        bands = {}
        for b in ("red", "green", "nir"):
            band = data.sel(band=b)
            if "time" in band.dims:
                band = band.isel(time=0)
            bands[b] = band.values
            band.rio.write_crs("EPSG:4326").rio.to_raster(files[b], compress="lzw")
    shift = boa_shift(item)
    if shift:
        bands = {b: np.where(np.isnan(v), np.nan, v + shift) for b, v in bands.items()}
    valid_pct = np.sum(~np.isnan(bands["nir"])) / bands["nir"].size
    if valid_pct < 0.01:
        shutil.rmtree(scene_dir, ignore_errors=True)
        return None
    ndvi = (bands["nir"] - bands["red"]) / (bands["nir"] + bands["red"] + 1e-8)
    mask = (ndvi > 0.4) & (ndvi < 0.95)
    biomass = np.maximum(np.where(mask, 250.5 * ndvi - 75.2, np.nan), 0)
    valid = biomass[~np.isnan(biomass)]
    ha = 0.25
    n_valid = int(np.sum(~np.isnan(bands["nir"])))
    n_mang = int(np.sum(mask))
    sample = {
        "date": item.datetime.isoformat(), "scene_id": item.id, "cloud_cover": item.properties.get("eo:cloud_cover", 0),
        "valid_coverage_ha": n_valid * ha, "valid_coverage_pct": float(valid_pct * 100), "boa_shift": shift,
        "biomass_mean": float(np.mean(valid)) if valid.size else 0, "biomass_std": float(np.std(valid)) if valid.size else 0,
        "mangrove_area_ha": n_mang * ha, "mangrove_fraction": (n_mang / n_valid * 100) if n_valid else 0,
        "carbon_stock": float(np.sum(valid) * ha * 0.47) if valid.size else 0,
        "carbon_density": float(np.mean(valid) * 0.47) if valid.size else 0,
    }
    (scene_dir / "stats.json").write_text(json.dumps(sample))
    # the raster the notebooks display; georeferenced like the bands so its footprint can be polygonised
    with rioxarray.open_rasterio(files["nir"]) as ref:
        xr.DataArray(biomass, dims=["y", "x"], coords={"y": ref.y.values, "x": ref.x.values}).rio.write_crs("EPSG:4326").rio.to_raster(scene_dir / "biomass.tif", compress="lzw")
    return sample


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", choices=list(STUDY_SITES))
    ap.add_argument("--max-cloud", type=int, default=30)
    ap.add_argument("--rule", choices=["coverage", "cloud"], default="coverage",
                    help="coverage: footprint coverage of the bbox, then cloud (2026). cloud: cloud cover alone (the 2025 loader)")
    ap.add_argument("--out", default="temporal", help="directory under data_cache/ (use temporal_2025 with --rule cloud)")
    args = ap.parse_args()
    b = STUDY_SITES[args.site]
    bbox = [b["west"], b["south"], b["east"], b["north"]]
    cache = Path("data_cache") / args.out / args.site.lower().replace(" ", "_")
    catalog = es.open_catalog()
    aoi = {"type": "Polygon", "coordinates": [[[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]]]}
    aoi_tree = bc.Tree.from_geojson(aoi, RANK_RESOLUTION)
    selection = {}
    for label, start, end in TIME_WINDOWS:
        items = list(catalog.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}/{end}",
                                    query={"eo:cloud_cover": {"lt": args.max_cloud}}, limit=40).items())
        ranked = rank_by_coverage(items, aoi_tree)
        if args.rule == "cloud":  # the 2025 rule: lowest cloud first, footprint ignored
            fractions = dict((item.id, f) for f, item in ranked)
            ranked = sorted(((fractions[i.id], i) for i in items), key=lambda t: t[1].properties.get("eo:cloud_cover", 0))
        print(f"{label}: {len(items)} candidates; best covers {100 * ranked[0][0]:.0f}% of the bbox" if ranked else f"{label}: no candidates", flush=True)
        for fraction, item in ranked[:5]:
            if (cache / item.id / "stats.json").exists():
                print(f"  cached {item.id}", flush=True)
                selection[label] = {"scene_id": item.id, "footprint_fraction": fraction}
                break
            try:
                s = es.with_deadline(lambda: process(item, bbox, cache / item.id))
            except Exception as e:  # noqa: BLE001 - a stalled or failed fetch: next candidate
                print(f"  {item.id}: could not be fetched ({type(e).__name__}: {str(e)[:120]}); next candidate", flush=True)
                continue
            if s:
                print(f"  {item.id}: footprint covers {100 * fraction:.0f}% of bbox, valid {s['valid_coverage_pct']:.0f}%, mangrove {s['mangrove_fraction']:.1f}%, mean {s['biomass_mean']:.1f} Mg/ha", flush=True)
                selection[label] = {"scene_id": item.id, "footprint_fraction": fraction}
                break
            print(f"  {item.id}: skipped (insufficient valid pixels)", flush=True)
    # the scenes this selection rule chose; notebooks read it so superseded cache directories are ignored
    (cache / "selection.json").write_text(json.dumps({"rule": "footprint coverage (5% steps) then cloud cover" if args.rule == "coverage" else "cloud cover only (2025)", "rank_resolution": RANK_RESOLUTION, "windows": selection}, indent=1))
    print(f"selection written: {[v['scene_id'] for v in selection.values()]}", flush=True)


if __name__ == "__main__":
    main()
