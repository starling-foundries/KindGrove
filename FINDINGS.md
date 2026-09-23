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

---

## 2026 Addendum: what the fingerprints found

*September 2026. The workflow was revisited to give every entity in its provenance a fingerprint
(see `docs/FINGERPRINTS.md`). Three of the lessons above turned out to have sharper versions than
we knew, and a fourth appeared.*

### A. Scene selection by cloud cover alone chose the worst scenes
Lesson 1 and Recommendation 1 above were right, but the 2025 fix (lower the valid-pixel threshold to
1 % and try up to five scenes, lowest cloud first) still ranked candidates by cloud cover only. For
the Sundarbans it selected a 4 % coverage scene for 2017 and a 2 % coverage scene for 2024 while
zero-cloud scenes covering 100 % of the bbox were in the same candidate list. The recommendation,
*filter scenes by bbox overlap percentage before download*, is now implemented as a query against
an index of the candidates' STAC footprints (`scripts/prime_cache.py`, the temporal-load cell of
`mangrove_workflow_marimo.py`): no pixel is read to rank them. All four Sundarbans scenes now cover
100 % of the bbox and all four Can Gio scenes share one tile footprint.

### B. Every scene from 2022 onward was radiometrically wrong
Sentinel-2 processing baseline 04.00 (January 2022) declares a BOA offset in `raster:bands`. Earth
Search delivers those scenes with the offset already removed (`earthsearch:boa_offset_applied`) but
keeps the declaration, and stackstac's rescale applies it again. Red reflectance went negative and
NDVI overshot the 0.95 cap, so mangrove was under-detected and biomass under-estimated on every
2022-or-later scene in the 2025 results. Fixed in the notebook, the CLI, the CWL notebook and the
cache script. A set difference of the 2017 and 2024 mangrove footprints on a fair grid surfaced it as
a near-total "loss" between two January scenes.

### C. Scale-independent metrics can be computed rather than hand-built
Lesson 2 above introduced coverage-normalised metrics by hand. With each scene's valid-data
footprint as a fingerprint on the equal-area rHEALPix grid, the comparable region is the
intersection of the roots, and the mangrove share of that region is the number that means the same
thing on every date. The application package now stamps every STAC item with its root
(`cwl/fingerprint.cwl`), and `archive/2026-process/THEN_AND_NOW.md` walks each 2025 pain point to its 2026 patch.

### D. A stalled fetch would have hung a job forever
During testing the analysis step sat at zero CPU for thirteen minutes, twice, after "Downloading
bands". The 2025 loaders had no timeout on the search or on the byte-range reads behind
stackstac, and no ceiling on a fetch. Inspecting the stuck process showed the second case was not
the network: the bytes had arrived, every socket was closed, and all 36 threads were waiting on a
lock, a deadlock inside the worker threads (observed under x86 emulation on an arm64 laptop).
Two guards now cover both: every request has a timeout and a retry budget, and every scene fetch
runs under a hard ten-minute deadline. A scene that cannot be fetched is skipped for the next
candidate, and a job with no fetchable candidate reports the reasons and exits non-zero even if
a wedged thread would otherwise keep the process alive (`earthsearch.py`; inlined in the CWL
notebook). Tests drive GDAL at a non-routable address and a fetch that never returns.

### Reproducing the 2026 numbers
`uv run python scripts/prime_cache.py "<site>"` for each site, then `uv run marimo run fingerprints_marimo.py`;
last year's selection for comparison: `--rule cloud --out temporal_2025`. The application package:
`cwltool --no-match-user --no-read-only mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input.yml`,
then `python cwl/fingerprint.py --stac outputs --check --deep` verifies every fingerprint from the JSON and the rasters.
