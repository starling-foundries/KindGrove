#!/usr/bin/env python3
"""
Non-interactive mangrove workflow runner
Generates summary CSV comparable to notebook output
"""

import os
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import rioxarray
import stackstac
import xarray as xr
from pystac_client import Client

warnings.filterwarnings("ignore")

# Study site configuration
STUDY_SITES = {
    "Thor Heyerdahl Climate Park": {
        "center": (95.25, 16.0),
        "bounds": {"west": 95.15, "east": 95.35, "south": 15.9, "north": 16.1},
        "country": "Myanmar",
        "description": "1,800 acres of mangrove restoration in Ayeyarwady Delta",
    }
}


def search_sentinel2(bounds, max_cloud=20, days_back=90):
    """Search for Sentinel-2 imagery"""
    print("🔍 Searching AWS STAC catalog...")
    catalog = Client.open("https://earth-search.aws.element84.com/v1")
    bbox = [bounds["west"], bounds["south"], bounds["east"], bounds["north"]]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
    )

    items = list(search.items())
    if len(items) == 0:
        print(f"❌ No scenes found with <{max_cloud}% cloud cover")
        return None, None

    print(f"✅ Found {len(items)} Sentinel-2 scenes")
    best_item = min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    print(f"📥 Using scene: {best_item.datetime.strftime('%Y-%m-%d')}")
    print(f"   Cloud cover: {best_item.properties.get('eo:cloud_cover', 'N/A'):.1f}%")

    return items, best_item


def load_sentinel2_data(best_item, bbox):
    """Load Sentinel-2 bands with caching"""
    cache_dir = "data_cache"
    os.makedirs(cache_dir, exist_ok=True)

    cache_files = {
        "red": f"{cache_dir}/red.tif",
        "green": f"{cache_dir}/green.tif",
        "nir": f"{cache_dir}/nir.tif",
    }

    cache_exists = all(os.path.exists(f) for f in cache_files.values())

    if cache_exists:
        print(f"\n💾 Found cached GeoTIFF data in {cache_dir}/")
        bands_data = {}
        for band_name, filepath in cache_files.items():
            with rioxarray.open_rasterio(filepath) as src:
                bands_data[band_name] = src.values[0]

        sentinel2_data = xr.DataArray(
            np.stack([bands_data["red"], bands_data["green"], bands_data["nir"]]),
            dims=["band", "y", "x"],
            coords={"band": ["red", "green", "nir"]},
        )
        print("✅ Loaded from cache (instant)")
    else:
        print("\n⏳ Downloading from AWS (30-60 seconds)")
        print("   Resolution: 10m | Bands: red, green, nir")

        sentinel2_lazy = stackstac.stack(
            [best_item],
            assets=["red", "green", "nir"],
            epsg=4326,
            resolution=0.0001,
            bounds_latlon=bbox,
            chunksize=(1, 1, 512, 512),
        )

        import time

        start_time = time.time()
        sentinel2_data = sentinel2_lazy.compute()
        elapsed = time.time() - start_time

        print(f"\n✅ Downloaded in {elapsed:.1f} seconds")
        print("💾 Caching as GeoTIFF...")

        for band_name in ["red", "green", "nir"]:
            band_data = sentinel2_data.sel(band=band_name)
            if "time" in band_data.dims:
                band_data = band_data.isel(time=0)

            band_xr = band_data.rio.write_crs("EPSG:4326")
            band_xr.rio.to_raster(cache_files[band_name], compress="lzw")

        print(f"✅ Cached to {cache_dir}/")

    return sentinel2_data


def calculate_indices(data):
    """Calculate vegetation indices for mangrove detection"""
    if "time" in data.dims:
        red = data.sel(band="red").isel(time=0).values
        green = data.sel(band="green").isel(time=0).values
        nir = data.sel(band="nir").isel(time=0).values
    else:
        red = data.sel(band="red").values
        green = data.sel(band="green").values
        nir = data.sel(band="nir").values

    # NDVI - Normalized Difference Vegetation Index
    ndvi = (nir - red) / (nir + red + 1e-8)

    # NDWI - Normalized Difference Water Index
    ndwi = (green - nir) / (green + nir + 1e-8)

    # SAVI - Soil Adjusted Vegetation Index
    L = 0.5
    savi = ((nir - red) / (nir + red + L)) * (1 + L)

    return {"ndvi": ndvi, "ndwi": ndwi, "savi": savi}


def detect_mangroves(indices):
    """Simple threshold-based mangrove detection"""
    ndvi = indices["ndvi"]
    ndwi = indices["ndwi"]
    savi = indices["savi"]

    mask = (
        (ndvi > 0.3)
        & (ndvi < 0.9)
        & (ndwi > -0.3)  # Vegetated
        & (savi > 0.2)  # Near water  # Adjusted vegetation
    )

    return mask.astype(float)


def estimate_biomass(ndvi, mask):
    """Estimate biomass from NDVI using allometric equation"""
    # Allometric model: AGB = 250.5 × NDVI - 75.2
    biomass = 250.5 * ndvi - 75.2

    # Apply only to mangrove areas
    biomass_masked = np.where(mask > 0, biomass, np.nan)

    # Ensure non-negative
    biomass_masked = np.maximum(biomass_masked, 0)

    return biomass_masked


def generate_summary(site_name, biomass_data):
    """Generate summary report matching notebook format"""
    valid_biomass = biomass_data[~np.isnan(biomass_data)]

    # Calculate comprehensive statistics
    pixel_area_ha = (10 * 10) / 10000
    total_area_ha = len(valid_biomass) * pixel_area_ha
    total_biomass = np.sum(valid_biomass) * pixel_area_ha
    carbon = total_biomass * 0.47
    co2 = carbon * 3.67

    summary_df = pd.DataFrame(
        [
            ["Study Site", site_name],
            ["Analysis Date", datetime.now().strftime("%Y-%m-%d")],
            ["", ""],
            ["Mangrove Area (ha)", f"{total_area_ha:.1f}"],
            ["", ""],
            ["Mean Biomass (Mg/ha)", f"{np.mean(valid_biomass):.1f}"],
            ["Median Biomass (Mg/ha)", f"{np.median(valid_biomass):.1f}"],
            ["Max Biomass (Mg/ha)", f"{np.max(valid_biomass):.1f}"],
            ["Min Biomass (Mg/ha)", f"{np.min(valid_biomass):.1f}"],
            ["Std Deviation (Mg/ha)", f"{np.std(valid_biomass):.1f}"],
            ["", ""],
            ["Total Biomass (Mg)", f"{total_biomass:,.0f}"],
            ["Carbon Stock (Mg C)", f"{carbon:,.0f}"],
            ["CO₂ Equivalent (Mg)", f"{co2:,.0f}"],
            ["", ""],
            ["Uncertainty", "±30%"],
        ],
        columns=["Metric", "Value"],
    )

    return summary_df


def main():
    """Run complete workflow"""
    print("=" * 60)
    print("MANGROVE MONITORING WORKFLOW")
    print("=" * 60)

    # Step 1: Select study area
    site_name = "Thor Heyerdahl Climate Park"
    site_info = STUDY_SITES[site_name]
    bounds = site_info["bounds"]

    print(f"\n📍 Study Site: {site_name}")
    print(f"   Location: {site_info['country']}")
    print(f"   {site_info['description']}")

    # Step 2: Search and load satellite data
    items, best_item = search_sentinel2(bounds)
    if best_item is None:
        print("❌ Failed to find suitable imagery")
        return

    bbox = [bounds["west"], bounds["south"], bounds["east"], bounds["north"]]
    sentinel2_data = load_sentinel2_data(best_item, bbox)

    print(f"\n📊 Data shape: {sentinel2_data.shape}")

    # Step 3: Detect mangroves
    print("\n🔬 Calculating vegetation indices...")
    indices = calculate_indices(sentinel2_data)

    print("🌿 Detecting mangroves...")
    mangrove_mask = detect_mangroves(indices)

    pixel_area_m2 = 10 * 10
    mangrove_pixels = np.sum(mangrove_mask)
    total_area_ha = (mangrove_pixels * pixel_area_m2) / 10000

    print("✅ Detection complete!")
    print(f"   Mangrove area: {total_area_ha:.1f} hectares")

    # Step 4: Estimate biomass
    print("\n🔬 Estimating biomass...")
    biomass_data = estimate_biomass(indices["ndvi"], mangrove_mask)

    valid_biomass = biomass_data[~np.isnan(biomass_data)]
    print("✅ Biomass estimation complete!")
    print(f"   Mean: {np.mean(valid_biomass):.1f} Mg/ha")
    print(f"   Max: {np.max(valid_biomass):.1f} Mg/ha")

    # Step 5: Generate summary and export
    print("\n📋 Generating summary report...")
    summary_df = generate_summary(site_name, biomass_data)

    # Save outputs
    csv_filename = f"{site_name.replace(' ', '_')}_summary.csv"
    summary_df.to_csv(csv_filename, index=False)
    print(f"✅ Summary saved to: {csv_filename}")

    biomass_filename = f"{site_name.replace(' ', '_')}_biomass.csv"
    np.savetxt(biomass_filename, biomass_data, delimiter=",", fmt="%.2f")
    print(f"✅ Biomass data saved to: {biomass_filename}")

    # Display summary
    print("\n" + "=" * 60)
    print("SUMMARY REPORT")
    print("=" * 60)
    print(summary_df.to_string(index=False))
    print("=" * 60)


if __name__ == "__main__":
    main()
