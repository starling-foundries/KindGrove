# Mangrove Workflow Notebook - Quick Start Guide

## Overview
This notebook demonstrates end-to-end mangrove monitoring using open satellite data without any API keys or authentication.

## Workflow Steps

### 1. **Study Area Selection**
- Interactive dropdown to select Thor Heyerdahl Climate Park
- Map viewport shows selected location on satellite imagery
- Click "Initialize Study Area" to lock in selection
- All subsequent maps sync to this location

### 2. **Satellite Data Acquisition**
- Searches AWS STAC catalog for Sentinel-2 imagery
- Adjust cloud cover threshold (default: 20%)
- Adjust date range (default: last 90 days)
- Automatically loads best scene (lowest cloud cover)
- **No authentication required** - uses AWS Open Data

### 3. **Mangrove Detection**
- Calculates vegetation indices (NDVI, NDWI, SAVI)
- Applies threshold-based classification
- Shows NDVI and mangrove mask side-by-side
- Reports total mangrove area in hectares

### 4. **Biomass Estimation**
- Uses NDVI-based allometric equation
- Creates **isopleth/contour map** showing biomass gradients
- Displays histogram of biomass distribution
- Calculates carbon stock and CO₂ equivalent

### 5. **Results & Export**
- Summary table with key statistics
- Exports CSV files:
  - Summary statistics
  - Biomass raster data
- Methodology documentation

## Key Features

### ✅ Open Data Only
- Sentinel-2 L2A (ESA Copernicus)
- AWS Open Data Registry
- No API keys required
- No authentication needed

### ✅ Interactive Workflow
- ipywidgets buttons for each step
- Progress feedback at each stage
- Clear error messages if steps skipped
- Visual outputs throughout

### ✅ Scientific Methods
Based on published research (see methodology section):
- **Mangrove detection**: 90-99% accuracy
- **Biomass estimation**: ±30% uncertainty (IPCC Tier 2)
- **Carbon conversion**: Standard 0.47 factor

### ✅ Visualizations
- Satellite base maps showing study area
- NDVI heatmaps
- Mangrove extent overlay
- **Isopleth/contour maps** for biomass gradients
- Distribution histograms
- Styled summary tables

## Technical Stack

### Data Access
- `pystac-client` - STAC catalog search
- `stackstac` - STAC to xarray conversion
- `rioxarray` - Raster I/O

### Processing
- `numpy` - Array operations
- `xarray` - Multidimensional arrays
- `geopandas` - Vector operations

### Visualization
- `plotly` - Interactive maps and charts
- `ipywidgets` - Workflow controls

### Requirements
```bash
pip install pystac-client stackstac rioxarray numpy pandas xarray geopandas plotly ipywidgets
```

## Usage

1. Open Jupyter Lab:
```bash
jupyter lab mangrove_workflow.ipynb
```

2. Run cells sequentially

3. Follow the interactive workflow:
   - Select study area → Initialize
   - Search satellite data → Auto-load
   - Detect mangroves → View results
   - Estimate biomass → View isopleth map
   - Export results

## Outputs

### Generated Files
- `Thor_Heyerdahl_Climate_Park_summary.csv` - Statistics
- `Thor_Heyerdahl_Climate_Park_biomass.csv` - Raster data

### Visualizations
- Interactive satellite map with study area
- NDVI and mangrove detection comparison
- Biomass isopleth/contour map (20 Mg/ha intervals)
- Biomass distribution histogram
- Styled summary table

## Extensibility

### Adding New Study Sites
Edit the `STUDY_SITES` dictionary:
```python
STUDY_SITES = {
    'New Site Name': {
        'center': (lon, lat),
        'bounds': {'west': w, 'east': e, 'south': s, 'north': n},
        'country': 'Country Name',
        'description': 'Site description'
    }
}
```

### Future Enhancements
- Multi-temporal change detection
- Sentinel-1 SAR integration
- GEDI LiDAR canopy height
- Random Forest classification
- OGC WPS service endpoints
- Real-time disturbance alerts

## Scientific Validity

### Methods Based On
- Global Mangrove Watch methodology
- GEEMMM (Google Earth Engine Mangrove Mapping)
- 600+ field plot validation (Mexico CONABIO)
- Research synthesis: "Satellite-based mangrove monitoring for climate credit MRV"

### Accuracy Targets
- Extent mapping: 90-99% overall accuracy
- Biomass estimation: R² = 0.72
- Uncertainty: ±30% (meets IPCC Tier 2)

### Limitations
- Single-date analysis (no time series)
- C-band saturation at 50-70 Mg/ha not addressed
- Species composition not assessed
- Below-ground carbon not measured
- Simulated workflow (not operational MRV)

## OGC/EarthCODE Compatibility

### Standards Compliance
- STAC-based data discovery
- CF-compliant data structures (xarray)
- GeoJSON/GeoTIFF outputs
- Documented processing steps

### Future Integration
- OGC API - Processes (WPS)
- OGC API - Coverages
- STAC metadata for outputs
- Interoperable with EarthCODE platforms

## Support

For issues or questions:
- Check methodology section in notebook
- Review error messages (they're descriptive!)
- Adjust cloud cover threshold if no scenes found
- Increase date range if data sparse

## License

Open source demonstration for educational and research purposes.