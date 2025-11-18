# STAC Data Flow Capture

This directory contains **actual API responses and intermediate data** from a complete execution of the mangrove biomass estimation workflow.

## Purpose

These JSON files document the **real data structures** used throughout the workflow, providing concrete examples for:
- Understanding STAC API response formats
- Validating data processing pipelines
- Creating workflow documentation
- Developing OGC Application Package specifications

## Execution Details

- **Execution Date**: 2025-10-23T18:17:52
- **Study Area**: Myanmar mangrove forest (95.15°E to 95.35°E, 15.9°N to 16.1°N)
- **Scene Selected**: S2B_46PGC_20251003_0_L2A
- **Scene Date**: 2025-10-03
- **Cloud Cover**: 14.5%

## Files Overview

### Step 1: STAC Catalog Search
- **01_stac_search_request.json** - Input parameters to `pystac_client.Client.search()`
- **01_stac_search_response.json** - Summary of search results (1 scene found)

### Step 2: STAC Item Selection
- **02_stac_item_selected.json** - Complete STAC Item with full metadata
  - GeoJSON Feature format
  - Assets (red, green, nir bands) with S3 URLs
  - Properties (cloud cover, sun angle, etc.)
  - Scene geometry and bounding box

### Step 3: Imagery Download (stackstac)
- **03_stackstac_request.json** - Input parameters to `stackstac.stack()`
- **03_stackstac_response.json** - xarray DataArray structure
  - Dimensions: [time=1, band=3, y=2000, x=2000]
  - Coordinates: time, band, x, y (WGS84)
  - All STAC metadata as coordinates
  - Data statistics (min, max, mean, std)

### Step 4: Spectral Band Extraction
- **04_spectral_bands.json** - Individual band statistics
  - Red band (B04, 665nm)
  - Green band (B03, 560nm)
  - NIR band (B08, 842nm)
  - Reflectance value histograms

### Step 5: Vegetation Indices
- **05_vegetation_indices.json** - Calculated indices
  - NDVI: (NIR - Red) / (NIR + Red)
  - NDWI: (Green - NIR) / (Green + NIR)
  - SAVI: ((NIR - Red) / (NIR + Red + 0.5)) × 1.5
  - Statistical distributions

### Step 6: Mangrove Detection
- **06_mangrove_detection.json** - Classification results
  - Binary mask (mangrove vs non-mangrove)
  - Classification criteria (thresholds)
  - Area statistics: **713.07 hectares** detected

### Step 7: Biomass & Carbon Results
- **07_biomass_carbon_results.json** - Final estimates
  - Biomass statistics (mean: 17.9 Mg/ha)
  - Carbon stock: **6,010 Mg C**
  - CO₂ equivalent: **22,055 Mg CO₂**
  - IPCC conversion factors
  - Uncertainty: ±30%

### Manifest
- **00_MANIFEST.json** - Index of all files with execution summary

## Data Structure Patterns

### STAC Item Format (GeoJSON)
```json
{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "S2B_46PGC_20251003_0_L2A",
  "collection": "sentinel-2-l2a",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": {
    "datetime": "2025-10-03T04:14:05.490000Z",
    "eo:cloud_cover": 14.536516,
    "platform": "sentinel-2b"
  },
  "assets": {
    "red": { "href": "s3://...", "eo:bands": [...] }
  }
}
```

### xarray DataArray Structure
```json
{
  "type": "xarray.DataArray",
  "dims": ["time", "band", "y", "x"],
  "shape": [1, 3, 2000, 2000],
  "coords": {
    "time": { "dtype": "datetime64[ns]", "sample_values": [...] },
    "band": { "dtype": "<U5", "sample_values": ["red", "green", "nir"] },
    "x": { "dtype": "float64", "min": 95.15, "max": 95.35 },
    "y": { "dtype": "float64", "min": 15.9, "max": 16.1 }
  },
  "data": {
    "dtype": "float64",
    "shape": [1, 3, 2000, 2000],
    "sample_statistics": { "min": -0.0999, "max": 1.8896 }
  }
}
```

### Statistics Pattern
```json
{
  "name": "ndvi",
  "shape": [2000, 2000],
  "dtype": "float64",
  "statistics": {
    "mean": 0.412,
    "median": 0.389,
    "min": -0.234,
    "max": 0.876,
    "std": 0.156
  },
  "histogram": {
    "bins": 10,
    "counts": [...],
    "edges": [...]
  }
}
```

## Key Findings from Captured Data

### STAC Asset URLs
Real Sentinel-2 COG URLs from AWS:
```
https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/46/P/GC/2025/10/S2B_46PGC_20251003_0_L2A/B04.tif
```

### Critical stackstac Parameters
```python
stackstac.stack(
    items,
    assets=["red", "green", "nir"],
    epsg=4326,                    # WGS84 for geographic coordinates
    resolution=0.0001,            # ~10m at equator
    bounds_latlon=bbox,           # CRITICAL: clip during load
    chunksize=(1, 1, 512, 512)    # Dask chunk size
)
```

### Data Dimensions
- **Input**: Sentinel-2 tile (10,980 × 10,980 pixels at 10m)
- **Clipped**: Study area (2,000 × 2,000 pixels)
- **Total pixels**: 4,000,000
- **Mangrove pixels**: 71,307 (1.78% coverage)
- **Area**: 713 hectares

### Reflectance Values
- **Range**: -0.0999 to 1.8896 (surface reflectance)
- **Scale**: Values are already scaled (0.0001 factor applied)
- **Offset**: BOA offset applied (earthsearch:boa_offset_applied=true)

## Usage

These files can be used to:

1. **Validate workflow implementations** - Compare your output to these reference files
2. **Generate documentation** - Extract schema definitions from actual data
3. **Test parsers** - Use real-world examples for unit tests
4. **Understand STAC** - See complete, real STAC Items from AWS Element84

## Reproducing This Data

Run the capture script:
```bash
python capture_stac_data.py
```

This will create a new timestamped directory with fresh API responses.

## Related Files

- **capture_stac_data.py** - Script that generated this data
- **STAC_DATA_FLOW.json** - Comprehensive workflow documentation
- **mangrove_workflow_cli.py** - Production CLI implementation

## Notes

- All data is from **real API calls** to AWS Element84 STAC catalog
- Scene date (Oct 3, 2025) is in the **future** relative to knowledge cutoff - this is a time-travel scenario
- File sizes are kept small by storing statistics rather than full arrays
- GeoJSON follows STAC spec v1.1.0
- Cloud-Optimized GeoTIFFs (COG) are used for all imagery

---

**Generated**: 2025-10-23 by capture_stac_data.py
**Workflow**: Mangrove Biomass Estimation v1.0.0
