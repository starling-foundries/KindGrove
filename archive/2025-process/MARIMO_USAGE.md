# marimo Notebook Usage Guide

**Notebook:** `mangrove_workflow_marimo.py`
**Purpose:** Interactive temporal analysis of mangrove biomass change

---

## Quick Start

### Installation

```bash
# Install marimo with SQL support
pip install "marimo[sql]"

# Install other dependencies
pip install -r requirements.txt

# Verify installation
marimo --version
```

### Running the Notebook

#### Option 1: Interactive Editor (Recommended)

```bash
marimo edit mangrove_workflow_marimo.py
```

- Opens in browser at `http://localhost:2718`
- Live editor with instant cell execution
- Interactive widgets and visualizations

#### Option 2: Web Application

```bash
marimo run mangrove_workflow_marimo.py
```

- User-facing application mode
- Code hidden, only outputs visible
- Perfect for demonstrations

---

## Workflow Steps

### 1. Study Site Selection

**UI Element:** Dropdown menu

Select from predefined study sites:
- **Can Gio Biosphere Reserve** (Vietnam) - UNESCO site, best coverage
- **Sundarbans** (Bangladesh/India) - World's largest mangrove forest
- **Thor Heyerdahl Climate Park** (Myanmar) - Restoration site
- **Wunbaik Reserved Forest** (Myanmar) - Biomass equation source

The map updates automatically to show:
- Green boundary: Study area extent
- Geographic center point

### 2. Temporal Configuration

**UI Element:** Cloud cover slider (10-50%)

Configure maximum cloud cover for scene selection. Lower values = cleaner data but fewer available scenes.

### 3. Load Temporal Data

**UI Element:** "Load Temporal Data" button

**Process:**
1. Click the button to begin data acquisition
2. System searches AWS STAC catalog for 4 strategic time points:
   - **Initial (2017):** Baseline measurement
   - **Pre-Cyclone Amphan (May 1-19, 2020):** Before major disturbance
   - **Post-Cyclone Amphan (June 5+, 2020):** After impact
   - **Current (2024):** Most recent state
3. For each time window, tries up to 5 scenes until finding one with >1% valid coverage
4. Downloads and caches band data (red, green, NIR)
5. Calculates NDVI and biomass for each valid scene

**Timing:** ~2-3 minutes for fresh data; instant for cached data

**Console Output:** Shows progress including scene dates and coverage percentages

### 4. Timelapse Visualization

**UI Element:** Time step slider

**Features:**
- Slide through temporal samples
- Each frame shows:
  - Biomass heatmap (green colorscale)
  - Date of acquisition
  - Mean biomass (Mg/ha)
  - Scene coverage percentage
  - Mangrove fraction (% of valid area)

**Interpretation:**
- Green = detected mangrove with biomass estimate
- Empty/transparent = no data or not classified as mangrove
- Coverage % indicates how much of bbox has valid data

### 5. Trend Analysis

**Auto-generated visualizations:**

**Time Series Chart:**
- Green line: Mean biomass over time
- Red dashed: Linear trend line with R² value
- Blue line: Mangrove area (secondary axis)

**Interpretation:**
- Upward trend = biomass growth
- R² near 1.0 = strong linear trend
- Large uncertainty if few data points

### 6. Change Summary

**Comparison Table showing scale-independent metrics:**

| Metric | Description |
|--------|-------------|
| Scene Coverage (%) | How much of bbox each scene covers |
| Mean Biomass (Mg/ha) | Average per hectare - comparable across scenes |
| Mangrove Fraction (%) | % of valid area that is mangrove |
| Carbon Density (Mg C/ha) | Carbon per hectare |

**Why Scale-Independent Metrics?**

Different scenes cover different portions of the study area. Absolute metrics (total area, total carbon) are misleading when coverage varies. Scale-independent metrics allow fair comparison.

---

## Key Parameters

### Mangrove Detection

```python
NDVI > 0.4  # Lower bound: healthy vegetation
NDVI < 0.95 # Upper bound: avoid saturation
```

### Biomass Equation

```python
Biomass (Mg/ha) = 250.5 × NDVI - 75.2
```
Source: Wunbaik Forest, Myanmar (R² = 0.72)

### Carbon Calculation

```python
Carbon = Biomass × 0.47  # IPCC 2006 standard
```

---

## Caching

**Location:** `data_cache/temporal/{site_name}/`

**Contents per scene:**
- `red.tif`, `green.tif`, `nir.tif` - Band data
- `biomass.tif` - Calculated biomass raster
- `stats.json` - Summary statistics

**Benefits:**
- First run: Downloads from AWS (~30 seconds per scene)
- Subsequent runs: Instant loading from cache
- Cache persists across sessions

**Clearing Cache:**
```bash
rm -rf data_cache/temporal/{site_name}/
```

---

## Troubleshooting

### "Need at least 2 samples for temporal analysis"

**Cause:** Not enough scenes passed the coverage threshold.

**Solutions:**
1. Try a different study site (Can Gio has best coverage)
2. Increase max cloud cover slider
3. Check console for coverage percentages

### Heatmap shows mostly empty

**Cause:** Scene only covers a portion of the bbox.

**This is expected** for sites at Sentinel-2 tile boundaries. The metrics are still valid - they're calculated only for the covered area.

### Inconsistent areas between time steps

**Cause:** Different scenes cover different portions.

**This is why we use scale-independent metrics.** Compare Mean Biomass and Mangrove Fraction, not absolute area.

---

## Export

Results are automatically exported to CSV:
- `{SiteName}_temporal_analysis.csv`

**Columns:**
- date, scene_id, cloud_cover_pct
- valid_coverage_pct, mangrove_fraction_pct
- biomass_mean_mg_ha, biomass_std_mg_ha
- carbon_density_mg_c_ha
- mangrove_area_ha, carbon_stock_mg_c (absolute values)

---

## Further Reading

- **[FINDINGS.md](../FINDINGS.md)** - Detailed methodology and lessons learned
- **[MARIMO_DESIGN.md](MARIMO_DESIGN.md)** - Architecture decisions
