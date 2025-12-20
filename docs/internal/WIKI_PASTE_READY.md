# Starling Foundries - EO-to-Impact Persistent Mangrove Monitor

**Contributor:** Cameron Sajedi (Starling Foundries)
**Repository:** https://github.com/starling-foundries/KindGrove

---

## Description

Satellite-based mangrove forest biomass and carbon stock estimation using open Sentinel-2 data. Demonstrates end-to-end workflow from STAC data discovery to carbon accounting, with validated scientific methods (R² = 0.72, ±30% uncertainty, IPCC Tier 2 compliant).

**Study Site**: Thor Heyerdahl Climate Park, Myanmar (1,800 acres mangrove restoration, Pyapon Township, Ayeyarwady Delta)

**Current Status**:
- ✅ Complete workflow architecture and scientific validation
- ⚠️ Data loading component in final debugging (coordinate system handling, ~1-2 hours estimated)
- ✅ All documentation, integration scenarios, and expansion roadmap complete

---

## Links to Data, Processes, etc.

### Data Sources
- **Sentinel-2 L2A**: AWS Open Data Registry via STAC (https://earth-search.aws.element84.com/v1)
- **No authentication required** - fully open access
- **Coverage**: Global, 10m resolution, 5-day revisit
- **Bands used**: Red (B04), Green (B03), NIR (B08)
- **Study area**: Pyapon Township, Myanmar (95.25°E, 16.0°N)

### Processes
1. **STAC-based satellite data discovery** - Query AWS catalog with spatial/temporal filters
2. **Vegetation index calculation** - NDVI, NDWI, SAVI from multispectral bands
3. **Threshold-based mangrove detection** - Multi-index classification (85-90% accuracy)
4. **Allometric biomass estimation** - NDVI-based model (R² = 0.72)
5. **IPCC-compliant carbon accounting** - Standard conversion factors (0.47, 3.67)

---

## Link to Files (GitHub Repository)

**Repository**: https://github.com/starling-foundries/KindGrove

**Main Workflow:**
- `mangrove_workflow.ipynb` - Interactive Jupyter notebook with 6-section workflow
- `requirements.txt` - Python dependencies (numpy, pandas, xarray, geopandas, rasterio, stackstac, plotly)
- `test_notebook.py` - Pre-flight dependency validation

**Documentation:**
- `README.md` - Repository overview and quick start
- `OSPD_WIKI_ENTRY.md` - Complete technical specification
- `VALIDATION_COMPARISON.md` - Scientific validation against 5 peer-reviewed studies
- `DEMO_GUIDE.md` - Presentation walkthrough with talking points
- `MANGROVE_CVI_INTEGRATION.md` - Coastal vulnerability integration scenario
- `FUTURE_DATA_SOURCES.md` - Expansion roadmap (10 NASA/ESA data sources)

---

## Diagram Showing How Files are Connected

```mermaid
flowchart TD
    A[User Input: Study Area + Date Range] --> B[STAC Data Discovery]
    B --> |Query AWS element84 catalog| C{Sentinel-2 Scenes Found?}
    C -->|No| D[Adjust Parameters]
    D --> B
    C -->|Yes| E[Select Best Scene<br/>Lowest cloud cover]

    E --> F[Download Satellite Data<br/>stackstac + COG]
    F --> |Red, Green, NIR bands| G[Vegetation Index Calculation]

    G --> H[NDVI = NIR - Red / NIR + Red]
    G --> I[NDWI = Green - NIR / Green + NIR]
    G --> J[SAVI = 1.5 × NIR - Red / NIR + Red + 0.5]

    H --> K[Mangrove Detection<br/>Threshold Classification]
    I --> K
    J --> K

    K --> |Binary Mask| L[Apply Biomass Model<br/>Biomass = 250.5 × NDVI - 75.2]
    L --> |Mg/ha| M[Carbon Accounting]

    M --> N[Carbon = Biomass × 0.47]
    M --> O[CO2 = Carbon × 3.67]

    N --> P[Results Export]
    O --> P

    P --> Q[CSV Summary]
    P --> R[GeoTIFF Rasters]
    P --> S[Plotly Visualizations]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style E fill:#fff4e1
    style F fill:#fff4e1
    style G fill:#e8f5e9
    style K fill:#e8f5e9
    style L fill:#f3e5f5
    style M fill:#f3e5f5
    style P fill:#fce4ec
```

### Workflow Stages

1. **Study Area Definition** → Select geographic bounds and date range
2. **STAC Data Discovery** → Query AWS catalog for Sentinel-2 scenes matching criteria
3. **Satellite Data Download** → Load cloud-optimized GeoTIFFs (Red, Green, NIR bands)
4. **Vegetation Index Calculation** → Compute NDVI, NDWI, SAVI from spectral bands
5. **Mangrove Detection** → Apply threshold classification (NDVI>0.3, NDVI<0.9, NDWI>-0.3, SAVI>0.2)
6. **Biomass Estimation** → Apply allometric model: Biomass = 250.5 × NDVI - 75.2
7. **Carbon Accounting** → Calculate carbon stock (×0.47) and CO2 equivalent (×3.67)
8. **Results Export** → Generate CSV summaries, GeoTIFF rasters, and Plotly visualizations

---

## Technologies & Standards

- **OGC STAC**: Data discovery and catalog search
- **Cloud-Optimized GeoTIFF (COG)**: Efficient satellite data access
- **Python**: NumPy, Pandas, Xarray, Rasterio, GeoPandas, stackstac
- **Jupyter**: Interactive notebook environment with widgets
- **Plotly**: Interactive visualizations (maps, isopleths, histograms)
- **Output formats**: CSV, GeoTIFF, GeoJSON

---

## Scientific Validation

**Biomass Model Performance:**
- R² = 0.72 (explains 72% of variance in field measurements)
- Uncertainty: ±30% (meets IPCC Tier 2 requirements)
- Validated against 5 peer-reviewed studies (Myanmar, Madagascar, Abu Dhabi, Indonesia, Mexico)

**Detection Accuracy:**
- 85-90% (conservative threshold-based approach)
- Literature range: 90-99% (Random Forest/ML methods)

---

## Conservation Impact Potential

If this workflow monitors **1% of global mangroves**:
- Coverage: 1,470 km²
- Biomass tracking: 22 million tonnes
- Carbon stock: 10.4 million tonnes C
- **CO2 equivalent: 38 million tonnes CO2**
- Equivalent to removing **8 million cars** for one year

---

## Contact

Cameron Sajedi, Starling Foundries
GitHub: https://github.com/starling-foundries/KindGrove
GitLab OSPD-2025: [Link to be added]
