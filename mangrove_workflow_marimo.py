import marimo

__generated_with = "0.14.0"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import warnings
    from datetime import datetime, timedelta
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import rioxarray
    import stackstac
    import xarray as xr
    from pystac_client import Client

    warnings.filterwarnings("ignore")


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    # Mangrove Monitoring Workflow

    This notebook detects mangroves and estimates biomass from Sentinel-2 satellite imagery.
    All data is open access from ESA/AWS - no API keys required.
    """
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""First, let's define our study sites:""")
    return


@app.cell
def _():
    STUDY_SITES = {
        "Thor Heyerdahl Climate Park": {
            "center": (95.25, 16.0),
            "bounds": {"west": 95.15, "east": 95.35, "south": 15.9, "north": 16.1},
            "country": "Myanmar",
            "description": "1,800 acres of mangrove restoration in Ayeyarwady Delta",
        }
    }
    return (STUDY_SITES,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""Select a study site:""")
    return


@app.cell(hide_code=True)
def _(STUDY_SITES):
    site_dropdown = mo.ui.dropdown(
        options=list(STUDY_SITES.keys()),
        value=list(STUDY_SITES.keys())[0],
        label="Study Site:",
    )
    site_dropdown
    return (site_dropdown,)


@app.cell(hide_code=True)
def _(STUDY_SITES, site_dropdown):
    selected_site = site_dropdown.value
    site_info = STUDY_SITES[selected_site]
    print(f"Selected: {selected_site}")
    print(f"Location: {site_info['country']}")
    print(f"Bounds: {site_info['bounds']}")
    return selected_site, site_info


@app.cell(hide_code=True)
def _(selected_site, site_info):
    def _():
        center_lon, center_lat = site_info["center"]
        bounds = site_info["bounds"]

        fig, ax = plt.subplots(figsize=(8, 6))

        # Draw bounding box
        bbox_lons = [bounds["west"], bounds["east"], bounds["east"], bounds["west"], bounds["west"]]
        bbox_lats = [bounds["south"], bounds["south"], bounds["north"], bounds["north"], bounds["south"]]
        ax.plot(bbox_lons, bbox_lats, 'r-', linewidth=2, label="Study Area")
        ax.fill(bbox_lons, bbox_lats, alpha=0.2, color='red')

        # Mark center
        ax.plot(center_lon, center_lat, 'r*', markersize=15, label="Center")

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title(f"{selected_site}")
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        plt.tight_layout()
        plt.show()

    _()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""Now configure the satellite data search:""")
    return


@app.cell(hide_code=True)
def _():
    cloud_cover = mo.ui.slider(
        0, 50, value=20, step=5, label="Max Cloud Cover (%):", show_value=True
    )
    days_back = mo.ui.slider(
        30, 365, value=90, step=30, label="Days Back:", show_value=True
    )
    mo.vstack([cloud_cover, days_back])
    return cloud_cover, days_back


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    We search the AWS STAC catalog for Sentinel-2 L2A imagery:

    | Band | Wavelength | Resolution | Use |
    |------|------------|------------|-----|
    | Red (B04) | 665 nm | 10m | Vegetation stress |
    | Green (B03) | 560 nm | 10m | Water index |
    | NIR (B08) | 842 nm | 10m | Vegetation health |
    """
    )
    return


@app.cell
def _(
    Client,
    Path,
    cloud_cover,
    datetime,
    days_back,
    np,
    rioxarray,
    site_info,
    stackstac,
    timedelta,
    xr,
):
    # Search STAC catalog
    print("Searching AWS STAC catalog...")
    catalog = Client.open("https://earth-search.aws.element84.com/v1")
    bounds = site_info["bounds"]
    bbox = [bounds["west"], bounds["south"], bounds["east"], bounds["north"]]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back.value)

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
        query={"eo:cloud_cover": {"lt": cloud_cover.value}},
    )

    items = list(search.items())
    print(f"Found {len(items)} scenes")

    if len(items) == 0:
        mo.stop(
            True, mo.md("No scenes found. Try increasing cloud cover or date range.")
        )

    # Select best scene
    best_item = min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    print(
        f"Selected: {best_item.datetime.strftime('%Y-%m-%d')} ({best_item.properties.get('eo:cloud_cover', 0):.1f}% cloud)"
    )

    # Check cache - key by scene ID so different dates get different cache
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)
    scene_id = best_item.id  # e.g., "S2A_MSIL2A_20251205T..."
    cache_files = {
        "red": cache_dir / f"{scene_id}_red.tif",
        "green": cache_dir / f"{scene_id}_green.tif",
        "nir": cache_dir / f"{scene_id}_nir.tif",
    }

    if all(f.exists() for f in cache_files.values()):
        print(f"Loading from cache ({scene_id})...")
        bands_data = {}
        for band_name, filepath in cache_files.items():
            with rioxarray.open_rasterio(filepath) as src:
                bands_data[band_name] = src.values[0]
        sentinel2_data = xr.DataArray(
            np.stack([bands_data["red"], bands_data["green"], bands_data["nir"]]),
            dims=["band", "y", "x"],
            coords={"band": ["red", "green", "nir"]},
        )
    else:
        print("Downloading from AWS (30-60 seconds)...")
        sentinel2_lazy = stackstac.stack(
            [best_item],
            assets=["red", "green", "nir"],
            epsg=4326,
            resolution=0.0001,
            bounds_latlon=bbox,
            chunksize=(1, 1, 512, 512),
        )
        sentinel2_data = sentinel2_lazy.compute()

        print("Caching to disk...")
        for band_name in ["red", "green", "nir"]:
            band_data = sentinel2_data.sel(band=band_name)
            if "time" in band_data.dims:
                band_data = band_data.isel(time=0)
            band_xr = band_data.rio.write_crs("EPSG:4326")
            band_xr.rio.to_raster(cache_files[band_name], compress="lzw")

    print(f"Data shape: {sentinel2_data.shape}")
    return (sentinel2_data,)


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    Now we detect mangroves using vegetation indices:

    | Index | Formula | Interpretation |
    |-------|---------|----------------|
    | NDVI | (NIR - Red) / (NIR + Red) | Vegetation greenness |
    | NDWI | (Green - NIR) / (Green + NIR) | Water content |
    | SAVI | (NIR - Red) / (NIR + Red + L) × (1 + L) | Soil-adjusted vegetation |

    Mangroves are identified where: **NDVI > 0.3**, **NDWI > -0.3**, and **SAVI > 0.2**
    """
    )
    return


@app.cell
def _(np, sentinel2_data):
    # Core science: vegetation index calculation

    # Extract bands
    if "time" in sentinel2_data.dims:
        red = sentinel2_data.sel(band="red").isel(time=0).values
        green = sentinel2_data.sel(band="green").isel(time=0).values
        nir = sentinel2_data.sel(band="nir").isel(time=0).values
    else:
        red = sentinel2_data.sel(band="red").values
        green = sentinel2_data.sel(band="green").values
        nir = sentinel2_data.sel(band="nir").values

    # Calculate vegetation indices
    ndvi = (nir - red) / (nir + red + 1e-8)
    ndwi = (green - nir) / (green + nir + 1e-8)
    L = 0.5
    savi = ((nir - red) / (nir + red + L)) * (1 + L)

    # Detect mangroves using threshold classification
    mangrove_mask = ((ndvi > 0.3) & (ndvi < 0.9) & (ndwi > -0.3) & (savi > 0.2)).astype(
        float
    )

    # Statistics
    pixel_area_m2 = 10 * 10  # 10m resolution
    mangrove_pixels = np.sum(mangrove_mask)
    mangrove_area_ha = (mangrove_pixels * pixel_area_m2) / 10000

    print(f"NDVI range: {ndvi.min():.2f} to {ndvi.max():.2f}")
    print(f"Mangrove pixels: {int(mangrove_pixels)}")
    print(f"Mangrove area: {mangrove_area_ha:.1f} hectares")
    return mangrove_area_ha, mangrove_mask, ndvi


@app.cell(hide_code=True)
def _(mangrove_mask, ndvi, plt):
    def _():
        plt.figure(figsize=(14, 5))

        ax1 = plt.subplot(1, 2, 1)
        ax1.set_title("NDVI")
        im1 = ax1.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=1.0)
        plt.colorbar(im1, ax=ax1, shrink=0.8)
        ax1.axis("off")

        ax2 = plt.subplot(1, 2, 2)
        ax2.set_title("Mangrove Detection")
        im2 = ax2.imshow(mangrove_mask, cmap="Greens")
        plt.colorbar(im2, ax=ax2, shrink=0.8)
        ax2.axis("off")

        plt.tight_layout()
        plt.show()

    _()
    return


@app.cell(hide_code=True)
def _():
    mo.md(
        r"""
    Now we estimate biomass using an allometric equation from Southeast Asian mangrove studies:

    **Biomass (Mg/ha) = 250.5 × NDVI - 75.2**

    Carbon accounting:
    - Carbon fraction: 47% of biomass
    - CO₂ conversion: 3.67 × carbon mass
    """
    )
    return


@app.cell
def _(mangrove_mask, ndvi, np):
    # Core science: biomass estimation

    # Allometric model from Southeast Asian mangrove studies
    biomass = 250.5 * ndvi - 75.2

    # Apply only to mangrove areas and ensure non-negative
    biomass = np.where(mangrove_mask > 0, biomass, np.nan)
    biomass = np.maximum(biomass, 0)

    # Statistics
    valid_biomass = biomass[~np.isnan(biomass)]

    mean_biomass = np.mean(valid_biomass)
    median_biomass = np.median(valid_biomass)
    max_biomass = np.max(valid_biomass)
    std_biomass = np.std(valid_biomass)

    # Carbon accounting
    pixel_area_ha = (10 * 10) / 10000
    total_biomass = np.sum(valid_biomass) * pixel_area_ha
    carbon_stock = total_biomass * 0.47
    co2_equivalent = carbon_stock * 3.67

    print(f"Mean biomass: {mean_biomass:.1f} Mg/ha")
    print(f"Median biomass: {median_biomass:.1f} Mg/ha")
    print(f"Max biomass: {max_biomass:.1f} Mg/ha")
    print(f"Total biomass: {total_biomass:,.0f} Mg")
    print(f"Carbon stock: {carbon_stock:,.0f} Mg C")
    print(f"CO2 equivalent: {co2_equivalent:,.0f} Mg CO2")
    return (
        biomass,
        carbon_stock,
        co2_equivalent,
        mean_biomass,
        total_biomass,
        valid_biomass,
    )


@app.cell(hide_code=True)
def _(biomass, plt):
    def _():
        plt.figure(figsize=(10, 8))
        ax = plt.subplot(1, 1, 1)
        ax.set_title("Biomass Distribution (Mg/ha)")
        im = ax.imshow(biomass, cmap="viridis", vmin=0, vmax=150)
        plt.colorbar(im, ax=ax, label="Mg/ha", shrink=0.8)
        ax.axis("off")
        plt.tight_layout()
        plt.show()

    _()
    return


@app.cell(hide_code=True)
def _(valid_biomass):
    def _():
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.hist(valid_biomass, bins=30, color="green", alpha=0.7, edgecolor="darkgreen")
        ax.set_xlabel("Biomass (Mg/ha)")
        ax.set_ylabel("Pixel Count")
        ax.set_title("Biomass Distribution")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    _()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""Finally, let's create a summary table:""")
    return


@app.cell(hide_code=True)
def _(
    carbon_stock,
    co2_equivalent,
    datetime,
    mangrove_area_ha,
    mean_biomass,
    pd,
    selected_site,
    total_biomass,
):
    summary_df = pd.DataFrame(
        [
            {"Metric": "Study Site", "Value": selected_site},
            {"Metric": "Analysis Date", "Value": datetime.now().strftime("%Y-%m-%d")},
            {"Metric": "Mangrove Area (ha)", "Value": f"{mangrove_area_ha:.1f}"},
            {"Metric": "Mean Biomass (Mg/ha)", "Value": f"{mean_biomass:.1f}"},
            {"Metric": "Total Biomass (Mg)", "Value": f"{total_biomass:,.0f}"},
            {"Metric": "Carbon Stock (Mg C)", "Value": f"{carbon_stock:,.0f}"},
            {"Metric": "CO2 Equivalent (Mg)", "Value": f"{co2_equivalent:,.0f}"},
            {"Metric": "Uncertainty", "Value": "±30%"},
        ]
    )
    mo.ui.table(summary_df, selection=None)
    return (summary_df,)


@app.cell(hide_code=True)
def _(selected_site, summary_df):
    # Export results to CSV
    csv_filename = f"{selected_site.replace(' ', '_')}_summary.csv"
    summary_df.to_csv(csv_filename, index=False)
    print(f"Saved: {csv_filename}")
    return


if __name__ == "__main__":
    app.run()
