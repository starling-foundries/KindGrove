#!/usr/bin/env python3
"""Fingerprint a STAC catalog, or check the fingerprints it already carries.

Reads a self-contained STAC directory (the output of an OGC Application Package step), copies it,
and writes the STAC Fingerprint extension into it. Vocabulary is OGC API - DGGS: zones, refinement
level, compact zone lists, DGGRS.

  Item          fingerprint:root of the item `geometry` at --zone-level, with the zone list attached as
                asset "fingerprint" (an OGC API - DGGS JSON zone list, compact, text zone identifiers).
  Mask assets   with --assets auto (default), every GeoTIFF asset whose key or role contains "mask" gets
                fingerprint:root of its covered pixels (non-zero, non-nodata, reprojected to EPSG:4326
                when needed), with the zone list attached as asset "<key>_fingerprint". Needs rasterio
                (the -raster image). --assets none turns this off; --assets k1,k2 names assets.
  Collections   and the root Catalog get the union of their items' fingerprints.

Asset hrefs are never touched: the output directory is still a valid stage-out. An item that
cannot be fingerprinted (null geometry, unreadable asset) is left unchanged with a warning;
--strict makes that a failure.

--check recomputes every item root from its geometry (JSON only), rebuilds every zone list and
hashes it (proving the list is the one its root names), and with --deep re-polygonises mask
assets too. Exit 1 on the first mismatch.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import burin_core as bc
import pystac
from pystac.utils import make_absolute_href

import pystac_fingerprint as fp

__version__ = "0.3.0"


def is_geotiff(asset: pystac.Asset) -> bool:
    mt = (asset.media_type or "").lower()
    return mt.startswith("image/tiff") or asset.href.lower().endswith((".tif", ".tiff"))


def looks_like_mask(key: str, asset: pystac.Asset) -> bool:
    return "mask" in key.lower() or any("mask" in r.lower() for r in (asset.roles or []))


def raster_available() -> bool:
    try:
        import rasterio  # noqa: F401
        return True
    except ImportError:
        return False


def mask_assets(item: pystac.Item, spec: str) -> list[str]:
    """Asset keys to fingerprint from their pixels, per --assets."""
    if spec == "none":
        return []
    if spec == "auto":
        keys = [k for k, a in item.assets.items() if is_geotiff(a) and looks_like_mask(k, a)]
        if keys and not raster_available():
            print(f"  {item.id}: mask asset(s) {keys} present but rasterio is not installed; geometry only", file=sys.stderr)
            return []
        return keys
    keys = [k.strip() for k in spec.split(",") if k.strip()]
    missing = [k for k in keys if k not in item.assets]
    if missing:
        raise KeyError(f"no asset(s) {missing}")
    return keys


def footprint_from_asset(item: pystac.Item, key: str) -> dict:
    """The covered pixels of a raster asset as a GeoJSON MultiPolygon in EPSG:4326."""
    import numpy as np
    import rasterio
    from rasterio.features import shapes
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    href = make_absolute_href(item.assets[key].href, item.get_self_href())
    with rasterio.open(href) as src:
        band = src.read(1)
        valid = np.isfinite(band)
        if src.nodata is not None:
            valid &= band != src.nodata
        mask = valid & (band > 0)
        transform = src.transform
        if src.crs is None:
            raise ValueError(f"asset {key!r} has no CRS")
        if src.crs.to_epsg() != 4326:
            dst_transform, w, h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
            out = np.zeros((h, w), dtype="uint8")
            reproject(mask.astype("uint8"), out, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=dst_transform, dst_crs="EPSG:4326", resampling=Resampling.nearest)
            mask, transform = out.astype(bool), dst_transform
    # connected components, each a polygon with holes; they never overlap, so no union is needed
    parts = [g["coordinates"] for g, v in shapes(mask.astype("uint8"), mask=mask, transform=transform, connectivity=8) if v == 1]
    if not parts:
        raise ValueError(f"asset {key!r} is empty (no covered pixels)")
    return {"type": "MultiPolygon", "coordinates": parts}


def find_root(stac_dir: Path) -> Path:
    for name in ("catalog.json", "collection.json"):
        if (stac_dir / name).exists():
            return stac_dir / name
    sys.exit(f"no catalog.json or collection.json in {stac_dir}")


def containers(root: pystac.Catalog | pystac.Collection) -> list:
    return [root, *root.get_all_collections()] if isinstance(root, pystac.Catalog) else [root]


def annotate(stac_dir: Path, out_dir: Path, zone_level: int, profile_name: str, assets: str, strict: bool) -> int:
    root_file = find_root(stac_dir)
    if out_dir.resolve() != stac_dir.resolve():
        if out_dir.exists():
            shutil.rmtree(out_dir)
        shutil.copytree(stac_dir, out_dir)
    # open the copy, so every relative href resolves against its final location and is written back unchanged
    root = pystac.read_file(str(out_dir / root_file.name))
    trees: dict[str, bc.Tree] = {}
    failures = 0
    for item in root.get_all_items():
        try:
            ext = fp.FingerprintExtension.ext(item, add_if_missing=True)
            tree = ext.apply_geometry(zone_level, profile_name)
            print(f"{item.id}: geometry -> {tree.leaf_count()} zones at level {zone_level}, root {tree.root_hex}")
            for key in mask_assets(item, assets):
                t = ext.apply_asset(key, footprint_from_asset(item, key), zone_level, profile_name)
                print(f"{item.id}/{key}: covered pixels -> {t.leaf_count()} zones, root {t.root_hex}")
        except Exception as e:  # noqa: BLE001 - every failure mode is reported the same way
            failures += 1
            print(f"  {item.id}: not fingerprinted ({e})", file=sys.stderr)
            if strict:
                raise
            continue
        trees[item.id] = tree
    for c in containers(root):
        members = [i.id for i in c.get_all_items() if i.id in trees]
        u = fp.union([trees[i] for i in members])
        if u is None:
            continue
        fp.FingerprintExtension.ext(c, add_if_missing=True).apply(u, profile_name)
        print(f"{c.STAC_OBJECT_TYPE.value.lower()} {c.id}: union of {len(members)} item(s) -> {u.root_hex}")
    root.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return failures


def check(stac_dir: Path, deep: bool) -> int:
    root = pystac.read_file(str(find_root(stac_dir)))
    mismatches = 0
    trees: dict[str, bc.Tree] = {}
    for item in root.get_all_items():
        ext = fp.FingerprintExtension.ext(item)
        if ext.root is None:
            print(f"{item.id}: no fingerprint")
            continue
        deep_fps = {}
        if deep:
            for key, a in item.assets.items():
                if fp.ROOT_PROP in a.extra_fields and fp.ZONE_LIST_ROLE not in (a.roles or []):
                    try:
                        deep_fps[key] = footprint_from_asset(item, key)
                    except Exception as e:  # noqa: BLE001
                        print(f"{item.id}/{key}: cannot re-polygonise ({e})")
                        mismatches += 1
        try:
            result = fp.FingerprintExtension.verify(item, deep_fps)
            _, _, p = ext.burin_profile()
            trees[item.id] = bc.Tree.from_geojson(item.geometry, ext.zone_level, p)
            print(f"{item.id}: ok ({', '.join(result)})  root {ext.root[:16]}…  level {ext.zone_level}")
        except fp.FingerprintError as e:
            mismatches += 1
            print(f"MISMATCH {e}")
    for c in containers(root):
        cext = fp.FingerprintExtension.ext(c)
        if cext.root is None:
            continue
        u = fp.union([trees[i.id] for i in c.get_all_items() if i.id in trees])
        if u is None:
            continue
        ok = u.root_hex == cext.root
        mismatches += 0 if ok else 1
        print(f"{c.STAC_OBJECT_TYPE.value.lower()} {c.id}: union {'ok' if ok else 'MISMATCH'}")
    print(f"{mismatches} mismatch(es)" if mismatches else "all fingerprints verified")
    return mismatches


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stac", required=True, type=Path, help="directory holding catalog.json or collection.json")
    ap.add_argument("--out", type=Path, default=Path("outputs"), help="output directory (copied, then fingerprinted)")
    ap.add_argument("--zone-level", type=int, default=11, help="DGGRS refinement level (11 ≈ 52 m zones)")
    ap.add_argument("--profile", default=fp.DEFAULT_PROFILE, choices=list(fp.PROFILES))
    ap.add_argument("--assets", default="auto", help="auto | none | key,key: assets to fingerprint from their pixels")
    ap.add_argument("--strict", action="store_true", help="fail on the first item that cannot be fingerprinted")
    ap.add_argument("--check", action="store_true", help="verify the fingerprints already in --stac; writes nothing")
    ap.add_argument("--deep", action="store_true", help="with --check: re-polygonise mask assets as well")
    ap.add_argument("--version", action="version", version=f"stac-fingerprint {__version__} (pystac_fingerprint {fp.__version__})")
    args = ap.parse_args()
    if not (0 <= args.zone_level <= bc.MAX_RESOLUTION):
        sys.exit(f"zone level must be 0..{bc.MAX_RESOLUTION}")
    if args.check:
        sys.exit(1 if check(args.stac, args.deep) else 0)
    failures = annotate(args.stac, args.out, args.zone_level, args.profile, args.assets, args.strict)
    if failures:
        print(f"{failures} item(s) left without a fingerprint", file=sys.stderr)


if __name__ == "__main__":
    main()
