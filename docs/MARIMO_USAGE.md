# marimo Notebook Usage Guide

**Notebook:** `mangrove_workflow_marimo.py`
**Purpose:** Interactive mangrove monitoring workflow with reactive visualizations

---

## Quick Start

### Installation

```bash
# Install marimo with SQL support
pip install "marimo[sql]"

# Verify installation
marimo --version
```

### Running the Notebook

#### Option 1: Interactive Editor (Recommended)

```bash
# Start marimo in edit mode
marimo edit mangrove_workflow_marimo.py
```

- Opens in browser at `http://localhost:2718`
- Live editor with instant cell execution
- Interactive widgets and visualizations
- Auto-saves changes

#### Option 2: Web Application

```bash
# Run as read-only web app (hides code)
marimo run mangrove_workflow_marimo.py
```

- User-facing application mode
- Code hidden, only outputs visible
- Perfect for sharing with stakeholders

#### Option 3: Python Script

```bash
# Execute as standard Python script
python mangrove_workflow_marimo.py
```

- Non-interactive execution
- Useful for automation/CI/CD
- Same results as interactive mode

---

## Workflow Steps

### 1. Study Area Selection

**UI Element:** Dropdown menu

- Select from predefined study sites
- Map updates automatically when selection changes
- Shows site boundaries, center point, and metadata

**Interactive Map:**
- Red boundary: Study area extent
- Red star: Geographic center
- Hover for coordinates

### 2. Satellite Data Acquisition

**UI Elements:**
- Cloud Cover slider (0-50%)
- Days Back slider (30-365 days)
- "Search & Load" button

**Workflow:**
1. Adjust cloud cover threshold (default: 20%)
2. Set date range (default: 90 days)
3. Click "Search & Load" button
4. System searches AWS STAC catalog
5. Displays available scenes
6. Automatically loads best scene (lowest cloud cover)

**Caching:**
- First run: Downloads from AWS (30-60 seconds)
- Subsequent runs: Loads from `data_cache/` (instant)
- Cache persists across sessions

### 3. Mangrove Detection

**UI Element:** "Detect Mangroves" button

**Process:**
1. Click button to start detection
2. Calculates vegetation indices (NDVI, NDWI, SAVI)
3. Applies threshold-based classification
4. Displays results:
   - Left panel: NDVI heatmap
   - Right panel: Mangrove mask (green = mangrove, gray = non-mangrove)
5. Shows statistics (area in hectares, coverage percentage)

**Method:**
- NDVI > 0.3: Vegetation present
- NDVI < 0.9: Not upland forest
- NDWI > -0.3: Near water
- SAVI > 0.2: Adjusted for soil reflectance

### 4. Biomass Estimation

**UI Element:** "Estimate Biomass" button

**Process:**
1. Click button to estimate biomass
2. Applies allometric equation: Biomass = 250.5 × NDVI - 75.2
3. Displays results:
   - **Isopleth map:** Contour lines showing biomass distribution
   - **Histogram:** Distribution of biomass values
4. Shows comprehensive statistics:
   - Mean, Median, Max, Std Dev (Mg/ha)
   - Total Biomass, Carbon Stock, CO₂ Equivalent

**Interpretation:**
- Contour intervals: 20 Mg/ha
- Hover over map for specific pixel values
- Histogram shows frequency distribution

### 5. Results Summary & Export

**UI Elements:**
- Summary table (auto-generated)
- "Export Results" button

**Summary Table:**
- Study site name
- Analysis date
- All key metrics
- ±30% uncertainty estimate

**Export:**
1. Click "Export Results" button
2. Generates two files:
   - `{SiteName}_summary.csv`: Summary statistics
   - `{SiteName}_biomass.csv`: Full biomass raster (>16MB)
3. Files saved in current directory

---

## Reactivity Features

### Automatic Updates

**marimo automatically re-runs dependent cells when inputs change:**

- Change study site → map updates instantly
- Adjust cloud cover → (no auto-reload; click button to re-search)
- Modify thresholds → would update detection (not implemented yet)

### Manual Triggers

**Expensive operations require button clicks to prevent unwanted execution:**

- Data loading (30-60 seconds)
- Mangrove detection (<1 second)
- Biomass estimation (<1 second)
- Export operations

This design balances interactivity with performance.

---

## Interactive Visualizations

### Map Interactions

**Study Area Map:**
- Zoom with scroll wheel
- Pan by dragging
- Hover for details

**Biomass Isopleth Map:**
- Zoom to specific regions
- Hover for pixel-level biomass values
- Interactive legend

### Plot Features

All Plotly visualizations support:
- Zoom (click-drag box)
- Pan (click-drag after zooming)
- Reset (double-click)
- Download (camera icon)
- Hover tooltips

---

## Collaborative Editing with Claude Code

### Setup

```bash
# Terminal 1: Start marimo with file watching
marimo edit --watch mangrove_workflow_marimo.py

# Terminal 2: Claude Code session
# Make changes → marimo auto-reloads → validate → iterate
```

### Workflow

1. **Claude suggests changes** in Terminal 2
2. **Claude writes to .py file**
3. **marimo detects change** (via `--watch`)
4. **Browser reloads automatically**
5. **Validate results** in browser
6. **Iterate** until complete

### Benefits

- No manual reloads needed
- Instant feedback loop
- Clear separation (Claude writes, human validates)
- marimo's Python format is AI-friendly

---

## Data Sources

### Satellite Imagery

- **Provider:** ESA Copernicus (via AWS Open Data)
- **Dataset:** Sentinel-2 L2A (Level-2A, atmospherically corrected)
- **Resolution:** 10 meters
- **Bands:** Red, Green, NIR (Near-Infrared)
- **Catalog:** AWS STAC (element84)
- **Authentication:** None required

### Access

```python
# STAC catalog search
catalog = Client.open("https://earth-search.aws.element84.com/v1")
search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=[west, south, east, north],
    datetime="2024-08-01/2024-11-01",
    query={"eo:cloud_cover": {"lt": 20}}
)
```

### Caching Strategy

- **Cache directory:** `data_cache/`
- **Format:** GeoTIFF (LZW compression)
- **Files:** red.tif, green.tif, nir.tif
- **Size:** ~5MB total per study site
- **Persistence:** Until manually deleted

---

## Methodology

### Vegetation Indices

1. **NDVI (Normalized Difference Vegetation Index)**
   ```
   NDVI = (NIR - Red) / (NIR + Red)
   ```
   - Range: -1 to +1
   - Interpretation: >0.3 indicates vegetation

2. **NDWI (Normalized Difference Water Index)**
   ```
   NDWI = (Green - NIR) / (Green + NIR)
   ```
   - Range: -1 to +1
   - Interpretation: >-0.3 indicates near water

3. **SAVI (Soil Adjusted Vegetation Index)**
   ```
   SAVI = ((NIR - Red) / (NIR + Red + L)) × (1 + L)
   where L = 0.5
   ```
   - Adjusts for soil background
   - More accurate in sparse vegetation

### Biomass Estimation

**Allometric Equation:**
```
Biomass (Mg/ha) = 250.5 × NDVI - 75.2
```

**Source:** Southeast Asian mangrove studies

**Validation:**
- R² = 0.72 (explains 72% of variance)
- Based on field measurements
- Uncertainty: ±30%

**Carbon Accounting:**
```
Carbon Stock (Mg C) = Total Biomass × 0.47
CO₂ Equivalent (Mg) = Carbon Stock × 3.67
```

---

## Troubleshooting

### Issue: No scenes found

**Symptoms:** "❌ No scenes found with <X% cloud cover"

**Solutions:**
1. Increase cloud cover threshold (try 30-50%)
2. Extend date range (try 180-365 days)
3. Check internet connection
4. Verify study site coordinates

### Issue: Download fails

**Symptoms:** Error during satellite data download

**Solutions:**
1. Check internet connection (AWS S3 access required)
2. Clear cache: `rm -rf data_cache/`
3. Try again (transient network issues)
4. Check firewall/proxy settings

### Issue: Notebook won't start

**Symptoms:** `marimo edit` fails to start

**Solutions:**
```bash
# Reinstall marimo
pip install --upgrade marimo

# Check Python version (3.10+ required)
python --version

# Try different port
marimo edit --port 2719 mangrove_workflow_marimo.py
```

### Issue: Cell won't execute

**Symptoms:** Cell shows "waiting" indefinitely

**Solutions:**
1. Check for errors in dependent cells
2. Ensure all required data is loaded
3. Restart kernel: Click ⟳ in marimo UI
4. Check console for error messages

### Issue: Reactivity not working

**Symptoms:** Changes don't propagate

**Solutions:**
1. Ensure cells have proper returns
2. Check variable dependencies
3. Restart notebook
4. Review dependency graph (marimo UI)

---

## Performance Tips

### Optimizing Load Times

1. **Use cache:** Don't delete `data_cache/` between runs
2. **Smaller study areas:** Reduce bbox size for faster downloads
3. **Higher cloud tolerance:** More scenes available = faster search
4. **Local data:** Pre-download GeoTIFFs if running repeatedly

### Memory Management

- **Typical usage:** ~500MB RAM
- **Peak usage:** ~1.5GB (during download)
- **Large study areas:** Consider increasing resolution to 0.0002° (reduces data)

### Browser Performance

- **Chrome recommended** (best Plotly performance)
- **Close other tabs** (reduces memory pressure)
- **Disable browser extensions** (can interfere with WebSockets)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + S` | Save notebook |
| `Ctrl/Cmd + Enter` | Run cell |
| `Shift + Enter` | Run cell and move to next |
| `Ctrl/Cmd + /` | Comment/uncomment |
| `Tab` | Autocomplete |
| `Shift + Tab` | Show documentation |

---

## Comparison with Jupyter Version

| Feature | Jupyter | marimo |
|---------|---------|--------|
| **File Format** | JSON (.ipynb) | Python (.py) |
| **Execution** | Manual, sequential | Automatic, reactive |
| **State** | Hidden globals | Explicit dependencies |
| **Widgets** | ipywidgets | marimo.ui |
| **Reactivity** | None | Full reactive graph |
| **Version Control** | Difficult (JSON diffs) | Easy (Python diffs) |
| **Collaboration** | Merge conflicts | Clean git diffs |
| **Deployment** | Voilà, Jupyter Lab | `marimo run` |
| **Script Mode** | Conversion needed | Native support |

---

## Advanced Usage

### Running as Script with Parameters

```python
# Modify mangrove_workflow_marimo.py
# Add at top of file:
import sys
if len(sys.argv) > 1:
    override_site = sys.argv[1]
```

Then run:
```bash
python mangrove_workflow_marimo.py "Thor Heyerdahl Climate Park"
```

### Batch Processing

```bash
# Process multiple sites
for site in "Site A" "Site B" "Site C"; do
    python mangrove_workflow_marimo.py "$site"
done
```

### Integration with Workflows

```yaml
# GitHub Actions example
- name: Run mangrove analysis
  run: |
    pip install "marimo[sql]"
    python mangrove_workflow_marimo.py
    # Upload results
```

---

## Further Reading

- [marimo Documentation](https://docs.marimo.io/)
- [Claude Code + marimo Blog Post](https://marimo.io/blog/claude-code)
- [Plotly Documentation](https://plotly.com/python/)
- [Sentinel-2 User Guide](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi)
- [STAC Specification](https://stacspec.org/)

---

## Support

For issues specific to:
- **marimo:** https://github.com/marimo-team/marimo/issues
- **This notebook:** Open issue in this repository
- **Sentinel-2 data:** ESA Copernicus support forum
- **STAC catalog:** AWS element84 documentation

---

**Happy Analyzing!** 🌿📊🛰️
