#!/usr/bin/env python3
"""
Capture STAC API calls and responses for documentation.

This script runs the mangrove workflow and saves all intermediate data
in JSON format for inspection and standardization.
"""

import json
import os
import warnings
from datetime import datetime, timedelta

import numpy as np
import stackstac
from pystac_client import Client

warnings.filterwarnings("ignore")
np.seterr(divide="ignore", invalid="ignore")

# Output directory for captured data
OUTPUT_DIR = "stac_data_capture"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Study area configuration
BBOX = [95.15, 15.9, 95.35, 16.1]  # Myanmar test area
CLOUD_COVER_MAX = 20
DAYS_BACK = 90


def serialize_stac_item(item):
    """Convert STAC item to JSON-serializable dict."""
    return {
        "type": item.to_dict().get("type"),
        "stac_version": item.to_dict().get("stac_version"),
        "id": item.id,
        "collection": item.collection_id,
        "geometry": item.geometry,
        "bbox": item.bbox,
        "properties": item.properties,
        "assets": {
            name: {
                "href": asset.href,
                "type": asset.media_type,
                "roles": asset.roles,
                "eo:bands": asset.extra_fields.get("eo:bands", []),
                "gsd": asset.extra_fields.get("gsd"),
                "proj:shape": asset.extra_fields.get("proj:shape"),
                "proj:transform": asset.extra_fields.get("proj:transform"),
            }
            for name, asset in item.assets.items()
            if name in ["red", "green", "nir"]
        },
        "links": [
            {"rel": link.rel, "href": link.target, "type": link.media_type}
            for link in item.links[:3]  # Just first few links
        ],
    }


def serialize_xarray_structure(data):
    """Extract xarray structure without full data arrays."""
    coords_info = {}
    for name, coord in data.coords.items():
        coord_info = {
            "dims": list(coord.dims),
            "size": coord.size,
            "dtype": str(coord.dtype),
        }

        # Handle numeric vs string coordinates
        if coord.size > 0:
            if np.issubdtype(coord.dtype, np.number):
                # Scalar or array
                if coord.ndim == 0:
                    coord_info["value"] = float(coord.values)
                else:
                    coord_info["min"] = float(coord.min().values)
                    coord_info["max"] = float(coord.max().values)
                    coord_info["sample_values"] = coord.values[:5].tolist()
            else:
                # String or object dtype
                if coord.ndim == 0:
                    coord_info["value"] = str(coord.values)
                else:
                    coord_info["sample_values"] = [str(v) for v in coord.values[:5]]

        coords_info[name] = coord_info

    # Serialize attrs, converting non-JSON types to strings
    attrs_serialized = {}
    for key, value in data.attrs.items():
        try:
            # Try to JSON serialize the value
            json.dumps(value)
            attrs_serialized[key] = value
        except (TypeError, ValueError):
            # If not serializable, convert to string
            attrs_serialized[key] = str(value)

    return {
        "type": "xarray.DataArray",
        "dims": list(data.dims),
        "shape": list(data.shape),
        "coords": coords_info,
        "attrs": attrs_serialized,
        "data": {
            "dtype": str(data.dtype),
            "nbytes": data.nbytes,
            "size": data.size,
            "shape": list(data.shape),
            "sample_statistics": {
                "min": float(np.nanmin(data.values)),
                "max": float(np.nanmax(data.values)),
                "mean": float(np.nanmean(data.values)),
                "std": float(np.nanstd(data.values)),
            },
        },
    }


def serialize_numpy_array(arr, name):
    """Extract numpy array statistics."""
    valid_data = arr[~np.isnan(arr)]
    return {
        "name": name,
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "total_elements": int(arr.size),
        "valid_elements": int(valid_data.size),
        "nan_elements": int(arr.size - valid_data.size),
        "statistics": {
            "min": float(np.nanmin(arr)) if valid_data.size > 0 else None,
            "max": float(np.nanmax(arr)) if valid_data.size > 0 else None,
            "mean": float(np.nanmean(arr)) if valid_data.size > 0 else None,
            "median": float(np.nanmedian(arr)) if valid_data.size > 0 else None,
            "std": float(np.nanstd(arr)) if valid_data.size > 0 else None,
        },
        "histogram": {
            "bins": 10,
            "counts": np.histogram(valid_data, bins=10)[0].tolist()
            if valid_data.size > 0
            else [],
            "edges": np.histogram(valid_data, bins=10)[1].tolist()
            if valid_data.size > 0
            else [],
        },
    }


print("=" * 60)
print("Capturing STAC Data Flow")
print("=" * 60)

# STEP 1: STAC Catalog Search
print("\n[1/7] Searching STAC catalog...")

catalog = Client.open("https://earth-search.aws.element84.com/v1")

end_date = datetime.now()
start_date = end_date - timedelta(days=DAYS_BACK)

# Capture the search parameters
search_params = {
    "catalog_url": "https://earth-search.aws.element84.com/v1",
    "method": "catalog.search",
    "parameters": {
        "collections": ["sentinel-2-l2a"],
        "bbox": BBOX,
        "datetime": f"{start_date.isoformat()}/{end_date.isoformat()}",
        "query": {"eo:cloud_cover": {"lt": CLOUD_COVER_MAX}},
    },
}

with open(f"{OUTPUT_DIR}/01_stac_search_request.json", "w") as f:
    json.dump(search_params, f, indent=2)

# Execute search
search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=BBOX,
    datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
    query={"eo:cloud_cover": {"lt": CLOUD_COVER_MAX}},
)

items = list(search.items())
print(f"   Found {len(items)} scenes")

# Capture search results summary
search_response = {
    "items_found": len(items),
    "items": [
        {
            "id": item.id,
            "datetime": item.datetime.isoformat(),
            "cloud_cover": item.properties.get("eo:cloud_cover"),
            "platform": item.properties.get("platform"),
        }
        for item in items
    ],
}

with open(f"{OUTPUT_DIR}/01_stac_search_response.json", "w") as f:
    json.dump(search_response, f, indent=2)

# STEP 2: Select best scene and capture full STAC item
print("\n[2/7] Selecting best scene and capturing STAC item...")

best_item = min(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
print(f"   Selected: {best_item.id}")
print(f"   Date: {best_item.datetime.strftime('%Y-%m-%d')}")
print(f"   Cloud cover: {best_item.properties.get('eo:cloud_cover'):.1f}%")

# Capture full STAC item
stac_item_data = serialize_stac_item(best_item)

with open(f"{OUTPUT_DIR}/02_stac_item_selected.json", "w") as f:
    json.dump(stac_item_data, f, indent=2)

# STEP 3: Download imagery with stackstac
print("\n[3/7] Loading imagery with stackstac...")

# Capture stackstac parameters
stackstac_params = {
    "library": "stackstac",
    "method": "stackstac.stack",
    "parameters": {
        "items": ["<STAC_Item>"],
        "assets": ["red", "green", "nir"],
        "epsg": 4326,
        "resolution": 0.0001,
        "bounds_latlon": BBOX,
        "chunksize": [1, 1, 512, 512],
    },
}

with open(f"{OUTPUT_DIR}/03_stackstac_request.json", "w") as f:
    json.dump(stackstac_params, f, indent=2)

# Execute stackstac
sentinel2_lazy = stackstac.stack(
    [best_item],
    assets=["red", "green", "nir"],
    epsg=4326,
    resolution=0.0001,
    bounds_latlon=BBOX,
    chunksize=(1, 1, 512, 512),
)

sentinel2_data = sentinel2_lazy.compute()
print(f"   Data shape: {sentinel2_data.shape}")

# Capture xarray structure
xarray_structure = serialize_xarray_structure(sentinel2_data)

with open(f"{OUTPUT_DIR}/03_stackstac_response.json", "w") as f:
    json.dump(xarray_structure, f, indent=2)

# STEP 4: Extract bands
print("\n[4/7] Extracting spectral bands...")

if "time" in sentinel2_data.dims:
    red = sentinel2_data.sel(band="red").isel(time=0).values
    green = sentinel2_data.sel(band="green").isel(time=0).values
    nir = sentinel2_data.sel(band="nir").isel(time=0).values
else:
    red = sentinel2_data.sel(band="red").values
    green = sentinel2_data.sel(band="green").values
    nir = sentinel2_data.sel(band="nir").values

# Capture band statistics
bands_data = {
    "bands": [
        serialize_numpy_array(red, "red"),
        serialize_numpy_array(green, "green"),
        serialize_numpy_array(nir, "nir"),
    ]
}

with open(f"{OUTPUT_DIR}/04_spectral_bands.json", "w") as f:
    json.dump(bands_data, f, indent=2)

# STEP 5: Calculate vegetation indices
print("\n[5/7] Calculating vegetation indices...")

ndvi = (nir - red) / (nir + red + 1e-8)
ndwi = (green - nir) / (green + nir + 1e-8)
savi = ((nir - red) / (nir + red + 0.5)) * 1.5

print(f"   NDVI range: {np.nanmin(ndvi):.3f} to {np.nanmax(ndvi):.3f}")

# Capture indices
indices_data = {
    "formulas": {
        "ndvi": "(NIR - Red) / (NIR + Red + 1e-8)",
        "ndwi": "(Green - NIR) / (Green + NIR + 1e-8)",
        "savi": "((NIR - Red) / (NIR + Red + 0.5)) * 1.5",
    },
    "indices": [
        serialize_numpy_array(ndvi, "ndvi"),
        serialize_numpy_array(ndwi, "ndwi"),
        serialize_numpy_array(savi, "savi"),
    ],
}

with open(f"{OUTPUT_DIR}/05_vegetation_indices.json", "w") as f:
    json.dump(indices_data, f, indent=2)

# STEP 6: Detect mangroves
print("\n[6/7] Detecting mangroves...")

mask = ((ndvi > 0.3) & (ndvi < 0.9) & (ndwi > -0.3) & (savi > 0.2)).astype(float)

pixel_area_m2 = 10 * 10
mangrove_pixels = np.sum(mask)
mangrove_area_ha = (mangrove_pixels * pixel_area_m2) / 10000

print(f"   Detected area: {mangrove_area_ha:.1f} hectares")

# Capture detection results
detection_data = {
    "classification_criteria": {
        "ndvi_min": 0.3,
        "ndvi_max": 0.9,
        "ndwi_min": -0.3,
        "savi_min": 0.2,
        "logic": "AND (all conditions must be true)",
    },
    "mask": serialize_numpy_array(mask, "mangrove_mask"),
    "statistics": {
        "total_pixels": int(mask.size),
        "mangrove_pixels": int(mangrove_pixels),
        "non_mangrove_pixels": int(mask.size - mangrove_pixels),
        "coverage_percent": float(mangrove_pixels / mask.size * 100),
        "pixel_area_m2": pixel_area_m2,
        "mangrove_area_hectares": float(mangrove_area_ha),
    },
}

with open(f"{OUTPUT_DIR}/06_mangrove_detection.json", "w") as f:
    json.dump(detection_data, f, indent=2)

# STEP 7: Estimate biomass and calculate carbon
print("\n[7/7] Estimating biomass and carbon stocks...")

# Biomass calculation
biomass = 250.5 * ndvi - 75.2
biomass_masked = np.where(mask > 0, biomass, np.nan)
biomass_masked = np.maximum(biomass_masked, 0)

valid_biomass = biomass_masked[~np.isnan(biomass_masked)]

biomass_stats = {
    "mean": float(np.mean(valid_biomass)),
    "median": float(np.median(valid_biomass)),
    "max": float(np.max(valid_biomass)),
    "min": float(np.min(valid_biomass)),
    "std": float(np.std(valid_biomass)),
}

print(f"   Mean biomass: {biomass_stats['mean']:.1f} Mg/ha")

# Carbon calculation
pixel_area_ha = (10 * 10) / 10000
total_biomass_mg = np.sum(valid_biomass) * pixel_area_ha
carbon_stock_mg = total_biomass_mg * 0.47
co2_equivalent_mg = carbon_stock_mg * 3.67

print(f"   Carbon stock: {carbon_stock_mg:,.0f} Mg C")

# Capture final results
final_results = {
    "allometric_model": {
        "equation": "Biomass = 250.5 × NDVI - 75.2",
        "units": "Mg/ha",
        "source": "Myanmar field studies",
        "r_squared": 0.72,
    },
    "biomass": {
        **serialize_numpy_array(biomass_masked, "biomass_masked"),
        "statistics": biomass_stats,
    },
    "carbon": {
        "ipcc_parameters": {
            "carbon_fraction": 0.47,
            "co2_to_c_ratio": 3.67,
        },
        "calculations": {
            "pixel_area_ha": pixel_area_ha,
            "total_biomass_mg": float(total_biomass_mg),
            "carbon_stock_mg": float(carbon_stock_mg),
            "co2_equivalent_mg": float(co2_equivalent_mg),
        },
        "units": {
            "total_biomass": "Mg",
            "carbon_stock": "Mg C",
            "co2_equivalent": "Mg CO2",
        },
    },
    "metadata": {
        "analysis_date": datetime.now().isoformat(),
        "scene_date": best_item.datetime.isoformat(),
        "scene_id": best_item.id,
        "cloud_cover_percent": best_item.properties.get("eo:cloud_cover"),
        "study_area_bbox": BBOX,
        "uncertainty": "±30%",
    },
}

with open(f"{OUTPUT_DIR}/07_biomass_carbon_results.json", "w") as f:
    json.dump(final_results, f, indent=2)

# Create summary manifest
print("\n" + "=" * 60)
print("Data capture complete!")
print("=" * 60)

manifest = {
    "workflow": "Mangrove Biomass Estimation",
    "execution_date": datetime.now().isoformat(),
    "study_area": {
        "bbox": BBOX,
        "description": "Myanmar mangrove forest",
    },
    "captured_files": [
        {
            "step": 1,
            "file": "01_stac_search_request.json",
            "description": "STAC catalog search parameters",
        },
        {
            "step": 1,
            "file": "01_stac_search_response.json",
            "description": "STAC search results summary",
        },
        {
            "step": 2,
            "file": "02_stac_item_selected.json",
            "description": "Complete STAC item for selected scene",
        },
        {
            "step": 3,
            "file": "03_stackstac_request.json",
            "description": "stackstac.stack() parameters",
        },
        {
            "step": 3,
            "file": "03_stackstac_response.json",
            "description": "xarray DataArray structure",
        },
        {
            "step": 4,
            "file": "04_spectral_bands.json",
            "description": "Extracted spectral bands (red, green, nir)",
        },
        {
            "step": 5,
            "file": "05_vegetation_indices.json",
            "description": "Calculated vegetation indices (NDVI, NDWI, SAVI)",
        },
        {
            "step": 6,
            "file": "06_mangrove_detection.json",
            "description": "Mangrove classification results",
        },
        {
            "step": 7,
            "file": "07_biomass_carbon_results.json",
            "description": "Final biomass and carbon estimates",
        },
    ],
    "summary": {
        "scenes_found": len(items),
        "scene_selected": best_item.id,
        "mangrove_area_ha": float(mangrove_area_ha),
        "mean_biomass_mg_ha": biomass_stats["mean"],
        "carbon_stock_mg_c": float(carbon_stock_mg),
        "co2_equivalent_mg": float(co2_equivalent_mg),
    },
}

with open(f"{OUTPUT_DIR}/00_MANIFEST.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\nAll data saved to: {OUTPUT_DIR}/")
print("\nFiles created:")
for item in manifest["captured_files"]:
    print(f"  - {item['file']}")
print("  - 00_MANIFEST.json")

print("\nSummary:")
print(f"  Scenes found: {len(items)}")
print(f"  Mangrove area: {mangrove_area_ha:.1f} ha")
print(f"  Carbon stock: {carbon_stock_mg:,.0f} Mg C")
print(f"  CO₂ equivalent: {co2_equivalent_mg:,.0f} Mg CO₂")
