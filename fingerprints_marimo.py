import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import json
    import sys
    import time
    from pathlib import Path

    sys.path.insert(0, "cwl")
    sys.path.insert(0, "stac-extension/python")

    import burin_core as bc
    import fingerprint_viz as v
    import marimo as mo
    import fingerprint as ba
    import numpy as np
    import plotly.graph_objects as go
    import pystac
    import pystac_fingerprint as fp
    import rasterio
    from plotly.subplots import make_subplots

    WORKFLOW_HASH = "sha256:6f1c…mangrove-biomass-v1"  # the application package's own content hash; any digest will do


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    # A number without its ground

    *The mangrove workflow was delivered to OGC's Open Science Persistent Demonstrator in 2025. This is
    what it could not say, and what one small change to its outputs makes possible.*
    """
    )
    return


@app.cell(hide_code=True)
def _():
    mo.callout(
        mo.md(
            "**The story in one line.** Give every dataset an identity that is a function of the ground it covers. "
            "Then a value carries its own caveat, scenes are chosen and compared on ground rather than on hope, change is a diff, "
            "a catalogue can answer *what covers this*, and a platform stops moving bytes nobody asked for."
        ),
        kind="info",
    )
    return


@app.cell(hide_code=True)
def _():
    _cached = [s for s in v.STUDY_SITES if v.scene_dirs_for(Path("data_cache") / "temporal" / v.slug(s))]
    mo.stop(
        not _cached,
        mo.callout(mo.md("No cached scenes yet. Run `uv run python scripts/prime_cache.py \"Sundarbans\"` (or any site in `fingerprint_viz.STUDY_SITES`) and reload."), kind="warn"),
    )
    _options = {(s if s in _cached else f"{s} (no cached scenes)"): s for s in v.STUDY_SITES}
    site_dropdown = mo.ui.dropdown(options=_options, value=_cached[0], label="Study site")
    resolution = mo.ui.slider(7, 10, value=9, step=1, label="rHEALPix refinement level", show_value=True)
    profile_radio = mo.ui.radio(options=list(v.PROFILES), value=list(v.PROFILES)[0], label="Grid profile")
    mo.hstack([site_dropdown, resolution, profile_radio], justify="start", gap=2, align="start")
    return profile_radio, resolution, site_dropdown


@app.cell(hide_code=True)
def _(profile_radio, resolution, site_dropdown):
    site = site_dropdown.value
    b = v.STUDY_SITES[site]
    aoi = v.bbox_polygon(b)
    profile = v.PROFILES[profile_radio.value]
    R = resolution.value
    _t0 = time.perf_counter()
    aoi_tree = bc.Tree.from_geojson(aoi, R, profile)
    aoi_ms = 1000 * (time.perf_counter() - _t0)
    n_aoi = aoi_tree.leaf_count()
    cell_ha = bc.cell_area_m2(R, profile) / 1e4
    scenes = v.load_scenes(Path("data_cache") / "temporal" / v.slug(site), R, profile)
    then = v.load_scenes(Path("data_cache") / "temporal_2025" / v.slug(site), R, profile)
    return R, aoi, aoi_ms, aoi_tree, b, cell_ha, n_aoi, profile, scenes, site, then


@app.cell(hide_code=True)
def _(b, n_aoi, profile, site, then):
    mo.stop(not then, mo.md(f"## 1. What we reported in 2025\n\n*No preserved 2025 selection for {site} under `data_cache/temporal_2025/`; pick the Sundarbans or Can Gio.*"))
    _rows = [{"date": s["date"], "scene": s["scene_id"], "mangrove fraction %": round(s["reported_fraction"], 1), "mean biomass Mg/ha": round(s["reported_biomass"], 1), "ground it was computed on": s["valid"].root_hex[:12] + "…", "share of the survey area": f"{100 * s['valid'].leaf_count() / n_aoi:.0f} %"} for s in then]
    _worst = min(then, key=lambda s: s["valid"].leaf_count())
    mo.vstack(
        [
            mo.md(f"## 1. What we reported in 2025, and where each number came from"),
            v.takeaway(f"**Takeaway.** The {_worst['date']} value stood on {100 * _worst['valid'].leaf_count() / n_aoi:.0f} % of the survey area, a sliver at a tile edge. The table could not say so. A number without its ground is not a datapoint."),
            mo.ui.plotly(v.thumbnails(then, b, n_aoi, profile)),
            mo.ui.table(_rows, selection=None),
            mo.md("The last two columns are new: the root names exactly which cells the value was computed on, and the zone count is an exact area. They travel with the value wherever it is copied."),
        ]
    )
    return


@app.cell(hide_code=True)
def _(n_aoi, scenes, then):
    mo.stop(not then or not scenes)
    _g_then, _g_now = v.common_ground(then), v.common_ground(scenes)

    def _series(ss, g):
        n = max(g.leaf_count(), 1)
        return [100 * s["mask"].intersect(g).leaf_count() / n for s in ss]

    _fig = go.Figure(
        [
            go.Scatter(x=[s["date"] for s in then], y=[s["reported_fraction"] for s in then], name="as reported in 2025: each value on its own ground", mode="lines+markers", line={"color": "#b0b0b0", "dash": "dot", "width": 2}, marker={"size": 10}),
            go.Scatter(x=[s["date"] for s in then], y=_series(then, _g_then), name=f"the same scenes on their common ground: {100 * _g_then.leaf_count() / n_aoi:.0f} % of the survey area", mode="lines+markers", line={"color": "#e45756", "width": 3}, marker={"size": 10}),
            go.Scatter(x=[s["date"] for s in scenes], y=_series(scenes, _g_now), name=f"scenes chosen by ground (2026) on their common ground: {100 * _g_now.leaf_count() / n_aoi:.0f} %", mode="lines+markers", line={"color": "#54a24b", "width": 3}, marker={"size": 10}),
        ]
    ).update_layout(height=360, template="plotly_white", yaxis={"title": "mangrove cells, %", "range": [0, 100]}, legend={"orientation": "h", "y": -0.25}, margin={"l": 10, "r": 10, "t": 10, "b": 10})
    mo.vstack(
        [
            mo.md("### Three series, each with its ground"),
            mo.ui.plotly(_fig),
            mo.md(
                "Grey is the 2025 table: four numbers on four pieces of ground, not a series. Its dip and recovery is the ground switching, not the forest. "
                "Red is the honest version of the same scenes, each restricted to the ground all four saw. Green is what the workflow reports now that it "
                "chooses scenes by ground. Red and green are both legitimate: different ground, different measurement, and the root is what says so."
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(R, aoi_tree):
    _canon = aoi_tree.cells()
    _min_level = min(v.level_of(c) for c in _canon) if _canon else R
    _steps = [(k, len(v.expand_to(_canon, R - k))) for k in range(0, R - _min_level + 1)]
    _first_ok = next(k for k, n in _steps if n <= 8000)
    rollup = mo.ui.slider(_first_ok, R - _min_level, value=R - _min_level, step=1, label="step", show_value=True)
    rollup_counts = dict(_steps)
    return rollup, rollup_counts


@app.cell(hide_code=True)
def _(R, aoi, aoi_ms, aoi_tree, b, cell_ha, profile, rollup, rollup_counts):
    _k = rollup.value
    _shown = v.expand_to(aoi_tree.cells(), R - _k)
    _fig = v.tile_map([v.cell_layer(_shown, "cells", by_level=True, opacity=0.6, profile=profile, line=0.3 if len(_shown) < 3000 else 0.1), v.outline(aoi, "study area")], b)
    _icicle, _n_partial, _n_full = v.tree_icicle(aoi_tree, R)
    _rows = []
    for _r in range(5, 12):
        _t0 = time.perf_counter()
        _t = bc.Tree.from_geojson(aoi, _r, profile)
        _rows.append((_r, _t.leaf_count(), len(_t.cells()), 1000 * (time.perf_counter() - _t0), bc.cell_area_m2(_r, profile)))
    _scale = make_subplots(specs=[[{"secondary_y": True}]])
    _scale.add_trace(go.Scatter(x=[r[0] for r in _rows], y=[r[1] for r in _rows], name="zones", mode="lines+markers", line={"color": "#b0b0b0", "width": 2}))
    _scale.add_trace(go.Scatter(x=[r[0] for r in _rows], y=[r[2] for r in _rows], name="compact zones", mode="lines+markers", line={"color": "#54a24b", "width": 3}))
    _scale.add_trace(go.Bar(x=[r[0] for r in _rows], y=[r[3] for r in _rows], name="polygon → root, ms", marker_color="rgba(76,120,168,0.35)"), secondary_y=True)
    _scale.update_layout(height=320, template="plotly_white", margin={"l": 10, "r": 10, "t": 20, "b": 10}, legend={"orientation": "h", "y": 1.12}, xaxis={"title": "resolution (cell area)", "tickvals": [r[0] for r in _rows], "ticktext": [f"{r[0]}<br>{r[4] / 1e4:,.3g} ha" for r in _rows]})
    _scale.update_yaxes(title_text="cells (log)", type="log", secondary_y=False)
    _scale.update_yaxes(title_text="ms", secondary_y=True, showgrid=False)
    mo.vstack(
        [
            mo.md("## 2. Naming the ground: fair cells, rolled up, hashed"),
            v.takeaway(f"**Takeaway.** The survey area becomes {aoi_tree.leaf_count():,} equal-area zones, rolled up to {len(aoi_tree.cells()):,}, and hashed to one root. Anyone with the same polygon, resolution and profile recomputes the same 32 bytes, in {aoi_ms:,.0f} ms."),
            mo.hstack(
                [
                    v.stat(f"{aoi_tree.leaf_count():,}", f"zones at resolution {R}", f"each {cell_ha:,.2f} ha, exactly"),
                    v.stat(f"{len(aoi_tree.cells()):,}", "compact zones", "nine full children become their parent, recursively"),
                    v.stat(aoi_tree.root_hex[:16] + "…", "the root", f"{profile.hash.upper()} over the canonical tree"),
                ],
                widths="equal",
            ),
            mo.hstack([rollup, mo.md(f"**{rollup_counts[_k]:,} cells drawn** · drag left to see every leaf, right to see the canonical form")], align="center", gap=2),
            mo.ui.plotly(_fig),
            mo.accordion(
                {
                    "The hash tree behind the root": mo.vstack([mo.ui.plotly(_icicle), mo.md(f"Grey nodes are partial and hashed from nine children; green nodes are full and hash to a constant. **{_n_partial:,} hash evaluations** produce the root, not {aoi_tree.leaf_count():,}. A region held whole and the same region spelled out leaf by leaf hash identically.")]),
                    "Why the canonical form matters as resolution grows": mo.vstack([mo.ui.plotly(_scale), mo.md(f"Leaf cells grow ×9 per resolution; compact zones grow with the boundary. At resolution {_rows[-1][0]} the area is {_rows[-1][1]:,} leaves but {_rows[-1][2]:,} compact zones. A continent and a field each cost one root.")]),
                }
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(R, b, profile, scenes):
    mo.stop(not scenes, mo.md("## 3. The same ground in any encoding is one root\n\n*No cached scenes for this site.*"))
    import zarr

    _s = scenes[-1]
    _arr, _t = _s["biomass"], _s["transform"]
    _tmp = Path("data_cache") / "encodings"
    _tmp.mkdir(parents=True, exist_ok=True)
    _cog = _tmp / "mask_cog.tif"
    with rasterio.open(_cog, "w", driver="GTiff", height=_arr.shape[0], width=_arr.shape[1], count=1, dtype=_arr.dtype, crs="EPSG:4326", transform=_t, tiled=True, blockxsize=256, blockysize=256, compress="deflate") as _dst:
        _dst.write(_arr, 1)
    _z = zarr.open(str(_tmp / "mask.zarr"), mode="w", shape=_arr.shape, chunks=(64, 64), dtype=_arr.dtype)
    _z[:] = _arr
    _z.attrs["transform"] = list(_t)[:6]
    with rasterio.open(_cog) as _a:
        _cog_arr, _cog_t = _a.read(1), _a.transform
    _zb = zarr.open(str(_tmp / "mask.zarr"), mode="r")
    _zarr_arr, _zarr_t = _zb[:], rasterio.Affine(*_zb.attrs["transform"])
    root_cog = bc.fingerprint_polygon(v.footprint(_cog_arr, _cog_t), R, profile)
    root_zarr = bc.fingerprint_polygon(v.footprint(_zarr_arr, _zarr_t), R, profile)
    _zarr_files = [p for p in (_tmp / "mask.zarr").rglob("*") if p.is_file()]

    def _heat(arr, t, title, step=2):
        arr = arr[::step, ::step]
        _h, _w = arr.shape
        return go.Figure(go.Heatmap(z=np.where(np.isnan(arr), None, arr), x=t.c + t.a * step * np.arange(_w), y=t.f + t.e * step * np.arange(_h), colorscale="YlGn", zmin=0, zmax=180, showscale=False, hovertemplate="%{z:.0f} Mg/ha<extra></extra>")).update_layout(title={"text": title, "font": {"size": 13}}, margin={"l": 0, "r": 0, "t": 30, "b": 0}, height=300, xaxis={"visible": False}, yaxis={"visible": False, "scaleanchor": "x"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0b1d2a")

    mo.vstack(
        [
            mo.md("## 3. The same ground in any encoding is one root"),
            v.takeaway(f"**Takeaway.** The {_s['date']} biomass map written as a tiled COG and as a chunked Zarr store: two files, one footprint, one root. Re-tile it, re-compress it, move it between object stores; the identity does not move."),
            mo.hstack([mo.ui.plotly(_heat(_cog_arr, _cog_t, f"COG · 256² tiles · deflate · {_cog.stat().st_size:,} bytes")), mo.ui.plotly(_heat(_zarr_arr, _zarr_t, f"Zarr · 64² chunks · {len(_zarr_files)} files"))], widths="equal"),
            mo.hstack([v.stat(root_cog[:16] + "…", "root of the COG"), v.stat(root_zarr[:16] + "…", "root of the Zarr"), v.stat("identical" if root_cog == root_zarr else "DIFFERENT", "verdict")], widths="equal"),
        ]
    )
    return


@app.cell(hide_code=True)
def _(aoi_tree):
    _canon = aoi_tree.cells()
    _inside = bc.cid_to_suid(min(_canon, key=v.level_of)) if _canon else "Q"
    pick = mo.ui.text(value=_inside + "4", label="Cell id")
    mo.hstack([pick, mo.md("Try a cell inside the study area, one far outside it (`N4`, `S0`), or an ancestor that straddles the edge.")], align="center", gap=2)
    return (pick,)


@app.cell(hide_code=True)
def _():
    _f = Path("docs/img/crossings.json")
    mo.stop(not _f.exists(), mo.md("## 4. You only lose on entering the system\n\n*Run `uv run python scripts/crossings.py` first.*"))
    _d = json.loads(_f.read_text())
    _bulk = [r for r in _d["bulk"] if "iou" in r]
    _fig = go.Figure()
    _fig.add_trace(go.Scatter(x=[r["hop"] for r in _bulk], y=[100 * r["iou"] for r in _bulk], mode="lines+markers", name="break-bulk: reprojected at every hop (overlap with the original)", line={"color": "#e45756", "width": 3}))
    _fig.add_trace(go.Scatter(x=[r["hop"] for r in _d["bulk"]], y=[r["area_pct"] for r in _d["bulk"]], mode="lines", name="break-bulk: area retained", line={"color": "#e45756", "width": 1.5, "dash": "dot"}))
    _fig.add_trace(go.Scatter(x=[c["op"] for c in _d["container"]], y=[100 * _d["entry_iou"]] * len(_d["container"]), mode="lines+markers", name="container: fingerprinted once, then the same number of operations (root unchanged every time)", line={"color": "#54a24b", "width": 3}))
    _fig.update_layout(height=420, margin={"l": 50, "r": 20, "t": 30, "b": 40}, template="plotly_white", legend={"orientation": "h", "y": -0.25}, xaxis={"title": "handlings (reprojection hops, or set operations)", "dtick": 2}, yaxis={"title": "% of the original", "range": [min(88, 100 * min(r["iou"] for r in _bulk) - 3), 101]})
    _moved = 100 * (1 - _bulk[-1]["iou"])
    _area_drift = max(abs(100 - r["area_pct"]) for r in _d["bulk"])
    mo.vstack(
        [
            mo.md("## 4. You only lose on entering the system"),
            v.takeaway(f"**Takeaway.** The same mangrove mask, two routes. Break-bulk: reprojected through twenty hops of the kind data really makes (UTM at 30 m, WGS84, Web Mercator at 60 m, a different WGS84 grid, UTM at 50 m, round again): after twenty handlings {_moved:.1f} % of the forest is in the wrong place while every area total stayed within {_area_drift:.1f} %, so a summary table would never notice and a change detector would report change that never happened. Container: fingerprinted once at level {_d['level']} (entry cost {100 * (1 - _d['entry_iou']):.1f} % of overlap, paid once), then twenty operations: root `{_d['root'][:16]}…` every time, {_d['container'][0]['zones']:,} zones every time. Loss stops at one."),
            mo.hstack([v.stat(f"{_moved:.1f} %", "of the forest moved", "after twenty reprojection hops"), v.stat(f"{_area_drift:.2f} %", "worst drift in area", "the totals look fine"), v.stat("0", "operations that changed the root", "out of twenty")], widths="equal"),
            mo.ui.plotly(_fig),
            mo.image("docs/img/crossings_masks.jpg", caption="the mask as computed, and after twenty hops: lost in red, gained in blue. The creeks are gone."),
            mo.accordion({"Why this grid: a hexagon's children straddle it, a square's children partition it": mo.image("docs/img/nesting.jpg")}),
        ]
    )
    return


@app.cell(hide_code=True)
def _(aoi_tree, b, pick, profile):
    try:
        _cid = bc.suid_to_cid(pick.value.strip())
    except ValueError as e:
        _cid = None
        _err = str(e)
    mo.stop(_cid is None, mo.md(f"*`{pick.value}` is not a cell id.*"))
    _rec = aoi_tree.open(_cid)
    _lvl = v.level_of(_cid)
    if _rec is None:
        _verdict, _colour, _detail = "PARTLY COVERED", "#b279a2", f"`{pick.value}` straddles the edge of the study area: some of its leaves are covered and some are not, so it has no single yes-or-no. Ask about one of its children."
        _extra = None
    else:
        _kind = v.claim_of(_rec)
        _ok = bc.verify_opening(_rec)
        _bad = json.loads(json.dumps(_rec))
        _bad["root"] = "00" * 32
        _verdict = "INSIDE" if _kind == "full" else "OUTSIDE"
        _colour = "#54a24b" if _kind == "full" else "#e45756"
        _detail = (
            f"`{pick.value}` is **{_verdict.lower()}** the study area's coverage. The proof is {len(json.dumps(_rec)):,} bytes, checks against the root "
            f"({_ok}) and fails against a forged root ({bc.verify_opening(_bad)}). Nobody needed the polygon, the raster or the tree to check it: only the root."
        )
        _extra = mo.accordion({"What the proof contains": mo.vstack([mo.md("The path from the root to the cell: six base hashes, then nine sibling hashes per level with the opened position marked. A verifier recomputes upward and compares with the root; the cell a proof names is the sequence of opened positions, so it cannot be relabelled."), v.opening_ladder(_rec)])})
    _map = v.tile_map([v.cell_layer(aoi_tree.cells(), "study area cells", color="#eeca3b", opacity=0.35, profile=profile), v.cell_layer([_cid], pick.value, color=_colour, opacity=0.9, line=2, profile=profile)], b, height=380)
    mo.vstack(
        [
            mo.md("## 5. The root answers questions without the data"),
            v.takeaway("**Takeaway.** Hand someone the root and they can ask *is this cell inside?* and get an answer they can check, for any cell, without the polygon or the raster. Absence is proven the same way as presence."),
            mo.hstack(
                [
                    mo.vstack([mo.Html(f'<div style="font:600 34px system-ui;color:{_colour};margin:6px 0">{_verdict}</div>'), mo.md(_detail)] + ([_extra] if _extra else [])),
                    mo.ui.plotly(_map),
                ],
                widths=[1, 1.1],
                align="start",
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(R, aoi, aoi_tree, b, n_aoi, profile, scenes, then):
    mo.stop(not scenes, mo.md("## 6. Four passes, one comparable region\n\n*No cached scenes for this site.*"))
    comparable = v.common_ground(scenes)
    _groups = {}
    for _s in scenes:
        _groups.setdefault(_s["valid"].root_hex, []).append(_s)

    def _panel(ss, comp, title):
        _tr = [v.cell_layer(_s["valid"].cells(), _s["date"], color=v.PALETTE[i % 4], opacity=0.3, line=0, profile=profile) for i, _s in enumerate(ss)]
        _tr += [v.cell_layer(comp.cells(), "comparable region", color="#ffffff", opacity=0.6, line=0.2, profile=profile), v.outline(aoi, "study area")]
        _f = v.tile_map(_tr, b, height=400)
        _f.update_layout(title={"text": title, "font": {"size": 13}, "x": 0.02, "y": 0.98}, showlegend=False, margin={"t": 28})
        return _f

    _cov = lambda ss: ", ".join(f"{100 * _s['valid'].leaf_count() / n_aoi:.0f}%" for _s in ss)
    _panels = [mo.ui.plotly(_panel(scenes, comparable, f"chosen by ground (2026): scenes cover {_cov(scenes)} · comparable {100 * comparable.leaf_count() / n_aoi:.0f}%"))]
    if then:
        _old_comp = v.common_ground(then)
        _panels.insert(0, mo.ui.plotly(_panel(then, _old_comp, f"chosen by cloud cover (2025): {_cov(then)} · comparable {100 * _old_comp.leaf_count() / n_aoi:.0f}%")))
    _dates = [_s["date"] for _s in scenes]
    _naive = [100 * _s["mask"].leaf_count() / max(_s["valid"].leaf_count(), 1) for _s in scenes]
    _fair = [100 * _s["mask"].intersect(comparable).leaf_count() / max(comparable.leaf_count(), 1) for _s in scenes]
    _bars = go.Figure([go.Bar(name="of the scene's own valid area", x=_dates, y=_naive, marker_color="#b0b0b0", text=[f"{x:.0f}%" for x in _naive], textposition="outside"), go.Bar(name="of the comparable region", x=_dates, y=_fair, marker_color="#54a24b", text=[f"{x:.0f}%" for x in _fair], textposition="outside")]).update_layout(barmode="group", height=300, margin={"l": 10, "r": 10, "t": 30, "b": 10}, yaxis={"title": "mangrove cells, %", "range": [0, 105]}, legend={"orientation": "h", "y": 1.15}, template="plotly_white")
    mo.vstack(
        [
            mo.md("## 6. Four passes, one comparable region"),
            v.takeaway(f"**Takeaway.** Nobody sees the whole area in one pass. Each scene's footprint is a root; the region they all saw is the intersection, computed, not assumed. And scenes are now *chosen* by how much of the area their footprint covers, before any download: the 2025 report's own first recommendation."),
            mo.hstack(_panels, widths="equal"),
            mo.ui.plotly(_bars),
            mo.md(f"Grey bars are what each scene says about itself; green bars are the number that means the same thing on every date. {len(scenes)} scenes, {len(_groups)} distinct footprint roots: scenes from one Sentinel-2 tile share a root to the byte."),
        ]
    )
    return (comparable,)


@app.cell(hide_code=True)
def _(R, b, comparable, profile, scenes):
    mo.stop(not scenes)
    _first, _last = scenes[0], scenes[-1]
    _m0, _m1 = _first["mask"].intersect(comparable), _last["mask"].intersect(comparable)
    lost, gained, stable = _m0.difference(_m1), _m1.difference(_m0), _m0.intersect(_m1)
    _ha = bc.cell_area_m2(R, profile) / 1e4
    _proof = _m0.prove(_m1, "difference")
    _bad = json.loads(json.dumps(_proof))
    _bad["op"] = "union"
    mo.vstack(
        [
            mo.md(f"## 7. Change is a set difference, {_first['date']} → {_last['date']}"),
            v.takeaway(f"**Takeaway.** Two roots, one difference: {lost.leaf_count() * _ha:,.0f} ha lost, {gained.leaf_count() * _ha:,.0f} ha gained, {stable.leaf_count() * _ha:,.0f} ha stable, on cells that are the same size everywhere, with a transcript a verifier replays without seeing either mask. The first thing this diff found was a processing artifact in our own pipeline."),
            mo.ui.plotly(v.tile_map([v.cell_layer(comparable.cells(), "comparable region", color="#ffffff", opacity=0.12, line=0, profile=profile), v.cell_layer(stable.cells(), "mangrove on both dates", color="#54a24b", opacity=0.6, line=0, profile=profile), v.cell_layer(lost.cells(), "lost", color="#e45756", opacity=0.85, line=0, profile=profile), v.cell_layer(gained.cells(), "gained", color="#4c78a8", opacity=0.85, line=0, profile=profile)], b, height=520)),
            mo.md(f"Transcript: {len(json.dumps(_proof)) // 1024} kB, verifies {bc.verify_setop(_proof)}; with the operation swapped it verifies {bc.verify_setop(_bad)}. *(The dates mix season and disturbance; the claim here is comparability, not the trend.)*"),
        ]
    )
    return


@app.cell(hide_code=True)
def _(R, aoi_tree, b, n_aoi, profile, scenes, then):
    mo.stop(not scenes)
    _obs = {}
    for _s in then + scenes:
        _obs[_s["scene_id"]] = _s
    _obs = sorted(_obs.values(), key=lambda s: s["date"], reverse=True)
    _seen, _contrib = None, []
    for _s in _obs:
        _new = _s["valid"] if _seen is None else _s["valid"].difference(_seen)
        _seen = _s["valid"] if _seen is None else _seen.union(_s["valid"])
        if not _new.is_empty():
            _contrib.append((_s, _new))
    _gap = aoi_tree.difference(_seen)
    _tr = [v.cell_layer(_new.cells(), f"{_s['date']} · {_s['scene_id'][4:9]}", color=v.PALETTE[i % len(v.PALETTE)], opacity=0.7, line=0, profile=profile) for i, (_s, _new) in enumerate(_contrib)]
    if not _gap.is_empty():
        _tr.append(v.cell_layer(_gap.cells(), "never observed", color="#222222", opacity=0.55, line=0, profile=profile))
    _tr.append(v.outline(v.bbox_polygon(b), "study area"))
    _ix = bc.Index()
    for _s in _obs:
        _ix.add(_s["scene_id"], _s["valid"])
    _revisit = v.tile_map([v.count_layer(_ix.attention(R - 2), "observations", profile, "observations"), v.outline(v.bbox_polygon(b), "study area")], b, height=400)
    mo.vstack(
        [
            mo.md("## 8. Looking is not seeing: the observation ledger"),
            v.takeaway(f"**Takeaway.** Every scene ever selected for this site, most recent first, contributes the cells no later scene saw: a best-available-pixel composite whose provenance is {len(_contrib)} root{'s' if len(_contrib) != 1 else ''} rather than a paragraph. {100 * _seen.leaf_count() / n_aoi:.0f} % of the area has been seen at all; the rest is itself a root you can query. Cloud masking is one more mask in the same algebra."),
            mo.hstack([mo.ui.plotly(v.tile_map(_tr, b, height=400)), mo.ui.plotly(_revisit)], widths="equal"),
            mo.md("Left: which observation each cell's best pixel comes from. Right: how many observations touched each cell, the revisit density."),
        ]
    )
    return


@app.cell(hide_code=True)
def _(R, profile):
    catalog = bc.Index()
    catalog_meta = {}
    jobs = {}
    for _site, _b in v.STUDY_SITES.items():
        _slug = v.slug(_site)
        _aoi = bc.Tree.from_geojson(v.bbox_polygon(_b), R, profile)
        catalog.add(f"{_slug}/aoi", _aoi)
        catalog_meta[f"{_slug}/aoi"] = {"site": _site, "lineage": "study area bbox", "date": ""}
        for _s in v.load_scenes(Path("data_cache") / "temporal" / _slug, R, profile):
            for _lineage, _tree in (("Sentinel-2 valid data", _s["valid"]), ("mangrove mask (NDVI)", _s["mask"])):
                _key = f"{_slug}/{_s['scene_id']}/{'valid' if _lineage.startswith('Sentinel') else 'mangrove'}"
                catalog.add(_key, _tree)
                catalog_meta[_key] = {"site": _site, "lineage": _lineage, "date": _s["date"]}
            jobs[f"{_slug}/{_s['scene_id']}"] = {"site": _site, "date": _s["date"], "aoi": _aoi, "computed": _s["valid"], "mask": _s["mask"]}
    return catalog, catalog_meta, jobs


@app.cell(hide_code=True)
def _(R, aoi_tree, b, catalog, catalog_meta, profile, site):
    _hits = catalog.query(aoi_tree)
    _rows = [{"entry": _h["key"], "lineage": catalog_meta[_h["key"]]["lineage"], "date": catalog_meta[_h["key"]]["date"], "relation": _h["relation"], "covers % of my ground": round(100 * _h["fraction_of_query"], 1), "% of it in my ground": round(100 * _h["fraction_of_item"], 1)} for _h in _hits]
    _lineages = sorted({r["lineage"] for r in _rows if r["lineage"] != "study area bbox"})
    _regional = v.region_map([v.count_layer(catalog.attention(5), "entries", profile)], {"lon": 97.5, "lat": 16.0}, 4.1, height=420)
    _local = v.tile_map([v.count_layer(catalog.attention(max(R - 2, 5)), "entries", profile), v.outline(v.bbox_polygon(b), "study area")], b, height=420)
    mo.vstack(
        [
            mo.md("## 9. A catalogue that indexes roots"),
            v.takeaway(f"**Takeaway.** {len(catalog)} entries across four sites, {catalog.distinct_roots} distinct roots, and the index never sees a coordinate. Ask *what covers {site}?* and every hit comes with two exact fractions a bbox search cannot give. Roll the entries up and count, and the catalogue draws where the effort is."),
            mo.ui.table(_rows, selection=None, page_size=8),
            mo.md(f"**{len(_lineages)} distinct lineages** have outputs over this ground ({', '.join(_lineages)}). Same ground, different lineage is the consilience query."),
            mo.hstack([mo.ui.plotly(_regional), mo.ui.plotly(_local)], widths="equal"),
            mo.md("Left: entries per 1,440 km² cell across the region. Right: the same count at site scale. A group that does not want to publish an exact footprint can publish its coarse cells and still appear here."),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    _presets = {
        "the study area bbox, redrawn 20 % further east by a colleague": "east",
        "exactly the study area bbox (a re-run)": "same",
        "somewhere nobody has run: the Mekong delta": "new",
    }
    request = mo.ui.dropdown(options=_presets, value=list(_presets)[0], label="Incoming request: run the workflow over")
    request  # noqa: B018
    return (request,)


@app.cell(hide_code=True)
def _(R, b, jobs, profile, request):
    _w = b["east"] - b["west"]
    _rb = {"east": {**b, "west": b["west"] + 0.2 * _w, "east": b["east"] + 0.2 * _w}, "same": b, "new": {"west": 105.6, "south": 9.6, "east": 105.9, "north": 9.9}}[request.value]
    req = bc.Tree.from_geojson(v.bbox_polygon(_rb), R, profile)
    _ledger = bc.Index()
    for _k, _j in jobs.items():
        _ledger.add(_k, _j["computed"])
    _hits = _ledger.query(req)
    served = None
    for _h in _hits:
        _t = jobs[_h["key"]]["computed"].intersect(req)
        served = _t if served is None else served.union(_t)
    delta = req.difference(served) if served else req
    _n, _sn = req.leaf_count(), (served.leaf_count() if served else 0)
    _tr = [v.cell_layer(req.cells(), "requested", color="#ffffff", opacity=0.15, line=0.2, profile=profile)]
    if served:
        _tr.append(v.cell_layer(served.cells(), "already computed: serve from the catalogue", color="#54a24b", opacity=0.6, line=0, profile=profile))
    if not delta.is_empty():
        _tr.append(v.cell_layer(delta.cells(), "not yet computed: execute only this", color="#e45756", opacity=0.75, line=0, profile=profile))
    _tr.append(v.outline(v.bbox_polygon(_rb), "request"))
    _decision = "serve it entirely from the catalogue" if delta.is_empty() else ("execute the whole request" if _sn == 0 else f"execute the {100 * delta.leaf_count() / _n:.0f} % that is new, serve the rest")
    mo.vstack(
        [
            mo.md("## 10. What the platform gains: execute only new ground"),
            v.takeaway(f"**Takeaway.** A job is its workflow hash plus the root of the ground it computed. This request is one query against the ledger of {len(jobs)} prior runs: {100 * _sn / max(_n, 1):.0f} % already computed, so the decision is to {_decision}. Compute stops scaling with how many people ask and scales with how much ground is new."),
            mo.ui.plotly(v.tile_map(_tr, _rb, height=460)),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    egress_price = mo.ui.slider(0.02, 0.12, value=0.09, step=0.01, label="egress price, $/GB", show_value=True)
    agency_tb = mo.ui.slider(10, 5000, value=500, step=10, label="an agency's annual egress, TB", show_value=True)
    mo.hstack([egress_price, agency_tb], gap=2)
    return agency_tb, egress_price


@app.cell(hide_code=True)
def _(R, agency_tb, egress_price, jobs, profile):
    _cell_px = bc.cell_area_m2(R, profile) / 100.0
    _mb = lambda cells: cells * _cell_px * 3 * 2 / 1e6  # three uint16 bands at 10 m
    _rows = []
    for _site, _b in v.STUDY_SITES.items():
        _runs = [(k, j) for k, j in jobs.items() if k.startswith(v.slug(_site) + "/")]
        if not _runs:
            continue
        _aoi = _runs[0][1]["aoi"]
        _shifted = bc.Tree.from_geojson(v.bbox_polygon({**_b, "west": _b["west"] + 0.2 * (_b["east"] - _b["west"]), "east": _b["east"] + 0.2 * (_b["east"] - _b["west"])}), R, profile)
        _served = None
        for _, _j in _runs:
            _t = _j["computed"].intersect(_shifted)
            _served = _t if _served is None else _served.union(_t)
        _rows.append({"site": _site, "as a bbox (today)": _mb(_aoi.leaf_count() * len(_runs)), "as the pixels of interest": _mb(sum(j["mask"].intersect(_aoi).leaf_count() for _, j in _runs)), "as a delta on a repeat request": _mb(_shifted.difference(_served).leaf_count() * len(_runs))})
    _cats = ["as a bbox (today)", "as the pixels of interest", "as a delta on a repeat request"]
    _fig = go.Figure([go.Bar(name=c, x=[r["site"] for r in _rows], y=[r[c] for r in _rows], marker_color=["#b0b0b0", "#54a24b", "#1b1b3a"][i], text=[f"{r[c]:,.0f}" for r in _rows], textposition="outside") for i, c in enumerate(_cats)])
    _fig.update_layout(barmode="group", height=340, template="plotly_white", yaxis={"title": "MB moved per 4-date request"}, legend={"orientation": "h", "y": 1.15}, margin={"l": 10, "r": 10, "t": 20, "b": 10})
    _tot = {c: sum(r[c] for r in _rows) / len(_rows) for c in _cats}
    _f_interest = 1 - _tot["as the pixels of interest"] / _tot["as a bbox (today)"]
    _f_delta = 1 - _tot["as a delta on a repeat request"] / _tot["as a bbox (today)"]
    _agency_usd = agency_tb.value * 1000 * egress_price.value
    mo.vstack(
        [
            mo.md("## 11. Cloud in, cloud out: request the ground, not the box"),
            v.takeaway(f"**Takeaway.** Today the operator answers a request with a bounding box and every byte in it moves, needed or not. Stated as cells of interest, a request moves {100 * _f_interest:.0f} % fewer bytes; as a delta on a repeat, {100 * _f_delta:.0f} % fewer. At {agency_tb.value:,} TB of annual egress and ${egress_price.value:.2f}/GB that is ${_agency_usd * _f_interest:,.0f} and ${_agency_usd * _f_delta:,.0f} a year. Both sides hold the same root, so the reply is also a receipt."),
            mo.ui.plotly(_fig),
            mo.md("Bars are this repository's own sites: four dates, three bands at 10 m, all counted in the same equal-area zones. The sliders above set the price and scale; the fractions hold at any scale."),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    _items = sorted(f for f in Path("outputs").glob("*/*.json") if not f.name.endswith("fingerprint.json")) if Path("outputs").exists() else []
    _stamped = []
    for _f in _items:
        try:
            _d = json.loads(_f.read_text())
        except json.JSONDecodeError:
            continue
        if "fingerprint:root" in _d.get("properties", {}):
            _stamped.append((_f, _d))
    mo.stop(not _stamped, mo.md("## 12. What travels with the number\n\n*No fingerprinted STAC item under `outputs/` yet; run the application package.*"))
    _f, _d = _stamped[-1]
    _item = pystac.Item.from_file(str(_f))
    _ext = fp.FingerprintExtension.ext(_item)
    _level = _ext.zone_level
    _, _, _profile = _ext.burin_profile()
    _geom_tree = bc.Tree.from_geojson(_item.geometry, _level, _profile)
    _mask_key = next((k for k, a_ in _item.assets.items() if "mask" in k and fp.ROOT_PROP in a_.extra_fields), None)
    _mask_ext = fp.FingerprintExtension.ext(_item.assets[_mask_key]) if _mask_key else None
    _mask_doc = json.loads((_f.parent / f"{_mask_key}_fingerprint.json").read_text()) if _mask_key else None
    _mask_tree = fp.tree_from_zone_list(_mask_doc, _mask_ext.zone_level, _profile) if _mask_doc else None
    _verified = fp.FingerprintExtension.verify(_item, {_mask_key: ba.footprint_from_asset(_item, _mask_key)} if _mask_key else None)
    _bb = {"west": _d["bbox"][0], "south": _d["bbox"][1], "east": _d["bbox"][2], "north": _d["bbox"][3]}
    _rows = [
        ("item geometry, the package", "Linux container via cwltool, the fingerprint step", _ext.root),
        ("item geometry, this notebook", "Python wheel, macOS, from the item JSON alone", _geom_tree.root_hex),
    ]
    if _mask_tree is not None:
        _rows += [
            (f"{_mask_key}, the package", "from the mask's pixels, in the container", _mask_ext.root),
            (f"{_mask_key}, this notebook", f"the zone list asset rebuilt and hashed ({len(_mask_doc['zones'])} compact zones)", _mask_tree.root_hex),
        ]
    _golden = Path("../burin-core/crates/burin-core/tests/fixtures/roots.json")
    if _golden.exists():
        _case = next((p for p in json.loads(_golden.read_text())["polygons"] if p["name"] == "london" and p["profile"] == "ogc"), None)
        if _case:
            _rows += [("London fixture, the Rust test suite", "frozen golden vector", _case["root"]), ("London fixture, this notebook", "Python wheel", bc.fingerprint_polygon(_case["geometry"], _case["resolution"]))]
    _table = "| fingerprint of | computed | root |\n|---|---|---|\n" + "\n".join(f"| {a_} | {w} | `{r[:20]}…` |" for a_, w, r in _rows)
    _props = {k: v_ for k, v_ in _d["properties"].items() if k.startswith("fingerprint:")}
    _layers = [v.cell_layer(_geom_tree.cells(), f"item geometry: the valid-data footprint · level {_level}", by_level=True, opacity=0.35)]
    if _mask_tree is not None:
        _layers.append(v.cell_layer(_mask_tree.cells(), f"{_mask_key}: the detected extent · level {_mask_ext.zone_level}", color="#2ca02c", opacity=0.75))
    _layers.append(v.outline(_d["geometry"], "item geometry"))
    mo.vstack(
        [
            mo.md("## 12. What travels with the number"),
            v.takeaway(f"**Takeaway.** The application package plus one CWL step at the end, and the STAC item carries the Fingerprint extension in OGC API - DGGS words: the item's fingerprint is the root of its geometry's compact zone list on the OGC-registered rHEALPix DGGRS at refinement level {_level}; the mask asset carries the fingerprint of the ground it detected; both zone lists travel as assets. Verified here from the JSON alone ({', '.join(_verified)}): the same roots on this laptop, in the Linux container, and in the Rust test suite, to the byte."),
            mo.hstack(
                [
                    mo.md("```json\n" + json.dumps(_props, indent=2) + "\n```\n\n" + _table),
                    mo.ui.plotly(v.tile_map(_layers, _bb, height=360)),
                ],
                widths=[1.1, 1],
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.vstack(
        [
            mo.md("## 13. The ask"),
            mo.callout(
                mo.md(
                    "**Three packages, each one file.** A STAC extension of three fields, so ground becomes a primary key (`stac-extension/`). "
                    "A coverage index behind the catalogue, so overlap becomes a fair fraction and jobs execute only new ground (`burin_core.Index`). "
                    "One platform-level step after every execution (`cwl/fingerprint.cwl`), so all of this appears without any workflow author changing anything.\n\n"
                    "STAC gives the primitive a ledger and a transport. The primitive gives STAC an identity for ground."
                ),
                kind="success",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
