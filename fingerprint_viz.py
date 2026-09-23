"""Helpers for the coverage-root notebooks: sites, cached scenes, satellite tile maps with cell
layers, the hash-tree icicle, and the opening ladder. Pure functions over burin_core trees."""
from __future__ import annotations

import json
from pathlib import Path

import burin_core as bc
import marimo as mo
import numpy as np
import plotly.graph_objects as go
import rasterio
from rasterio.features import shapes
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

STUDY_SITES = {
    "Sundarbans": {"west": 89.325, "east": 89.595, "south": 21.865, "north": 22.135},
    "Can Gio Biosphere Reserve": {"west": 106.73, "east": 107.05, "south": 10.35, "north": 10.68},
    "Thor Heyerdahl Climate Park": {"west": 94.462, "east": 94.502, "south": 17.044, "north": 17.082},
    "Wunbaik Reserved Forest": {"west": 94.3, "east": 94.7, "south": 16.6, "north": 16.9},
}
PROFILES = {"OGC API-DGGS Annex B rHEALPix (lon₀ = 50°)": bc.OGC_RHEALPIX, "burin-1 (lon₀ = 0°)": bc.BURIN_1}
ESRI_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
LEVEL_COLORS = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]  # coarse → fine
PALETTE = ["#f58518", "#4c78a8", "#e45756", "#eeca3b", "#b279a2", "#72b7b2", "#9d755d", "#54a24b"]
A = 9


def slug(site: str) -> str:
    return site.lower().replace(" ", "_")


def bbox_polygon(b):
    return {"type": "Polygon", "coordinates": [[[b["west"], b["south"]], [b["east"], b["south"]], [b["east"], b["north"]], [b["west"], b["north"]], [b["west"], b["south"]]]]}


def footprint(array, transform):
    """The non-empty extent of a raster as GeoJSON: the union of its valid pixels."""
    mask = ~np.isnan(array) & (array > 0)
    polys = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=transform) if v == 1]
    return mapping(unary_union(polys)) if polys else {"type": "MultiPolygon", "coordinates": []}


def level_of(cid: int) -> int:
    n, x = 0, cid
    while x:
        x //= A
        n += 1
    return n - 2


def expand_to(cids, target_level: int):
    """Cells at levels >= target_level: compact zones coarser than that are spelled out."""
    out = []
    for c in cids:
        k = target_level - level_of(c)
        if k <= 0:
            out.append(c)
        else:
            out.extend(range(c * A**k, (c + 1) * A**k))
    return out


def scene_dirs_for(site_dir: Path):
    """The cached scene directories a site's selection chose (selection.json), else every cached scene."""
    sel = site_dir / "selection.json"
    if sel.exists():
        chosen = [w["scene_id"] for w in json.loads(sel.read_text())["windows"].values()]
        return [site_dir / c for c in chosen if (site_dir / c / "biomass.tif").exists()]
    return sorted(p.parent for p in site_dir.glob("*/biomass.tif"))


def load_scenes(site_dir: Path, resolution: int, profile=None):
    """Cached scenes with their valid-data and mangrove footprint trees, sorted by date."""
    out = []
    for sd in scene_dirs_for(site_dir):
        st = json.loads((sd / "stats.json").read_text())
        with rasterio.open(sd / "nir.tif") as s:
            nir, t = s.read(1), s.transform
        with rasterio.open(sd / "biomass.tif") as s:
            bio = s.read(1)
        out.append(
            {
                "dir": sd, "date": st["date"][:10], "scene_id": st["scene_id"], "cloud": st["cloud_cover"],
                "reported_fraction": st["mangrove_fraction"], "reported_biomass": st["biomass_mean"], "biomass": bio, "transform": t,
                "valid": bc.Tree.from_geojson(footprint(np.where(np.isnan(nir), 0.0, 1.0), t), resolution, profile),
                "mask": bc.Tree.from_geojson(footprint(bio, t), resolution, profile),
            }
        )
    out.sort(key=lambda s: s["date"])
    return out


def common_ground(scenes):
    c = scenes[0]["valid"]
    for s in scenes[1:]:
        c = c.intersect(s["valid"])
    return c


def cell_layer(cids, name, color=None, by_level=False, opacity=0.55, line=0.4, profile=None, n=3):
    """A Choroplethmap trace for a set of cells: one flat colour, or coloured by level."""
    cids = list(cids)
    if not cids:
        return None
    gj = bc.cells_geojson(cids, profile, n)
    levels = [f["properties"]["level"] for f in gj["features"]]
    ids = [f["id"] for f in gj["features"]]
    if by_level:
        lo, hi = min(levels), max(levels)
        pick = lambda l: LEVEL_COLORS[min(len(LEVEL_COLORS) - 1, round((l - lo) * (len(LEVEL_COLORS) - 1) / max(hi - lo, 1)))]
        scale = [[0, pick(lo)], [1, pick(hi)]] if lo == hi else [[(l - lo) / (hi - lo), pick(l)] for l in range(lo, hi + 1)]
        z, showscale, cbar = levels, True, {"title": "cell level", "tickvals": list(range(lo, hi + 1)), "len": 0.5, "thickness": 12}
    else:
        scale, z, showscale, cbar = [[0, color], [1, color]], [1] * len(ids), False, None
    return go.Choroplethmap(
        geojson=gj, locations=ids, z=z, colorscale=scale, zmin=min(z), zmax=max(z) if max(z) > min(z) else min(z) + 1,
        showscale=showscale, colorbar=cbar, marker={"opacity": opacity, "line": {"width": line, "color": "white"}},
        name=name, text=[f"{f['properties']['suid']} · level {f['properties']['level']}" for f in gj["features"]], hovertemplate="%{text}<extra>" + name + "</extra>",
    )


def count_layer(counts: dict, name, profile=None, title="entries"):
    """Cells coloured by an integer count (attention, revisits)."""
    gj = bc.cells_geojson(list(counts), profile, 3)
    z = [counts[int(f["id"])] for f in gj["features"]]
    return go.Choroplethmap(
        geojson=gj, locations=[f["id"] for f in gj["features"]], z=z, colorscale="YlOrRd", zmin=0, zmax=max(z),
        marker={"opacity": 0.75, "line": {"width": 0.3, "color": "white"}}, colorbar={"title": title, "thickness": 12, "len": 0.5},
        text=[f"{f['properties']['suid']}: {counts[int(f['id'])]} {title}" for f in gj["features"]], hovertemplate="%{text}<extra></extra>", name=name,
    )


def tile_map(traces, b, height=560, satellite=True, zoom_delta=-0.6):
    """Traces on a satellite (or OSM) tile map framed on bbox b."""
    span = max(b["east"] - b["west"], (b["north"] - b["south"]) * 1.4)
    zoom = float(np.log2(360.0 / span)) + zoom_delta
    fig = go.Figure(data=[t for t in traces if t is not None])
    style = {"style": "white-bg", "layers": [{"below": "traces", "sourcetype": "raster", "source": [ESRI_IMAGERY]}]} if satellite else {"style": "open-street-map"}
    fig.update_layout(
        map={**style, "center": {"lon": (b["west"] + b["east"]) / 2, "lat": (b["south"] + b["north"]) / 2}, "zoom": zoom},
        margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=height, legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,0.85)"},
    )
    return fig


def region_map(traces, center, zoom, height=520):
    fig = go.Figure(data=[t for t in traces if t is not None])
    fig.update_layout(map={"style": "white-bg", "layers": [{"below": "traces", "sourcetype": "raster", "source": [ESRI_IMAGERY]}], "center": center, "zoom": zoom}, margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=height)
    return fig


def outline(geojson, name, color="#ffffff", width=2.5):
    coords = geojson["coordinates"][0] if geojson["type"] == "Polygon" else [c for poly in geojson["coordinates"] for c in poly[0] + [[None, None]]]
    return go.Scattermap(lon=[c[0] for c in coords], lat=[c[1] for c in coords], mode="lines", line={"width": width, "color": color}, name=name, hoverinfo="skip")


def stat(value, label, caption=None):
    return mo.stat(value=value, label=label, caption=caption, bordered=True)


def takeaway(text):
    return mo.callout(mo.md(text), kind="neutral")


def thumbnails(scenes, b, n_aoi, profile=None, height=310):
    """One row of small satellite maps, one per scene: the valid-data footprint over the bbox."""
    fig = go.Figure()
    n = len(scenes)
    span = max(b["east"] - b["west"], (b["north"] - b["south"]) * 1.4)
    zoom = float(np.log2(360.0 / span)) - 1.1
    layout = {"margin": {"l": 0, "r": 0, "t": 44, "b": 0}, "height": height, "showlegend": False, "annotations": []}
    for i, s in enumerate(scenes):
        key = "map" if i == 0 else f"map{i + 1}"
        share = 100 * s["valid"].leaf_count() / n_aoi
        colour = "#e45756" if share < 25 else "#54a24b"
        gj = bc.cells_geojson(s["valid"].cells(), profile, 3)
        fig.add_trace(go.Choroplethmap(geojson=gj, locations=[f["id"] for f in gj["features"]], z=[1] * len(gj["features"]), colorscale=[[0, colour], [1, colour]], showscale=False, marker={"opacity": 0.6, "line": {"width": 0}}, subplot=key, hoverinfo="skip"))
        ring = bbox_polygon(b)["coordinates"][0]
        fig.add_trace(go.Scattermap(lon=[c[0] for c in ring], lat=[c[1] for c in ring], mode="lines", line={"width": 2, "color": "white"}, subplot=key, hoverinfo="skip"))
        layout[key] = {"style": "white-bg", "layers": [{"below": "traces", "sourcetype": "raster", "source": [ESRI_IMAGERY]}], "center": {"lon": (b["west"] + b["east"]) / 2, "lat": (b["south"] + b["north"]) / 2}, "zoom": zoom, "domain": {"x": [i / n + 0.004, (i + 1) / n - 0.004], "y": [0, 1]}}
        layout["annotations"].append({"text": f"<b>{s['date']}</b>  covers <b>{share:.0f}%</b><br><span style='font-size:10px;color:#666'>root {s['valid'].root_hex[:10]}…</span>", "x": (i + 0.5) / n, "y": 1.0, "xref": "paper", "yref": "paper", "yanchor": "bottom", "showarrow": False, "align": "center", "font": {"size": 12, "color": colour}})
    fig.update_layout(**layout)
    return fig


def tree_icicle(tree, R, height=380):
    """The canonical tree as an icicle: root, partial ancestors (grey), full zones (green)."""
    cells = [bc.cid_to_suid(c) for c in tree.cells()]
    full = {s: A ** (R - (len(s) - 1)) for s in cells}
    partial = {}
    for s in cells:
        for k in range(1, len(s)):
            partial[s[:k]] = partial.get(s[:k], 0) + full[s]
    ids = ["root"] + list(partial) + cells
    parents = [""] + ["root" if len(a) == 1 else a[:-1] for a in partial] + ["root" if len(s) == 1 else s[:-1] for s in cells]
    values = [sum(full.values())] + [partial[a] for a in partial] + [full[s] for s in cells]
    colors = ["#1b1b3a"] + ["#c8c8c8"] * len(partial) + ["#54a24b"] * len(cells)
    fig = go.Figure(go.Icicle(ids=ids, labels=ids, parents=parents, values=values, branchvalues="total", marker={"colors": colors, "line": {"width": 0.5, "color": "white"}}, tiling={"orientation": "v"}, hovertemplate="%{label}<br>%{value:,} zones<extra></extra>", textfont={"size": 10}))
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=height)
    return fig, len(partial), len(cells)


def opening_ladder(record):
    """An opening drawn as rows of sibling hashes, the opened position highlighted per level."""
    op, rows = record["opening"], []
    while "entries" in op:
        es = op["entries"]
        idx = next(i for i, e in enumerate(es) if isinstance(e, dict))
        rows.append((es, idx))
        op = es[idx]
    claim = op["claim"]
    box = "display:inline-block;min-width:58px;height:26px;margin:2px;border-radius:4px;font:11px ui-monospace,monospace;line-height:26px;text-align:center;"
    html = []
    for lvl, (es, idx) in enumerate(rows):
        cells = [f'<span style="{box}background:#54a24b;color:white;font-weight:600">▼ {i}</span>' if i == idx else f'<span style="{box}background:#eef0f3;color:#555">{e[:6]}</span>' for i, e in enumerate(es)]
        label = "bases" if lvl == 0 else f"level {lvl}"
        html.append(f'<div style="white-space:nowrap"><span style="display:inline-block;width:64px;font:12px system-ui;color:#666">{label}</span>{"".join(cells)}</div>')
    colour = "#54a24b" if claim == "full" else "#e45756"
    html.append(f'<div><span style="display:inline-block;width:64px;font:12px system-ui;color:#666">claim</span><span style="{box}background:{colour};color:white;font-weight:600;min-width:120px">{claim.upper()}</span></div>')
    return mo.Html('<div style="overflow-x:auto">' + "".join(html) + "</div>")


def claim_of(record):
    op = record["opening"]
    while "entries" in op:
        op = next(e for e in op["entries"] if isinstance(e, dict))
    return op["claim"]
