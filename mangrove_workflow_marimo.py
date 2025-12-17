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
    start_year = mo.ui.slider(
        2017, 2024, value=2017, step=1, label="Start Year:", show_value=True
    )
    end_year = mo.ui.slider(
        2017, 2024, value=2024, step=1, label="End Year:", show_value=True
    )
    max_cloud_cover = mo.ui.slider(
        10, 50, value=20, step=5, label="Max Cloud Cover (%):", show_value=True
    )
    mo.vstack([start_year, end_year, max_cloud_cover])
    return end_year, max_cloud_cover, start_year


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    Temporal sampling will query the AWS STAC catalog for ~20 Sentinel-2 L2A scenes
    distributed across the selected time range (2-3 scenes per year, preferring low cloud cover).

    | Band | Wavelength | Resolution | Use |
    |------|------------|------------|-----|
    | Red (B04) | 665 nm | 10m | Vegetation stress |
    | Green (B03) | 560 nm | 10m | Water index |
    | NIR (B08) | 842 nm | 10m | Vegetation health |
    """
    )
    return


@app.cell(hide_code=True)
def _():
    load_temporal_button = mo.ui.run_button(
        label="🛰️ Load Temporal Data (~10-20 min first run)"
    )
    load_temporal_button  # noqa: B018
    return (load_temporal_button,)


@app.cell
def _(
    end_year,
    load_temporal_button,
    max_cloud_cover,
    selected_site,
    site_info,
    start_year,
):
    mo.stop(
        not load_temporal_button.value,
        mo.md("*Click 'Load Temporal Data' to begin temporal analysis*"),
    )

    # Generate time windows (2 per year for dry season sampling)
    time_windows = []
    for year in range(start_year.value, end_year.value + 1):
        # Early dry season (Jan-Feb) and late dry season (Nov-Dec)
        time_windows.append((f"{year}-01-01", f"{year}-02-28"))
        time_windows.append((f"{year}-11-01", f"{year}-12-31"))

    print(
        f"Querying {len(time_windows)} time windows from {start_year.value} to {end_year.value}..."
    )

    # Setup
    _catalog = Client.open("https://earth-search.aws.element84.com/v1")
    _bounds = site_info["bounds"]
    _bbox = [_bounds["west"], _bounds["south"], _bounds["east"], _bounds["north"]]

    # Cache directory for temporal data
    site_slug = selected_site.lower().replace(" ", "_")
    cache_dir = Path("data_cache") / "temporal" / site_slug
    cache_dir.mkdir(parents=True, exist_ok=True)

    temporal_samples = []

    for i, (start_str, end_str) in enumerate(time_windows):
        print(
            f"  [{i+1}/{len(time_windows)}] Searching {start_str} to {end_str}...",
            end=" ",
        )

        _search = _catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=_bbox,
            datetime=f"{start_str}/{end_str}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover.value}},
            sortby=[{"field": "eo:cloud_cover", "direction": "asc"}],
            limit=1,
        )

        items = list(_search.items())
        if not items:
            print("no scenes")
            continue

        item = items[0]
        scene_id = item.id
        scene_date = item.datetime
        cloud = item.properties.get("eo:cloud_cover", 0)
        print(f"found {scene_date.strftime('%Y-%m-%d')} ({cloud:.1f}% cloud)")

        # Check scene cache
        scene_cache_dir = cache_dir / scene_id
        stats_file = scene_cache_dir / "stats.json"

        if stats_file.exists():
            # Load from cache
            with open(stats_file) as f:
                sample = json.load(f)
                sample["date"] = datetime.fromisoformat(sample["date"])
            temporal_samples.append(sample)
            print("    Loaded from cache")
        else:
            # Download and process
            print("    Downloading...", end=" ")
            scene_cache_dir.mkdir(parents=True, exist_ok=True)

            cache_files = {
                "red": scene_cache_dir / "red.tif",
                "green": scene_cache_dir / "green.tif",
                "nir": scene_cache_dir / "nir.tif",
            }

            if all(f.exists() for f in cache_files.values()):
                bands_data = {}
                for band_name, filepath in cache_files.items():
                    with rioxarray.open_rasterio(filepath) as src:
                        bands_data[band_name] = src.values[0]
            else:
                sentinel2_lazy = stackstac.stack(
                    [item],
                    assets=["red", "green", "nir"],
                    epsg=4326,
                    resolution=0.0005,  # Lower res for speed (50m)
                    bounds_latlon=_bbox,
                    chunksize=(1, 1, 512, 512),
                )
                data = sentinel2_lazy.compute()

                bands_data = {}
                for band_name in ["red", "green", "nir"]:
                    band = data.sel(band=band_name)
                    if "time" in band.dims:
                        band = band.isel(time=0)
                    bands_data[band_name] = band.values
                    band_xr = band.rio.write_crs("EPSG:4326")
                    band_xr.rio.to_raster(cache_files[band_name], compress="lzw")

            # Calculate biomass stats
            red = bands_data["red"]
            nir = bands_data["nir"]
            ndvi = (nir - red) / (nir + red + 1e-8)

            mangrove_mask = (ndvi > 0.4) & (ndvi < 0.95)
            biomass = 250.5 * ndvi - 75.2
            biomass = np.where(mangrove_mask, biomass, np.nan)
            biomass = np.maximum(biomass, 0)

            valid_biomass = biomass[~np.isnan(biomass)]

            pixel_area_ha = (50 * 50) / 10000  # 50m resolution
            mangrove_area_ha = np.sum(mangrove_mask) * pixel_area_ha

            sample = {
                "date": scene_date,
                "scene_id": scene_id,
                "cloud_cover": cloud,
                "biomass_mean": float(np.mean(valid_biomass))
                if len(valid_biomass) > 0
                else 0,
                "biomass_std": float(np.std(valid_biomass))
                if len(valid_biomass) > 0
                else 0,
                "mangrove_area_ha": float(mangrove_area_ha),
                "carbon_stock": float(np.sum(valid_biomass) * pixel_area_ha * 0.47)
                if len(valid_biomass) > 0
                else 0,
            }

            # Save to cache
            cache_sample = sample.copy()
            cache_sample["date"] = sample["date"].isoformat()
            with open(stats_file, "w") as f:
                json.dump(cache_sample, f)

            # Save biomass raster for visualization
            biomass_xr = xr.DataArray(biomass, dims=["y", "x"])
            biomass_xr = biomass_xr.rio.write_crs("EPSG:4326")
            biomass_xr.rio.to_raster(scene_cache_dir / "biomass.tif", compress="lzw")

            temporal_samples.append(sample)
            print("done")

    # Sort by date
    temporal_samples.sort(key=lambda x: x["date"])

    print(f"\n✅ Loaded {len(temporal_samples)} temporal samples")

    # Create temporal_data structure
    if len(temporal_samples) >= 2:
        initial = temporal_samples[0]
        current = temporal_samples[-1]
        change_biomass = current["biomass_mean"] - initial["biomass_mean"]
        change_percent = (
            (change_biomass / initial["biomass_mean"] * 100)
            if initial["biomass_mean"] > 0
            else 0
        )

        # Calculate trend
        dates_numeric = [
            (s["date"] - temporal_samples[0]["date"]).days for s in temporal_samples
        ]
        biomass_values = [s["biomass_mean"] for s in temporal_samples]
        if len(dates_numeric) >= 2:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                dates_numeric, biomass_values
            )
            trend_slope_per_year = slope * 365  # Mg/ha per year
        else:
            trend_slope_per_year = 0
            r_value = 0

        temporal_data = {
            "metadata": {
                "site_name": selected_site,
                "bbox": _bounds,
                "n_samples": len(temporal_samples),
                "date_range": (
                    temporal_samples[0]["date"],
                    temporal_samples[-1]["date"],
                ),
            },
            "samples": temporal_samples,
            "summary": {
                "initial": initial,
                "current": current,
                "change_percent": change_percent,
                "trend_slope_per_year": trend_slope_per_year,
                "trend_r2": r_value**2,
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

    idx = time_slider.value
    sample = temporal_data["samples"][idx]
    date_str = sample["date"].strftime("%Y-%m-%d")

    # Load biomass raster for this sample
    site_slug = selected_site.lower().replace(" ", "_")
    biomass_path = (
        Path("data_cache") / "temporal" / site_slug / sample["scene_id"] / "biomass.tif"
    )

    if biomass_path.exists():
        with rioxarray.open_rasterio(biomass_path) as src:
            biomass_raster = src.values[0]

        # Create Plotly heatmap
        fig = px.imshow(
            biomass_raster,
            color_continuous_scale="YlGn",
            labels={"color": "Biomass (Mg/ha)"},
            title=f"Biomass: {date_str} | Mean: {sample['biomass_mean']:.1f} Mg/ha | Area: {sample['mangrove_area_ha']:.0f} ha",
        )
        fig.update_layout(
            height=500,
            coloraxis_colorbar={"title": "Biomass<br>(Mg/ha)"},
        )
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)
        fig  # noqa: B018
    else:
        mo.md(f"*Biomass raster not found for {date_str}*")
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

    samples = temporal_data["samples"]
    dates = [s["date"] for s in samples]
    biomass_values = [s["biomass_mean"] for s in samples]
    area_values = [s["mangrove_area_ha"] for s in samples]

    # Calculate trend line
    dates_numeric = [(d - dates[0]).days for d in dates]
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        dates_numeric, biomass_values
    )
    trend_line = [slope * x + intercept for x in dates_numeric]

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Biomass time series
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=biomass_values,
            mode="markers+lines",
            name="Mean Biomass",
            marker={"size": 10, "color": "green"},
            line={"width": 1, "color": "lightgreen"},
        ),
        secondary_y=False,
    )

    # Trend line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=trend_line,
            mode="lines",
            name=f"Trend (R²={r_value**2:.2f})",
            line={"width": 2, "color": "red", "dash": "dash"},
        ),
        secondary_y=False,
    )

    # Mangrove area on secondary axis
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=area_values,
            mode="markers+lines",
            name="Mangrove Area",
            marker={"size": 8, "color": "blue", "symbol": "square"},
            line={"width": 1, "color": "lightblue"},
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Mangrove Biomass and Area Over Time",
        height=450,
        template="plotly_white",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Mean Biomass (Mg/ha)", secondary_y=False)
    fig.update_yaxes(title_text="Mangrove Area (ha)", secondary_y=True)

    fig  # noqa: B018
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

    summary = temporal_data["summary"]
    initial = summary["initial"]
    current = summary["current"]

    # Calculate changes
    biomass_change = current["biomass_mean"] - initial["biomass_mean"]
    area_change = current["mangrove_area_ha"] - initial["mangrove_area_ha"]
    carbon_change = current["carbon_stock"] - initial["carbon_stock"]

    # Determine trend
    trend_direction = "📈 GROWTH" if biomass_change > 0 else "📉 DECLINE"

    # Create comparison table
    comparison_df = pd.DataFrame(
        [
            {
                "Metric": "Date",
                "Initial": initial["date"].strftime("%Y-%m-%d"),
                "Current": current["date"].strftime("%Y-%m-%d"),
                "Change": f"{(current['date'] - initial['date']).days} days",
            },
            {
                "Metric": "Mean Biomass (Mg/ha)",
                "Initial": f"{initial['biomass_mean']:.1f}",
                "Current": f"{current['biomass_mean']:.1f}",
                "Change": f"{biomass_change:+.1f} ({summary['change_percent']:+.1f}%)",
            },
            {
                "Metric": "Mangrove Area (ha)",
                "Initial": f"{initial['mangrove_area_ha']:.0f}",
                "Current": f"{current['mangrove_area_ha']:.0f}",
                "Change": f"{area_change:+.0f}",
            },
            {
                "Metric": "Carbon Stock (Mg C)",
                "Initial": f"{initial['carbon_stock']:,.0f}",
                "Current": f"{current['carbon_stock']:,.0f}",
                "Change": f"{carbon_change:+,.0f}",
            },
        ]
    )

    mo.vstack(
        [
            mo.md(f"### {selected_site}"),
            mo.md(f"**Overall Trend: {trend_direction}**"),
            mo.md(
                f"**Trend Rate:** {summary['trend_slope_per_year']:.2f} Mg/ha per year (R²={summary['trend_r2']:.2f})"
            ),
            mo.ui.table(comparison_df, selection=None),
        ]
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    ---
    ## Methodology

    **Biomass Equation:** `Biomass (Mg/ha) = 250.5 × NDVI - 75.2` (R² = 0.72)

    | Parameter | Value | Source |
    |-----------|-------|--------|
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
    export_data = []
    for sample in temporal_data["samples"]:
        export_data.append(
            {
                "site": selected_site,
                "date": sample["date"].strftime("%Y-%m-%d"),
                "scene_id": sample["scene_id"],
                "cloud_cover_pct": sample["cloud_cover"],
                "biomass_mean_mg_ha": sample["biomass_mean"],
                "biomass_std_mg_ha": sample["biomass_std"],
                "mangrove_area_ha": sample["mangrove_area_ha"],
                "carbon_stock_mg_c": sample["carbon_stock"],
            }
        )

    export_df = pd.DataFrame(export_data)

    # Save to CSV
    csv_filename = f"{selected_site.replace(' ', '_')}_temporal_analysis.csv"
    export_df.to_csv(csv_filename, index=False)

    mo.vstack(
        [
            mo.md(f"**Exported:** `{csv_filename}` ({len(export_data)} samples)"),
            mo.ui.table(export_df, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
