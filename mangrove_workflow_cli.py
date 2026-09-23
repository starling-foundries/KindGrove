#!/usr/bin/env python3
"""
Mangrove Biomass Estimation CLI

Command-line interface for mangrove forest biomass and carbon stock estimation
using Sentinel-2 satellite imagery. Follows OGC Application Package best practices.

Based on validated allometric model from Myanmar field studies (R² = 0.72).
"""

import os
import sys

# Suppress warnings for cleaner output
import warnings
from datetime import datetime, timedelta

import click
import numpy as np
import pandas as pd
import stackstac

import earthsearch as es
from pystac_client import Client

warnings.filterwarnings("ignore")

# Configure numpy error handling
np.seterr(divide="ignore", invalid="ignore")


def search_sentinel2(bbox, cloud_cover_max, days_back):
    """
    Search AWS STAC catalog for Sentinel-2 L2A scenes.

    Args:
        bbox: Bounding box [west, south, east, north]
        cloud_cover_max: Maximum cloud cover percentage
        days_back: Days to search backwards from today

    Returns:
        List of STAC items
    """
    click.echo("🔍 Searching AWS STAC catalog...")

    catalog = es.open_catalog()  # request timeout and retries: a stalled search fails, not hangs

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
        query={"eo:cloud_cover": {"lt": cloud_cover_max}},
    )

    items = list(search.items())
    click.echo(f"   Found {len(items)} scenes")

    if len(items) == 0:
        raise ValueError(f"No scenes found with <{cloud_cover_max}% cloud cover")

    return items


def download_imagery(item, bbox):
    """
    Download and crop Sentinel-2 bands to study area.

    Args:
        item: STAC item
        bbox: Bounding box [west, south, east, north]

    Returns:
        xarray.DataArray with red, green, nir bands
    """
    click.echo(f"📥 Downloading scene: {item.datetime.strftime('%Y-%m-%d')}")
    click.echo(f"   Cloud cover: {item.properties.get('eo:cloud_cover', 'N/A'):.1f}%")

    # Load imagery with bounds_latlon to clip during load (fixes NaN issue)
    sentinel2_lazy = stackstac.stack(
        [item],
        assets=["red", "green", "nir"],
        epsg=4326,
        resolution=0.0001,  # ~10m at equator
        bounds_latlon=bbox,  # Clip to study area during load
        chunksize=(1, 1, 512, 512),
        gdal_env=es.GDAL_ENV,  # every byte-range read has a timeout and a retry budget
    )

    # Compute data (already clipped by bounds_latlon)
    sentinel2_data = sentinel2_lazy.compute()

    # Processing baseline >= 04.00 (Jan 2022) declares a BOA offset (raster:bands offset -0.1
    # at scale 0.0001). Earth Search delivers those scenes with the offset already removed
    # (earthsearch:boa_offset_applied) but keeps the declaration, and stackstac's rescale
    # applies it again, so red goes negative and NDVI overshoots. Add it back.
    rb = item.assets["red"].extra_fields.get("raster:bands", [{}])[0]
    shift = -float(rb.get("offset", 0.0)) if item.properties.get("earthsearch:boa_offset_applied") else 0.0
    if shift:
        sentinel2_data = sentinel2_data + shift
        click.echo(f"   BOA offset re-added: {shift:+.2f} (processing baseline {item.properties.get('s2:processing_baseline')})")

    click.echo(f"   Data shape: {sentinel2_data.shape}")

    return sentinel2_data


def calculate_indices(data):
    """
    Calculate vegetation indices for mangrove detection.

    Args:
        data: xarray.DataArray with red, green, nir bands

    Returns:
        Dictionary with ndvi, ndwi, savi arrays
    """
    click.echo("🔬 Calculating vegetation indices...")

    # Extract bands (BOA offset of processing baseline >= 04.00 removed by the caller)
    if "time" in data.dims:
        red = data.sel(band="red").isel(time=0).values
        green = data.sel(band="green").isel(time=0).values
        nir = data.sel(band="nir").isel(time=0).values
    else:
        red = data.sel(band="red").values
        green = data.sel(band="green").values
        nir = data.sel(band="nir").values

    # Calculate indices
    ndvi = (nir - red) / (nir + red + 1e-8)
    ndwi = (green - nir) / (green + nir + 1e-8)
    savi = ((nir - red) / (nir + red + 0.5)) * 1.5

    click.echo(f"   NDVI range: {np.nanmin(ndvi):.3f} to {np.nanmax(ndvi):.3f}")

    return {"ndvi": ndvi, "ndwi": ndwi, "savi": savi}


def detect_mangroves(indices):
    """
    Detect mangrove pixels using threshold classification.

    Args:
        indices: Dictionary with ndvi, ndwi, savi

    Returns:
        Binary mask (1 = mangrove, 0 = non-mangrove)
    """
    click.echo("🌿 Detecting mangroves...")

    ndvi = indices["ndvi"]
    ndwi = indices["ndwi"]
    savi = indices["savi"]

    # Threshold criteria from research
    mask = (
        (ndvi > 0.3)
        & (ndvi < 0.9)  # Vegetated
        & (ndwi > -0.3)  # Not upland forest
        & (savi > 0.2)  # Near water  # Soil-adjusted vegetation
    ).astype(float)

    pixel_area_m2 = 10 * 10
    mangrove_pixels = np.sum(mask)
    mangrove_area_ha = (mangrove_pixels * pixel_area_m2) / 10000

    click.echo(f"   Detected area: {mangrove_area_ha:.1f} hectares")
    click.echo(f"   Coverage: {(mangrove_pixels / mask.size * 100):.1f}% of study area")

    return mask


def estimate_biomass(ndvi, mask):
    """
    Estimate above-ground biomass using allometric equation.

    Args:
        ndvi: NDVI array
        mask: Mangrove detection mask

    Returns:
        Biomass array (Mg/ha), statistics dictionary
    """
    click.echo("📊 Estimating biomass...")

    # Allometric model from Myanmar field studies
    # Biomass = 250.5 × NDVI - 75.2 (R² = 0.72)
    biomass = 250.5 * ndvi - 75.2
    biomass_masked = np.where(mask > 0, biomass, np.nan)
    biomass_masked = np.maximum(biomass_masked, 0)

    valid_biomass = biomass_masked[~np.isnan(biomass_masked)]

    if len(valid_biomass) > 0:
        stats = {
            "mean": np.mean(valid_biomass),
            "median": np.median(valid_biomass),
            "max": np.max(valid_biomass),
            "min": np.min(valid_biomass),
            "std": np.std(valid_biomass),
        }

        click.echo(f"   Mean: {stats['mean']:.1f} Mg/ha")
        click.echo(f"   Range: {stats['min']:.1f} - {stats['max']:.1f} Mg/ha")
    else:
        click.echo("   Warning: No valid biomass estimates")
        stats = {"mean": 0, "median": 0, "max": 0, "min": 0, "std": 0}

    return biomass_masked, stats


def calculate_carbon(biomass_masked):
    """
    Calculate carbon stocks using IPCC guidelines.

    Args:
        biomass_masked: Biomass array (Mg/ha)

    Returns:
        Dictionary with carbon metrics
    """
    click.echo("🌍 Calculating carbon stocks...")

    valid_biomass = biomass_masked[~np.isnan(biomass_masked)]

    if len(valid_biomass) > 0:
        pixel_area_ha = (10 * 10) / 10000
        total_biomass_mg = np.sum(valid_biomass) * pixel_area_ha
        carbon_stock_mg = total_biomass_mg * 0.47  # IPCC carbon fraction
        co2_equivalent_mg = carbon_stock_mg * 3.67  # CO2 to C ratio

        carbon = {
            "total_biomass": total_biomass_mg,
            "carbon_stock": carbon_stock_mg,
            "co2_equivalent": co2_equivalent_mg,
        }

        click.echo(f"   Total biomass: {carbon['total_biomass']:,.0f} Mg")
        click.echo(f"   Carbon stock: {carbon['carbon_stock']:,.0f} Mg C")
        click.echo(f"   CO₂ equivalent: {carbon['co2_equivalent']:,.0f} Mg CO₂")
    else:
        carbon = {"total_biomass": 0, "carbon_stock": 0, "co2_equivalent": 0}

    return carbon


def export_results(output_dir, mask, biomass, ndvi, stats, carbon, item, bbox):
    """
    Export results as CSV summaries and GeoTIFF rasters.

    Args:
        output_dir: Output directory path
        mask: Mangrove detection mask
        biomass: Biomass array
        ndvi: NDVI array
        stats: Biomass statistics
        carbon: Carbon metrics
        item: STAC item (for metadata)
        bbox: Bounding box
    """
    click.echo(f"💾 Exporting results to {output_dir}/...")

    os.makedirs(output_dir, exist_ok=True)

    # Calculate area
    pixel_area_m2 = 10 * 10
    mangrove_pixels = np.sum(mask)
    mangrove_area_ha = (mangrove_pixels * pixel_area_m2) / 10000

    # 1. Biomass summary CSV
    biomass_df = pd.DataFrame(
        [
            {"Metric": "Mangrove Area (ha)", "Value": f"{mangrove_area_ha:.1f}"},
            {"Metric": "Mean Biomass (Mg/ha)", "Value": f"{stats['mean']:.1f}"},
            {"Metric": "Median Biomass (Mg/ha)", "Value": f"{stats['median']:.1f}"},
            {"Metric": "Max Biomass (Mg/ha)", "Value": f"{stats['max']:.1f}"},
            {"Metric": "Std Deviation (Mg/ha)", "Value": f"{stats['std']:.1f}"},
        ]
    )
    biomass_df.to_csv(
        os.path.join(output_dir, "mangrove_area_summary.csv"), index=False
    )

    # 2. Carbon summary CSV
    carbon_df = pd.DataFrame(
        [
            {
                "Metric": "Total Biomass (Mg)",
                "Value": f"{carbon['total_biomass']:,.0f}",
            },
            {
                "Metric": "Carbon Stock (Mg C)",
                "Value": f"{carbon['carbon_stock']:,.0f}",
            },
            {
                "Metric": "CO2 Equivalent (Mg CO2)",
                "Value": f"{carbon['co2_equivalent']:,.0f}",
            },
            {"Metric": "Analysis Date", "Value": datetime.now().strftime("%Y-%m-%d")},
            {"Metric": "Scene Date", "Value": item.datetime.strftime("%Y-%m-%d")},
            {
                "Metric": "Cloud Cover (%)",
                "Value": f"{item.properties.get('eo:cloud_cover', 0):.1f}",
            },
            {"Metric": "Uncertainty", "Value": "±30%"},
        ]
    )
    carbon_df.to_csv(
        os.path.join(output_dir, "biomass_carbon_summary.csv"), index=False
    )

    click.echo("   ✓ CSV summaries saved")
    click.echo("\n✅ Workflow complete!")
    click.echo(f"   Outputs: {output_dir}/")


@click.command(
    short_help="Mangrove biomass estimation",
    help="""
    Estimates mangrove forest above-ground biomass and carbon stocks using
    Sentinel-2 satellite imagery from AWS Open Data Registry.

    Uses threshold-based classification and validated allometric model:
    Biomass = 250.5 × NDVI - 75.2 (R² = 0.72, Myanmar field studies)

    Example:

        python mangrove_workflow_cli.py --west 95.15 --south 15.9 --east 95.35 --north 16.1
    """,
)
@click.option(
    "--west",
    type=float,
    required=True,
    help="Western longitude bound (decimal degrees)",
)
@click.option(
    "--south",
    type=float,
    required=True,
    help="Southern latitude bound (decimal degrees)",
)
@click.option(
    "--east",
    type=float,
    required=True,
    help="Eastern longitude bound (decimal degrees)",
)
@click.option(
    "--north",
    type=float,
    required=True,
    help="Northern latitude bound (decimal degrees)",
)
@click.option(
    "--cloud-cover",
    type=int,
    default=20,
    help="Maximum cloud cover percentage (0-100) [default: 20]",
)
@click.option(
    "--days-back",
    type=int,
    default=90,
    help="Days to search backwards from today [default: 90]",
)
@click.option(
    "--output-dir",
    type=str,
    default="outputs",
    help="Output directory for results [default: outputs]",
)
def main(west, south, east, north, cloud_cover, days_back, output_dir):
    """Main workflow execution."""

    click.echo("=" * 60)
    click.echo("🌿 Mangrove Biomass Estimation Workflow")
    click.echo("=" * 60)
    click.echo(f"Study area: ({west}, {south}) to ({east}, {north})")
    click.echo(f"Max cloud cover: {cloud_cover}%")
    click.echo(f"Search window: {days_back} days")
    click.echo("")

    try:
        # 1. Search STAC catalog
        bbox = [west, south, east, north]
        items = search_sentinel2(bbox, cloud_cover, days_back)

        # 2. Download the best scene; if it cannot be fetched inside the network budget, the next
        candidates = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
        best_item, sentinel2_data = es.fetch_first(candidates, lambda it: download_imagery(it, bbox), log=click.echo)

        # 3. Calculate vegetation indices
        indices = calculate_indices(sentinel2_data)

        # 4. Detect mangroves
        mask = detect_mangroves(indices)

        # 5. Estimate biomass
        biomass, stats = estimate_biomass(indices["ndvi"], mask)

        # 6. Calculate carbon
        carbon = calculate_carbon(biomass)

        # 7. Export results
        export_results(
            output_dir, mask, biomass, indices["ndvi"], stats, carbon, best_item, bbox
        )

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
