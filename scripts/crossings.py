"""You only lose on entering the system.

The same mangrove mask, two routes. Break-bulk: reprojected hop after hop the way data moves
between workflow steps and platforms (WGS84 -> UTM -> WGS84 -> Web Mercator -> ...), nearest
neighbour each time, the way masks are actually resampled. Container: fingerprinted once on the
rHEALPix grid, then put through the same number of operations (union, intersection, difference,
zone-list round trip, roll-up). Measures area retained and overlap with the original after every
hop, and the root after every operation.

    uv run python scripts/crossings.py            # prints the table, writes docs/img/crossings.jpg and crossings_masks.jpg
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import rasterio
from plotly.subplots import make_subplots
from rasterio.features import shapes
from rasterio.warp import Resampling, calculate_default_transform, reproject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import burin_core as bc  # noqa: E402

HOPS = 20
LEVEL = 11
SCENE = sorted(glob.glob("data_cache/temporal/sundarbans/*/biomass.tif"))[-1]
# The way data really moves: a different platform, projection and pixel size at every hop.
# UTM 45N at Landsat's 30 m, WGS84 at the analysis grid, Web Mercator at a tile server's 60 m, WGS84 on a
# slightly different grid, UTM at 50 m, WGS84 at 100 m for a summary, and so on. Nearest neighbour throughout.
CHAIN = [("EPSG:32645", 30.0), ("EPSG:4326", 0.0005), ("EPSG:3857", 60.0), ("EPSG:4326", 0.00045),
         ("EPSG:32645", 50.0), ("EPSG:4326", 0.0005), ("EPSG:3857", 40.0), ("EPSG:4326", 0.0009)]


def cos_area_ha(mask: np.ndarray, transform, crs) -> float:
    """Area of a mask in hectares, honestly: WGS84 pixels weighted by cos(latitude), projected pixels by their true scale."""
    if crs.to_epsg() == 4326:
        rows = np.arange(mask.shape[0])
        lat = transform.f + transform.e * (rows + 0.5)
        px = abs(transform.a) * 111_320 * np.cos(np.radians(lat)) * abs(transform.e) * 110_574
        return float((mask.sum(axis=1) * px).sum() / 1e4)
    if crs.to_epsg() == 3857:
        rows = np.arange(mask.shape[0])
        y = transform.f + transform.e * (rows + 0.5)
        lat = np.degrees(2 * np.arctan(np.exp(y / 6378137.0)) - np.pi / 2)
        k = np.cos(np.radians(lat))  # Mercator scale factor
        px = abs(transform.a) * abs(transform.e) * k * k
        return float((mask.sum(axis=1) * px).sum() / 1e4)
    return float(mask.sum() * abs(transform.a) * abs(transform.e) / 1e4)


def hop(mask: np.ndarray, transform, crs, dst_crs: str, res: float):
    with rasterio.Env():
        w, h = mask.shape[1], mask.shape[0]
        left, top = transform * (0, 0)
        right, bottom = transform * (w, h)
        dst_t, dw, dh = calculate_default_transform(crs, dst_crs, w, h, left=left, bottom=bottom, right=right, top=top, resolution=res)
        out = np.zeros((dh, dw), dtype="uint8")
        reproject(mask.astype("uint8"), out, src_transform=transform, src_crs=crs, dst_transform=dst_t, dst_crs=dst_crs, resampling=Resampling.nearest)
    return out.astype(bool), dst_t, rasterio.crs.CRS.from_string(dst_crs)


def on_original_grid(mask, transform, crs, ref_shape, ref_transform):
    """Bring a WGS84 mask back onto the original pixel grid to compare pixel by pixel."""
    out = np.zeros(ref_shape, dtype="uint8")
    reproject(mask.astype("uint8"), out, src_transform=transform, src_crs=crs, dst_transform=ref_transform, dst_crs="EPSG:4326", resampling=Resampling.nearest)
    return out.astype(bool)


def main() -> None:
    with rasterio.open(SCENE) as src:
        band = src.read(1)
        mask0 = np.isfinite(band) & (band > 0)
        t0, crs0 = src.transform, src.crs
    area0 = cos_area_ha(mask0, t0, crs0)
    print(f"scene {Path(SCENE).parent.name}: mangrove mask {mask0.sum():,} pixels, {area0:,.0f} ha")

    # ---- break-bulk: reproject hop after hop
    mask, t, crs = mask0, t0, crs0
    bulk = [{"hop": 0, "area_pct": 100.0, "iou": 1.0, "crs": "EPSG:4326"}]
    for k in range(1, HOPS + 1):
        dst, res = CHAIN[(k - 1) % len(CHAIN)]
        mask, t, crs = hop(mask, t, crs, dst, res)
        area = cos_area_ha(mask, t, crs)
        rec = {"hop": k, "area_pct": 100 * area / area0, "crs": dst, "res": res}
        if dst == "EPSG:4326":
            back = on_original_grid(mask, t, crs, mask0.shape, t0)
            rec["iou"] = float((back & mask0).sum() / (back | mask0).sum())
            rec["lost"] = int((mask0 & ~back).sum()); rec["gained"] = int((back & ~mask0).sum())
        bulk.append(rec)
    final = on_original_grid(mask, t, crs, mask0.shape, t0)

    # ---- container: fingerprint once, then operate
    parts = [g["coordinates"] for g, v in shapes(mask0.astype("uint8"), mask=mask0, transform=t0, connectivity=8) if v == 1]
    tree = bc.Tree.from_geojson({"type": "MultiPolygon", "coordinates": parts}, LEVEL)
    entry_area = tree.leaf_count() * bc.cell_area_m2(LEVEL) / 1e4
    root0 = tree.root_hex
    from rasterio.features import rasterize
    zones_gj = bc.cells_geojson(tree.cells(), None, 3)
    zones_px = rasterize([(f["geometry"], 1) for f in zones_gj["features"]], out_shape=mask0.shape, transform=t0, fill=0, all_touched=False).astype(bool)
    entry_iou = float((zones_px & mask0).sum() / (zones_px | mask0).sum())
    bbox_tree = bc.Tree.from_geojson({"type": "Polygon", "coordinates": [[[t0.c, t0.f + t0.e * mask0.shape[0]], [t0.c + t0.a * mask0.shape[1], t0.f + t0.e * mask0.shape[0]],
                                                                          [t0.c + t0.a * mask0.shape[1], t0.f], [t0.c, t0.f], [t0.c, t0.f + t0.e * mask0.shape[0]]]]}, LEVEL)
    empty = bc.Tree.from_cells([], LEVEL)
    ops = [("union with itself", lambda x: x.union(x)), ("intersect with the survey box", lambda x: x.intersect(bbox_tree)),
           ("difference with empty", lambda x: x.difference(empty)), ("zone list round trip", lambda x: bc.Tree.from_cells(x.cells(), LEVEL)),
           ("union with the intersection", lambda x: x.union(x.intersect(bbox_tree)))]
    cont = [{"op": 0, "name": "fingerprinted (the one crossing)", "root": root0, "zones": tree.leaf_count()}]
    cur = tree
    for k in range(1, HOPS + 1):
        name, fn = ops[(k - 1) % len(ops)]
        cur = fn(cur)
        cont.append({"op": k, "name": name, "root": cur.root_hex, "zones": cur.leaf_count()})
    assert all(c["root"] == root0 for c in cont), "a set operation changed the root: that would be a bug"

    # ---- report
    print(f"\nbreak-bulk: {HOPS} hops through {' -> '.join(f'{c}@{r}' for c, r in CHAIN)} ...")
    for r in bulk:
        if "iou" in r:
            print(f"  hop {r['hop']:2d}  area {r['area_pct']:6.2f} %  overlap with original {100 * r['iou']:6.2f} %  lost {r.get('lost', 0):,} gained {r.get('gained', 0):,} px")
    print(f"\ncontainer: entry {100 * entry_area / area0:.2f} % of the mask area, {100 * entry_iou:.2f} % overlap ({tree.leaf_count():,} zones at level {LEVEL}, {len(tree.cells()):,} compact); "
          f"then {HOPS} operations, root {root0[:16]}… every time, {cur.leaf_count():,} zones every time")
    Path("docs/img").mkdir(parents=True, exist_ok=True)
    (Path("docs/img") / "crossings.json").write_text(json.dumps({"scene": Path(SCENE).parent.name, "area_ha": area0, "level": LEVEL,
                                                                  "entry_pct": 100 * entry_area / area0, "entry_iou": entry_iou, "root": root0, "bulk": bulk, "container": cont}, indent=1))

    # ---- figure 1: the two routes
    fig = go.Figure()
    xs = [r["hop"] for r in bulk if "iou" in r]
    fig.add_trace(go.Scatter(x=xs, y=[100 * r["iou"] for r in bulk if "iou" in r], mode="lines+markers", name="break-bulk: reprojected at every hop (overlap with the original)",
                             line={"color": "#e45756", "width": 3}, marker={"size": 8}))
    fig.add_trace(go.Scatter(x=[r["hop"] for r in bulk], y=[r["area_pct"] for r in bulk], mode="lines", name="break-bulk: area retained",
                             line={"color": "#e45756", "width": 1.5, "dash": "dot"}))
    fig.add_trace(go.Scatter(x=[c["op"] for c in cont], y=[100 * entry_iou] * len(cont), mode="lines+markers", name=f"container: fingerprinted once, then {HOPS} operations (root unchanged every time)",
                             line={"color": "#54a24b", "width": 3}, marker={"size": 6}))
    fig.add_annotation(x=0, y=100 * entry_iou, text=f"entry: {100 * entry_iou:.1f} % overlap, {100 * entry_area / area0:.2f} % of the area, at level {LEVEL}; paid once", showarrow=True, arrowhead=2, ax=150, ay=-40,
                       font={"size": 12, "color": "#54a24b"})
    fig.add_annotation(x=xs[-1], y=100 * bulk[-1]["iou"], text=f"after {HOPS} hops: {100 * (1 - bulk[-1]['iou']):.1f} % of the forest has moved", showarrow=True, arrowhead=2, ax=-140, ay=30,
                       font={"size": 12, "color": "#e45756"})
    fig.update_layout(title={"text": "You only lose on entering the system<br><sup>the Sundarbans mangrove mask: reprojected hop after hop, or fingerprinted once and operated on</sup>", "x": 0.02},
                      xaxis={"title": "handlings (reprojection hops, or set operations)", "dtick": 2}, yaxis={"title": "% of the original", "range": [min(80, min(100 * r["iou"] for r in bulk if "iou" in r) - 5), 102]},
                      legend={"orientation": "h", "y": -0.22}, height=520, width=1100, margin={"l": 60, "r": 30, "t": 80, "b": 110}, template="plotly_white")
    fig.write_image("docs/img/crossings.jpg", scale=2)

    # ---- figure 2: the mask before and after, and what moved
    diff = np.zeros(mask0.shape, dtype="int8")
    diff[mask0 & final] = 1; diff[mask0 & ~final] = 2; diff[~mask0 & final] = 3
    f2 = make_subplots(rows=1, cols=2, subplot_titles=("the mask, as computed", f"after {HOPS} reprojection hops: lost (red), gained (blue)"), horizontal_spacing=0.03)
    f2.add_trace(go.Heatmap(z=np.where(mask0, 1, 0)[::-1], colorscale=[[0, "#f4f4f4"], [1, "#2e7d32"]], showscale=False), row=1, col=1)
    f2.add_trace(go.Heatmap(z=diff[::-1], zmin=0, zmax=3, colorscale=[[0, "#f4f4f4"], [0.33, "#2e7d32"], [0.34, "#2e7d32"], [0.66, "#e45756"], [0.67, "#e45756"], [1, "#4c78a8"]], showscale=False), row=1, col=2)
    for c in (1, 2):
        f2.update_xaxes(visible=False, row=1, col=c); f2.update_yaxes(visible=False, scaleanchor=f"x{c if c > 1 else ''}", row=1, col=c)
    f2.update_layout(height=520, width=1100, margin={"l": 10, "r": 10, "t": 50, "b": 10}, template="plotly_white")
    f2.write_image("docs/img/crossings_masks.jpg", scale=2)
    print("wrote docs/img/crossings.jpg, docs/img/crossings_masks.jpg, docs/img/crossings.json")


if __name__ == "__main__":
    main()
