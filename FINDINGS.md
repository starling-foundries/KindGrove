# Mangrove Biomass Temporal Analysis - Findings & Learnings

**Project:** OGC Open Science Persistent Demonstrator (OSPD)
**Workflow:** Mangrove Biomass Change Detection
**Date:** December 2025

---

## Executive Summary

This workflow demonstrates satellite-based mangrove biomass monitoring using open-access Sentinel-2 imagery via OGC-compliant APIs. The implementation showcases how OGC Building Blocks (bbox parameters, STAC APIs, CWL workflows) can be combined to create reproducible Earth observation analysis pipelines.

**Key Capabilities:**
- Temporal analysis across 4 strategic time points (2017-2024)
- Scale-independent metrics for fair comparison across scenes with variable coverage
- Interactive visualization via Marimo reactive notebook
- CWL-packaged workflow for automated execution

---

## Study Sites

| Site | Location | Size | Coverage Quality |
|------|----------|------|------------------|
| **Can Gio Biosphere Reserve** | Vietnam | ~75,000 ha | Good (single tile) |
| **Sundarbans** | Bangladesh/India | ~900 km² subset | Variable (tile boundaries) |
| **Thor Heyerdahl Climate Park** | Myanmar | 1,800 ha | Variable (tile boundaries) |
| **Wunbaik Reserved Forest** | Myanmar | ~4,000 ha | Moderate |

---

## Methodology

### Mangrove Detection
- **NDVI Threshold:** `0.4 < NDVI < 0.95`
  - Lower bound (0.4): Excludes water, bare soil, sparse vegetation
  - Upper bound (0.95): Avoids sensor saturation artifacts

### Biomass Estimation
- **Equation:** `Biomass (Mg/ha) = 250.5 × NDVI - 75.2`
- **Source:** Wunbaik Reserved Forest, Myanmar (R² = 0.72)
- **Carbon Fraction:** 47% of biomass (IPCC 2006 Guidelines)

### Temporal Sampling Strategy
Four strategic time windows to capture change dynamics:
1. **Initial (2017):** Baseline measurement
2. **Pre-Cyclone Amphan (May 1-19, 2020):** Before major disturbance
3. **Post-Cyclone Amphan (June 5+, 2020):** After impact assessment
4. **Current (2024):** Most recent state

---

## Scale-Independent Metrics

### The Problem
Individual Sentinel-2 scenes cover variable portions of study areas due to:
- Tile boundaries (~100km × 100km scenes)
- Cloud masking removing portions
- Orbit patterns causing variable overlap

This makes absolute metrics (total area, total carbon) incomparable across time.

### The Solution
We use **coverage-normalized metrics** that are comparable regardless of scene coverage:

| Metric | Definition | Why It Works |
|--------|------------|--------------|
| **Mean Biomass (Mg/ha)** | Average per hectare of observed mangrove | Scale-independent average |
| **Mangrove Fraction (%)** | % of valid pixels classified as mangrove | Density measure, not absolute |
| **Carbon Density (Mg C/ha)** | Carbon per hectare of mangrove | Comparable across scenes |
| **Scene Coverage (%)** | % of bbox with valid data | Transparency metric |

---

## Data Coverage Tradeoffs

### Current Approach: Sentinel-2 via AWS Earth Search
**Pros:**
- Open access, no credentials required
- 10m resolution
- Free via AWS Open Data

**Cons:**
- 5-day revisit (single satellite)
- Tile boundaries cause coverage gaps
- Cloud cover reduces usable scenes

### Alternative: Harmonized Landsat Sentinel (HLS)
For production workflows requiring consistent coverage:
- Combines Landsat 8/9 + Sentinel-2A/B/C
- 2-3 day revisit (more scene options)
- Analysis-ready with atmospheric correction
- **Trade-off:** Requires NASA Earthdata credentials, 30m resolution

---

## OGC Building Blocks Integration

### 1. Bounding Box (bbox) Parameter
```yaml
bbox:
  west: 94.462
  south: 17.044
  east: 94.502
  north: 17.082
crs: EPSG:4326
```
- Standard OGC bbox format used throughout
- Passed to STAC API queries
- Defines spatial extent for raster clipping

### 2. STAC API Integration
```python
catalog = Client.open("https://earth-search.aws.element84.com/v1")
search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime="2024-01-01/2024-12-31",
    query={"eo:cloud_cover": {"lt": 30}}
)
```
- OGC-compliant STAC endpoint for scene discovery
- Temporal and spatial filtering
- Cloud cover metadata filtering

### 3. CWL Workflow Packaging
```yaml
cwlVersion: v1.0
class: Workflow
inputs:
  bbox: string
  max_cloud_cover: int
  days_back: int
```
- Reproducible workflow definition
- Platform-independent execution
- OGC Application Package compliant

---

## Lessons Learned

### 1. Scene Validation is Critical
- **Issue:** Some scenes had <1% valid pixels within bbox
- **Solution:** Implemented coverage threshold (>1%) and try multiple scenes per time window
- **Learning:** Always validate scene coverage before processing

### 2. Absolute vs. Relative Metrics
- **Issue:** "Area increased 3x!" was actually just different scene coverage
- **Solution:** Use scale-independent metrics (fraction, density, mean)
- **Learning:** Always report coverage percentage alongside absolute values

### 3. Site Size Matters
- **Issue:** Large sites (Sundarbans) span multiple Sentinel-2 tiles
- **Solution:** Either use smaller bbox subsets or accept variable coverage
- **Learning:** Match site size to data source tile boundaries when possible

### 4. NDVI Thresholds Need Context
- **Issue:** Initial threshold (0.5-0.85) was too restrictive
- **Solution:** Reverted to literature standard (0.4-0.95)
- **Learning:** Document threshold choices and their sources

---

## Recommendations for Production

### Short-term Improvements
1. **Coverage Filtering:** Filter scenes by bbox overlap percentage before download
2. **Metadata Transparency:** Always display coverage % in outputs
3. **Multi-scene Selection:** Try multiple scenes per time window

### Long-term Enhancements
1. **HLS Integration:** For sites requiring consistent coverage
2. **Scene Mosaicking:** Combine multiple scenes from same time period
3. **Quality Flags:** Propagate uncertainty through calculations
4. **Site-Specific Calibration:** Develop local biomass equations

---

## Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Notebook** | Marimo | Reactive UI, interactive visualization |
| **Data Access** | pystac-client, stackstac | STAC API, lazy loading |
| **Raster Processing** | rioxarray, xarray | Geospatial data handling |
| **Visualization** | Plotly, Lonboard | Interactive maps and charts |
| **Workflow** | CWL | Reproducible execution |

---

## Uncertainty & Limitations

| Source | Magnitude | Notes |
|--------|-----------|-------|
| Biomass equation | ±30% | IPCC Tier 2 uncertainty |
| NDVI calibration | Variable | Equation from single site |
| Atmospheric correction | ~5% | L2A product uncertainty |
| Scene coverage | 1-100% | Site-dependent |
| Temporal sampling | Opportunistic | Cloud-dependent availability |

---

## Conclusion

This workflow demonstrates that OGC Building Blocks provide a solid foundation for satellite-based environmental monitoring. The key insight is that **scale-independent metrics are essential** when working with Earth observation data that has variable spatial coverage.

The combination of STAC APIs for discovery, bbox parameters for spatial queries, and CWL for workflow packaging creates a reproducible, standards-compliant analysis pipeline suitable for operational deployment.

---

## References

- IPCC 2006 Guidelines for National Greenhouse Gas Inventories
- Sentinel-2 User Handbook (ESA)
- NASA Harmonized Landsat Sentinel-2 (HLS) Documentation
- OGC SpatioTemporal Asset Catalog (STAC) Specification
