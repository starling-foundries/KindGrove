"""Tests for the fingerprint step: `uv run pytest cwl/tests` (pythonpath is set in pyproject)."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pystac
import pytest
import rasterio
from rasterio.transform import from_bounds

import burin_core as bc
import pystac_fingerprint as fp

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "cwl" / "fingerprint.py"
SCHEMA = fp.SCHEMA_URI
ENV = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "stac-extension" / "python"), os.environ.get("PYTHONPATH", "")])}


def box(w, s, e, n):
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def write_mask(path: Path, bounds, crs="EPSG:4326", size=60):
    """A mask with the north-west quarter set: the covered ground is a quarter of the box."""
    arr = np.zeros((size, size), dtype="uint8")
    arr[: size // 2, : size // 2] = 1
    with rasterio.open(path, "w", driver="GTiff", height=size, width=size, count=1, dtype="uint8",
                       crs=crs, transform=from_bounds(*bounds, size, size), nodata=0) as dst:
        dst.write(arr, 1)


def make_catalog(root: Path, *, with_mask=True, mask_crs="EPSG:4326", null_geometry=False, as_collection=False):
    """A step_1-style output: items in <id>/<id>.json with assets next to them, hrefs relative."""
    bounds = (95.15, 15.9, 95.35, 16.1)
    container = (pystac.Collection(id="c", description="test", extent=pystac.Extent(
        pystac.SpatialExtent([list(bounds)]), pystac.TemporalExtent([[None, None]])))
        if as_collection else pystac.Catalog(id="c", description="test"))
    for i in range(2):
        item = pystac.Item(id=f"item-{i}", geometry=None if null_geometry and i == 1 else box(*bounds), bbox=list(bounds),
                           datetime=dt.datetime(2026, 1, 1 + i, tzinfo=dt.timezone.utc), properties={})
        if with_mask:
            item_dir = root / item.id
            item_dir.mkdir(parents=True, exist_ok=True)
            write_mask(item_dir / "mangrove_mask.tif", bounds, mask_crs)
            item.add_asset("mangrove_mask_tif", pystac.Asset(href="mangrove_mask.tif", media_type="image/tiff", roles=["data"]))
        container.add_item(item)
    container.normalize_and_save(str(root), catalog_type=pystac.CatalogType.SELF_CONTAINED)
    return root


def run(*args, expect=0):
    p = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=ENV)
    assert p.returncode == expect, p.stdout + p.stderr
    return p


def load_items(out: Path):
    return {p.parent.name: json.loads(p.read_text()) for p in out.glob("*/*.json") if not p.name.endswith("fingerprint.json")}


def test_hrefs_survive_and_fields_written(tmp_path):
    src = make_catalog(tmp_path / "in")
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 9)
    items = load_items(out)
    assert set(items) == {"item-0", "item-1"}
    for it in items.values():
        assert it["assets"]["mangrove_mask_tif"]["href"].lstrip("./") == "mangrove_mask.tif"  # the bug that broke stage-out
        assert SCHEMA in it["stac_extensions"]
        p = it["properties"]
        assert p["fingerprint:dggrs"] == fp.OGC_RHEALPIX_URI and p["fingerprint:zone_level"] == 9
        assert len(p["fingerprint:root"]) == 64 and p["fingerprint:zone_count"] > 0
        # item geometry fingerprint and its zone list
        assert it["assets"]["fingerprint"]["roles"] == ["fingerprint"]
        assert it["assets"]["fingerprint"]["fingerprint:root"] == p["fingerprint:root"]
        # mask asset fingerprint (auto) and its zone list
        m = it["assets"]["mangrove_mask_tif"]
        assert len(m["fingerprint:root"]) == 64 and m["fingerprint:root"] != p["fingerprint:root"]
        assert it["assets"]["mangrove_mask_tif_fingerprint"]["fingerprint:root"] == m["fingerprint:root"]
        assert 0.2 < m["fingerprint:zone_count"] / p["fingerprint:zone_count"] < 0.3  # a quarter of the box
        assert (out / it["id"] / "mangrove_mask.tif").exists()
    cat = json.loads((out / "catalog.json").read_text())
    assert cat["fingerprint:root"] == items["item-0"]["properties"]["fingerprint:root"]  # identical geometries: union == item
    assert SCHEMA in cat["stac_extensions"]


def test_zone_list_is_ogc_and_self_verifying(tmp_path):
    src = make_catalog(tmp_path / "in")
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 9)
    it = load_items(out)["item-0"]
    doc = json.loads((out / "item-0" / "fingerprint.json").read_text())
    assert set(doc) == {"zones", "returnedAreaMetersSquare", "links"}
    assert doc["links"][0]["rel"] == fp.DGGRS_DEFINITION_REL and doc["links"][0]["href"] == fp.OGC_RHEALPIX_URI
    assert all(z[0] in "NOPQRS" and z[1:].isdigit() for z in doc["zones"])  # OGC text zone identifiers
    assert len({len(z) for z in doc["zones"]}) > 1  # compact: mixed levels
    rebuilt = fp.tree_from_zone_list(doc, 9, bc.OGC_RHEALPIX)
    assert rebuilt.root_hex == it["properties"]["fingerprint:root"]
    assert abs(doc["returnedAreaMetersSquare"] - rebuilt.leaf_count() * bc.cell_area_m2(9)) < 1e-3


def test_utm_mask_is_reprojected(tmp_path):
    src = make_catalog(tmp_path / "in", mask_crs="EPSG:32646")  # bounds are treated as metres here; only the code path matters
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 6)
    assert "fingerprint:root" in load_items(out)["item-0"]["assets"]["mangrove_mask_tif"]


def test_check_passes_then_fails_after_tamper(tmp_path):
    src = make_catalog(tmp_path / "in")
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 8)
    assert "all fingerprints verified" in run("--stac", out, "--check").stdout
    assert "all fingerprints verified" in run("--stac", out, "--check", "--deep").stdout
    f = out / "item-1" / "item-1.json"
    d = json.loads(f.read_text())
    d["properties"]["fingerprint:root"] = "0" * 64
    f.write_text(json.dumps(d))
    assert "MISMATCH" in run("--stac", out, "--check", expect=1).stdout
    # tamper with a zone list instead: the hash no longer matches the asset's root
    d["properties"]["fingerprint:root"] = load_items(out)["item-0"]["properties"]["fingerprint:root"]
    f.write_text(json.dumps(d))
    z = out / "item-1" / "mangrove_mask_tif_fingerprint.json"
    zd = json.loads(z.read_text()); zd["zones"] = zd["zones"][:-1]; z.write_text(json.dumps(zd))
    assert "zone list hashes to" in run("--stac", out, "--check", expect=1).stdout


def test_null_geometry_is_skipped_unless_strict(tmp_path):
    src = make_catalog(tmp_path / "in", with_mask=False, null_geometry=True)
    out = tmp_path / "out"
    p = run("--stac", src, "--out", out, "--zone-level", 8)
    assert "not fingerprinted" in p.stderr
    items = load_items(out)
    assert "fingerprint:root" in items["item-0"]["properties"] and "fingerprint:root" not in items["item-1"]["properties"]
    run("--stac", src, "--out", tmp_path / "out2", "--zone-level", 8, "--strict", expect=1)


def test_collection_root_and_assets_none(tmp_path):
    src = make_catalog(tmp_path / "in", as_collection=True)
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 8, "--assets", "none")
    col = json.loads((out / "collection.json").read_text())
    it = load_items(out)["item-0"]
    assert col["fingerprint:root"] == it["properties"]["fingerprint:root"]
    assert "fingerprint:root" not in it["assets"]["mangrove_mask_tif"]
    assert SCHEMA in col["stac_extensions"]
    assert "all fingerprints verified" in run("--stac", out, "--check").stdout


def test_extension_schema_validates_output(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "stac-extension" / "json-schema" / "schema.json").read_text())
    src = make_catalog(tmp_path / "in", as_collection=True)
    out = tmp_path / "out"
    run("--stac", src, "--out", out, "--zone-level", 8)
    for it in load_items(out).values():
        jsonschema.validate(it, schema)
    jsonschema.validate(json.loads((out / "collection.json").read_text()), schema)


def test_pystac_api_roundtrip(tmp_path):
    item = pystac.Item(id="x", geometry=box(0, 0, 1, 1), bbox=[0, 0, 1, 1], datetime=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc), properties={})
    item.set_self_href(str(tmp_path / "x.json"))
    ext = fp.FingerprintExtension.ext(item, add_if_missing=True)
    tree = ext.apply_geometry(7)
    assert ext.root == tree.root_hex and ext.zone_count == tree.leaf_count()
    assert fp.FingerprintExtension.verify(item) == {"geometry": "ok", "fingerprint": "ok"}
    d = item.to_dict()
    again = pystac.Item.from_dict(d)
    assert fp.FingerprintExtension.ext(again).root == tree.root_hex
