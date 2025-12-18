import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import json
    import warnings
    from datetime import datetime
    from pathlib import Path

    import geopandas as gpd
    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import rioxarray
    import stackstac
    import xarray as xr
    from lonboard import Map, PolygonLayer
    from plotly.subplots import make_subplots
    from pystac_client import Client
    from scipy import stats
    from shapely.geometry import box

    warnings.filterwarnings("ignore")


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    # Mangrove Biomass Temporal Analysis

    This notebook analyzes mangrove biomass change over time using Sentinel-2 satellite imagery (2017-present).

    **Features:**
    - Select from validated study sites with published biomass data
    - View study area as OGC Building Block parameters
    - Sample ~20 scenes across Sentinel-2's operational history
    - Visualize biomass change with interactive timelapse
    - Compare initial vs current measurements

    All data is open access from ESA/AWS - no API keys required.
    """
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    First, let's define our study sites:
    """
    )
    return


@app.cell
def _():
    STUDY_SITES = {
        "Thor Heyerdahl Climate Park": {
            "center": (95.25, 16.0),
            "bounds": {"west": 95.15, "east": 95.35, "south": 15.9, "north": 16.1},
            "country": "Myanmar",
            "description": "1,800 acres of mangrove restoration in Ayeyarwady Delta",
            "published_agc": None,
        },
        "Can Gio Biosphere Reserve": {
            "center": (106.89, 10.52),
            "bounds": {"west": 106.73, "east": 107.05, "south": 10.35, "north": 10.68},
            "country": "Vietnam",
            "description": "UNESCO Biosphere Reserve, 75,740 ha with consistent monitoring",
            "published_agc": "Fringe: 102±24.7, Transition: 298.1±14.1, Interior: 243.6±40.4 Mg C/ha",
        },
        "Sundarbans": {
            "center": (89.46, 22.0),
            "bounds": {"west": 89.0, "east": 89.92, "south": 21.5, "north": 22.5},
            "country": "Bangladesh/India",
            "description": "World's largest mangrove forest, varies by salinity zone",
            "published_agc": "24-119 Mg C/ha (salinity dependent), Mean AGB: 243.4 Mg/ha",
        },
        "Wunbaik Reserved Forest": {
            "center": (94.5, 16.75),
            "bounds": {"west": 94.3, "east": 94.7, "south": 16.6, "north": 16.9},
            "country": "Myanmar (Rakhine State)",
            "description": "Source region for biomass equation (250.5×NDVI - 75.2)",
            "published_agc": "Equation source: R²=0.72 (⚠️ citation unverified)",
        },
    }
    return (STUDY_SITES,)


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    Select a study site:
    """
    )
    return


@app.cell(hide_code=True)
def _(STUDY_SITES):
    site_dropdown = mo.ui.dropdown(
        options=list(STUDY_SITES.keys()),
        value=list(STUDY_SITES.keys())[0],
        label="Study Site:",
    )
    site_dropdown  # noqa: B018
    return (site_dropdown,)


@app.cell(hide_code=True)
def _(STUDY_SITES, site_dropdown):
    selected_site = site_dropdown.value
    site_info = STUDY_SITES[selected_site]
    _bounds = site_info["bounds"]

    # OGC Building Block style display
    bbox_yaml = f"""```yaml
    # OGC Building Block Parameters
    bbox:
      west: {_bounds["west"]}
      south: {_bounds["south"]}
      east: {_bounds["east"]}
      north: {_bounds["north"]}
    crs: EPSG:4326
    collection: sentinel-2-l2a
    ```"""

    published_info = ""
    if site_info.get("published_agc"):
        published_info = f"\n**Published AGC:** {site_info['published_agc']}"

    mo.md(
        f"""
    ## {selected_site}

    **Location:** {site_info['country']}

    **Description:** {site_info['description']}{published_info}

    {bbox_yaml}
    """
    )
    return selected_site, site_info


@app.cell(hide_code=True)
def _(selected_site, site_info):
    # Create lonboard map showing study area
    _bounds = site_info["bounds"]
    _bbox_polygon = box(
        _bounds["west"], _bounds["south"], _bounds["east"], _bounds["north"]
    )

    _bbox_gdf = gpd.GeoDataFrame(
        {"name": [selected_site], "type": ["study_area"]},
        geometry=[_bbox_polygon],
        crs="EPSG:4326",
    )

    _layer = PolygonLayer.from_geopandas(
        _bbox_gdf,
        get_fill_color=[100, 180, 100, 80],  # Semi-transparent green
        get_line_color=[0, 120, 0, 255],  # Dark green border
        line_width_min_pixels=3,
    )

    _center = site_info["center"]
    # Calculate zoom based on bbox size
    _lon_span = _bounds["east"] - _bounds["west"]
    _lat_span = _bounds["north"] - _bounds["south"]
    _max_span = max(_lon_span, _lat_span)
    _zoom = max(1, min(14, 9 - np.log2(_max_span + 0.01)))

    _view_state = {
        "longitude": _center[0],
        "latitude": _center[1],
        "zoom": _zoom,
    }

    _study_area_map = Map(_layer, view_state=_view_state)
    _study_area_map  # noqa: B018
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Temporal Analysis Configuration

    Configure the temporal sampling parameters:
    """
    )
    return


@app.cell(hide_code=True)
def _():
    max_cloud_cover = mo.ui.slider(
        10, 50, value=30, step=5, label="Max Cloud Cover (%):", show_value=True
    )
    max_cloud_cover  # noqa: B018
    return (max_cloud_cover,)


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    Temporal analysis samples **3 key points** from Sentinel-2's operational history:
    - **Initial** (2017): First available low-cloud scene
    - **Midpoint** (2020-2021): Mid-operational baseline
    - **Current** (2024): Most recent measurement

    This enables quick change detection (~2-3 min) while capturing the full trend.
    """
    )
    return


@app.cell(hide_code=True)
def _():
    load_temporal_button = mo.ui.run_button(label="🛰️ Load Temporal Data (~2-3 min)")
    load_temporal_button  # noqa: B018
    return (load_temporal_button,)


@app.cell
def _(load_temporal_button, max_cloud_cover, selected_site, site_info):
    mo.stop(
        not load_temporal_button.value,
        mo.md("*Click 'Load Temporal Data' to begin temporal analysis*"),
    )

    # 3 strategic time windows: Initial, Midpoint, Current
    _time_windows = [
        ("Initial (2017)", "2017-01-01", "2017-12-31"),
        ("Midpoint (2020-21)", "2020-06-01", "2021-06-01"),
        ("Current (2024)", "2024-01-01", "2024-12-31"),
    ]

    print("Querying 3 key time points for change detection...")

    # Setup
    _catalog = Client.open("https://earth-search.aws.element84.com/v1")
    _bounds = site_info["bounds"]
    _bbox = [_bounds["west"], _bounds["south"], _bounds["east"], _bounds["north"]]

    # Cache directory for temporal data
    _site_slug = selected_site.lower().replace(" ", "_")
    _cache_dir = Path("data_cache") / "temporal" / _site_slug
    _cache_dir.mkdir(parents=True, exist_ok=True)

    _temporal_samples = []

    for _i, (_label, _start_str, _end_str) in enumerate(_time_windows):
        print(f"  [{_i+1}/3] {_label}: Searching...", end=" ")

        _search = _catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=_bbox,
            datetime=f"{_start_str}/{_end_str}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover.value}},
            limit=10,
        )

        _items = list(_search.items())
        if not _items:
            print("no scenes")
            continue

        # Select items with lowest cloud cover (sort client-side)
        _items.sort(key=lambda x: x.properties.get("eo:cloud_cover", 100))

        # Try items until we find one with valid data
        for _item in _items[:5]:  # Try up to 5 scenes per time window
            _scene_id = _item.id
            _scene_date = _item.datetime
            _cloud = _item.properties.get("eo:cloud_cover", 0)

            # Check scene cache
            _scene_cache_dir = _cache_dir / _scene_id
            _stats_file = _scene_cache_dir / "stats.json"

            if _stats_file.exists():
                # Load from cache
                with open(_stats_file) as _f:
                    _sample = json.load(_f)
                    _sample["date"] = datetime.fromisoformat(_sample["date"])
                _temporal_samples.append(_sample)
                print(
                    f"found {_scene_date.strftime('%Y-%m-%d')} ({_cloud:.1f}% cloud) [cached]"
                )
                break  # Found valid cached scene

            # Download and process
            print(f"trying {_scene_date.strftime('%Y-%m-%d')}...", end=" ")
            _scene_cache_dir.mkdir(parents=True, exist_ok=True)

            _cache_files = {
                "red": _scene_cache_dir / "red.tif",
                "green": _scene_cache_dir / "green.tif",
                "nir": _scene_cache_dir / "nir.tif",
            }

            if all(_f.exists() for _f in _cache_files.values()):
                _bands_data = {}
                for _band_name, _filepath in _cache_files.items():
                    with rioxarray.open_rasterio(_filepath) as _src:
                        _bands_data[_band_name] = _src.values[0]
            else:
                _sentinel2_lazy = stackstac.stack(
                    [_item],
                    assets=["red", "green", "nir"],
                    epsg=4326,
                    resolution=0.0005,  # Lower res for speed (50m)
                    bounds_latlon=_bbox,
                    chunksize=(1, 1, 512, 512),
                )
                _data = _sentinel2_lazy.compute()

                _bands_data = {}
                for _band_name in ["red", "green", "nir"]:
                    _band = _data.sel(band=_band_name)
                    if "time" in _band.dims:
                        _band = _band.isel(time=0)
                    _bands_data[_band_name] = _band.values
                    _band_xr = _band.rio.write_crs("EPSG:4326")
                    _band_xr.rio.to_raster(_cache_files[_band_name], compress="lzw")

            # Validate scene has enough valid data (>5% non-NaN)
            _valid_pct = np.sum(~np.isnan(_bands_data["nir"])) / _bands_data["nir"].size
            if _valid_pct < 0.05:
                print(f"skipped ({_valid_pct*100:.1f}% valid)")
                import shutil

                shutil.rmtree(_scene_cache_dir, ignore_errors=True)
                continue  # Try next scene in this time window

            # Calculate biomass stats
            _red = _bands_data["red"]
            _nir = _bands_data["nir"]
            _ndvi = (_nir - _red) / (_nir + _red + 1e-8)

            # Tighter NDVI range for mangroves (excludes agriculture/other forest)
            _mangrove_mask = (_ndvi > 0.5) & (_ndvi < 0.85)
            _biomass = 250.5 * _ndvi - 75.2
            _biomass = np.where(_mangrove_mask, _biomass, np.nan)
            _biomass = np.maximum(_biomass, 0)

            _valid_biomass = _biomass[~np.isnan(_biomass)]

            _pixel_area_ha = (50 * 50) / 10000  # 50m resolution
            _mangrove_area_ha = np.sum(_mangrove_mask) * _pixel_area_ha

            _sample = {
                "date": _scene_date,
                "scene_id": _scene_id,
                "cloud_cover": _cloud,
                "biomass_mean": float(np.mean(_valid_biomass))
                if len(_valid_biomass) > 0
                else 0,
                "biomass_std": float(np.std(_valid_biomass))
                if len(_valid_biomass) > 0
                else 0,
                "mangrove_area_ha": float(_mangrove_area_ha),
                "carbon_stock": float(np.sum(_valid_biomass) * _pixel_area_ha * 0.47)
                if len(_valid_biomass) > 0
                else 0,
            }

            # Save to cache
            _cache_sample = _sample.copy()
            _cache_sample["date"] = _sample["date"].isoformat()
            with open(_stats_file, "w") as _f:
                json.dump(_cache_sample, _f)

            # Save biomass raster for visualization
            _biomass_xr = xr.DataArray(_biomass, dims=["y", "x"])
            _biomass_xr = _biomass_xr.rio.write_crs("EPSG:4326")
            _biomass_xr.rio.to_raster(_scene_cache_dir / "biomass.tif", compress="lzw")

            _temporal_samples.append(_sample)
            print("done")
            break  # Found valid scene, move to next time window

    # Sort by date
    _temporal_samples.sort(key=lambda x: x["date"])

    print(f"\n✅ Loaded {len(_temporal_samples)} temporal samples")

    # Create temporal_data structure
    if len(_temporal_samples) >= 2:
        _initial = _temporal_samples[0]
        _current = _temporal_samples[-1]
        _change_biomass = _current["biomass_mean"] - _initial["biomass_mean"]
        _change_percent = (
            (_change_biomass / _initial["biomass_mean"] * 100)
            if _initial["biomass_mean"] > 0
            else 0
        )

        # Calculate trend
        _dates_numeric = [
            (s["date"] - _temporal_samples[0]["date"]).days for s in _temporal_samples
        ]
        _biomass_values = [s["biomass_mean"] for s in _temporal_samples]
        if len(_dates_numeric) >= 2:
            _slope, _intercept, _r_value, _p_value, _std_err = stats.linregress(
                _dates_numeric, _biomass_values
            )
            _trend_slope_per_year = _slope * 365  # Mg/ha per year
        else:
            _trend_slope_per_year = 0
            _r_value = 0

        temporal_data = {
            "metadata": {
                "site_name": selected_site,
                "bbox": _bounds,
                "n_samples": len(_temporal_samples),
                "date_range": (
                    _temporal_samples[0]["date"],
                    _temporal_samples[-1]["date"],
                ),
            },
            "samples": _temporal_samples,
            "summary": {
                "initial": _initial,
                "current": _current,
                "change_percent": _change_percent,
                "trend_slope_per_year": _trend_slope_per_year,
                "trend_r2": _r_value**2,
            },
        }
    else:
        temporal_data = None
        mo.stop(True, mo.md("**Error:** Need at least 2 samples for temporal analysis"))
    return (temporal_data,)


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Timelapse Visualization

    Use the slider to step through temporal samples, or click Play for automatic animation:
    """
    )
    return


@app.cell(hide_code=True)
def _(temporal_data):
    n_samples = len(temporal_data["samples"]) if temporal_data else 1
    time_slider = mo.ui.slider(
        0, max(0, n_samples - 1), value=0, step=1, label="Time Step:", show_value=True
    )
    time_slider  # noqa: B018
    return (time_slider,)


@app.cell(hide_code=True)
def _(selected_site, temporal_data, time_slider):
    mo.stop(temporal_data is None, mo.md("*Load temporal data first*"))

    _idx = time_slider.value
    _sample = temporal_data["samples"][_idx]
    _date_str = _sample["date"].strftime("%Y-%m-%d")

    # Load biomass raster for this sample
    _site_slug = selected_site.lower().replace(" ", "_")
    _biomass_path = (
        Path("data_cache")
        / "temporal"
        / _site_slug
        / _sample["scene_id"]
        / "biomass.tif"
    )

    if _biomass_path.exists():
        with rioxarray.open_rasterio(_biomass_path) as _src:
            _biomass_raster = _src.values[0]

        # Create Plotly heatmap
        _fig = px.imshow(
            _biomass_raster,
            color_continuous_scale="YlGn",
            labels={"color": "Biomass (Mg/ha)"},
            title=f"Biomass: {_date_str} | Mean: {_sample['biomass_mean']:.1f} Mg/ha | Area: {_sample['mangrove_area_ha']:.0f} ha",
        )
        _fig.update_layout(
            height=500,
            coloraxis_colorbar={"title": "Biomass<br>(Mg/ha)"},
        )
        _fig.update_xaxes(showticklabels=False)
        _fig.update_yaxes(showticklabels=False)
        mo.output.replace(mo.ui.plotly(_fig))
    else:
        mo.output.replace(mo.md(f"*Biomass raster not found for {_date_str}*"))
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Temporal Trend Analysis

    Time series showing biomass change over the study period with trend line:
    """
    )
    return


@app.cell(hide_code=True)
def _(temporal_data):
    mo.stop(temporal_data is None, mo.md("*Load temporal data first*"))

    _samples = temporal_data["samples"]
    _dates = [s["date"] for s in _samples]
    _biomass_values = [s["biomass_mean"] for s in _samples]
    _area_values = [s["mangrove_area_ha"] for s in _samples]

    # Calculate trend line
    _dates_numeric = [(_d - _dates[0]).days for _d in _dates]
    _slope, _intercept, _r_value, _p_value, _std_err = stats.linregress(
        _dates_numeric, _biomass_values
    )
    _trend_line = [_slope * x + _intercept for x in _dates_numeric]

    # Create figure with secondary y-axis
    _fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Biomass time series
    _fig.add_trace(
        go.Scatter(
            x=_dates,
            y=_biomass_values,
            mode="markers+lines",
            name="Mean Biomass",
            marker={"size": 10, "color": "green"},
            line={"width": 1, "color": "lightgreen"},
        ),
        secondary_y=False,
    )

    # Trend line
    _fig.add_trace(
        go.Scatter(
            x=_dates,
            y=_trend_line,
            mode="lines",
            name=f"Trend (R²={_r_value**2:.2f})",
            line={"width": 2, "color": "red", "dash": "dash"},
        ),
        secondary_y=False,
    )

    # Mangrove area on secondary axis
    _fig.add_trace(
        go.Scatter(
            x=_dates,
            y=_area_values,
            mode="markers+lines",
            name="Mangrove Area",
            marker={"size": 8, "color": "blue", "symbol": "square"},
            line={"width": 1, "color": "lightblue"},
        ),
        secondary_y=True,
    )

    _fig.update_layout(
        title="Mangrove Biomass and Area Over Time",
        height=450,
        template="plotly_white",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    _fig.update_xaxes(title_text="Date")
    _fig.update_yaxes(title_text="Mean Biomass (Mg/ha)", secondary_y=False)
    _fig.update_yaxes(title_text="Mangrove Area (ha)", secondary_y=True)

    mo.ui.plotly(_fig)
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Change Summary: Initial vs Current

    Comparison of biomass and carbon metrics between the first and most recent measurements:
    """
    )
    return


@app.cell(hide_code=True)
def _(selected_site, temporal_data):
    mo.stop(temporal_data is None, mo.md("*Load temporal data first*"))

    _summary = temporal_data["summary"]
    _initial = _summary["initial"]
    _current = _summary["current"]

    # Calculate changes
    _biomass_change = _current["biomass_mean"] - _initial["biomass_mean"]
    _area_change = _current["mangrove_area_ha"] - _initial["mangrove_area_ha"]
    _carbon_change = _current["carbon_stock"] - _initial["carbon_stock"]

    # Determine trend
    _trend_direction = "📈 GROWTH" if _biomass_change > 0 else "📉 DECLINE"

    # Create comparison table
    _comparison_df = pd.DataFrame(
        [
            {
                "Metric": "Date",
                "Initial": _initial["date"].strftime("%Y-%m-%d"),
                "Current": _current["date"].strftime("%Y-%m-%d"),
                "Change": f"{(_current['date'] - _initial['date']).days} days",
            },
            {
                "Metric": "Mean Biomass (Mg/ha)",
                "Initial": f"{_initial['biomass_mean']:.1f}",
                "Current": f"{_current['biomass_mean']:.1f}",
                "Change": f"{_biomass_change:+.1f} ({_summary['change_percent']:+.1f}%)",
            },
            {
                "Metric": "Mangrove Area (ha)",
                "Initial": f"{_initial['mangrove_area_ha']:.0f}",
                "Current": f"{_current['mangrove_area_ha']:.0f}",
                "Change": f"{_area_change:+.0f}",
            },
            {
                "Metric": "Carbon Stock (Mg C)",
                "Initial": f"{_initial['carbon_stock']:,.0f}",
                "Current": f"{_current['carbon_stock']:,.0f}",
                "Change": f"{_carbon_change:+,.0f}",
            },
        ]
    )

    mo.vstack(
        [
            mo.md(f"### {selected_site}"),
            mo.md(f"**Overall Trend: {_trend_direction}**"),
            mo.md(
                f"**Trend Rate:** {_summary['trend_slope_per_year']:.2f} Mg/ha per year (R²={_summary['trend_r2']:.2f})"
            ),
            mo.ui.table(_comparison_df, selection=None),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Methodology

    **Mangrove Detection:** NDVI threshold `0.5 < NDVI < 0.85`
    - Lower bound (0.5) excludes sparse vegetation and agriculture
    - Upper bound (0.85) excludes dense non-mangrove forest

    **Biomass Equation:** `Biomass (Mg/ha) = 250.5 × NDVI - 75.2` (R² = 0.72)

    | Parameter | Value | Source |
    |-----------|-------|--------|
    | NDVI range | 0.5 - 0.85 | Mangrove-specific threshold |
    | Slope | 250.5 | Wunbaik Forest, Myanmar |
    | Intercept | -75.2 | Regional calibration |
    | Carbon fraction | 47% | IPCC 2006 Guidelines |
    | Resolution | 50m | Optimized for temporal analysis |

    ⚠️ **Uncertainty:** ±30% (IPCC Tier 2)
    """
    )
    return


@app.cell(hide_code=True)
def _(selected_site, temporal_data):
    mo.stop(temporal_data is None, mo.md("*No data to export*"))

    # Create export DataFrame with all temporal samples
    _export_data = []
    for _sample in temporal_data["samples"]:
        _export_data.append(
            {
                "site": selected_site,
                "date": _sample["date"].strftime("%Y-%m-%d"),
                "scene_id": _sample["scene_id"],
                "cloud_cover_pct": _sample["cloud_cover"],
                "biomass_mean_mg_ha": _sample["biomass_mean"],
                "biomass_std_mg_ha": _sample["biomass_std"],
                "mangrove_area_ha": _sample["mangrove_area_ha"],
                "carbon_stock_mg_c": _sample["carbon_stock"],
            }
        )

    _export_df = pd.DataFrame(_export_data)

    # Save to CSV
    _csv_filename = f"{selected_site.replace(' ', '_')}_temporal_analysis.csv"
    _export_df.to_csv(_csv_filename, index=False)

    mo.vstack(
        [
            mo.md(f"**Exported:** `{_csv_filename}` ({len(_export_data)} samples)"),
            mo.ui.table(_export_df, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
