# marimo Notebook Design Document

## Migration: Jupyter → marimo

**Date:** 2025-11-17
**Original:** `mangrove_workflow.ipynb`
**Target:** `mangrove_workflow_marimo.py`
**Goal:** Create a reactive, interactive mangrove monitoring workflow with enhanced Plotly visualizations

---

## Why marimo?

### Advantages Over Jupyter

1. **Reproducibility**
   - Stored as pure Python (not JSON) → better version control
   - Deterministic execution order based on dependency graph
   - No hidden state from out-of-order execution

2. **Reactivity**
   - Automatic re-execution when dependencies change
   - No manual "Run All" needed
   - Prevents stale outputs

3. **Collaboration with AI**
   - Claude Code can read/write Python directly
   - File watching with `--watch` flag for instant feedback
   - No base64-encoded outputs to confuse AI agents

4. **Deployment**
   - Run as script: `python mangrove_workflow_marimo.py`
   - Serve as web app: `marimo run mangrove_workflow_marimo.py`
   - Same file for development and production

5. **Interactive Visualizations**
   - Native support for `mo.ui.plotly()` with selections
   - Reactive updates based on user interactions
   - Better than static Plotly figures

---

## Architecture Differences

### Jupyter Pattern (Sequential, Imperative)

```python
# Cell 1: Define global variable
selected_site = None

# Cell 2: Button callback mutates global
def on_click(b):
    global selected_site
    selected_site = dropdown.value

button.on_click(on_click)

# Cell 3: Uses global variable (might be stale!)
if selected_site is not None:
    process(selected_site)
```

**Problems:**
- Hidden state in global variables
- Execution order matters
- No automatic updates when dropdown changes
- Hard to reason about dependencies

### marimo Pattern (Reactive, Functional)

```python
# Cell 1: Create UI element (returns dropdown object)
site_dropdown = mo.ui.dropdown(["Site A", "Site B"])

# Cell 2: Automatically runs when dropdown changes
selected_site = site_dropdown.value
mo.md(f"Selected: {selected_site}")

# Cell 3: Automatically updates when selected_site changes
processed_data = process(selected_site)
```

**Benefits:**
- Clear data flow through cell returns
- Automatic reactivity
- No hidden state
- Dependency graph makes execution order explicit

---

## Variable Scoping Strategy

### Problem: Global Variables in Jupyter

Current notebook uses module-level globals:
```python
selected_site = None
selected_bounds = None
sentinel2_data = None
sentinel2_items = None
mangrove_mask = None
ndvi_data = None
biomass_data = None
```

### Solution: Cell Returns in marimo

Each cell returns its output, which becomes available to dependent cells:

```python
# ❌ Jupyter: Global mutation
selected_site = "Thor Heyerdahl"

# ✅ marimo: Cell return
_site_name = site_dropdown.value  # Cell returns _site_name
```

**Naming Convention:**
- Public variables (used by other cells): `site_name`, `biomass_data`
- Private variables (local to cell): `_temp`, `_helper`

---

## Widget Migration Map

### Study Area Selection

**Jupyter:**
```python
location_dropdown = widgets.Dropdown(...)
initialize_button = widgets.Button(...)

def on_initialize_click(b):
    global selected_site, selected_bounds
    # ... mutation logic ...

initialize_button.on_click(on_initialize_click)
display(widgets.VBox([location_dropdown, initialize_button, output_area]))
```

**marimo:**
```python
# Cell 1: UI controls
site_dropdown = mo.ui.dropdown(
    options=list(STUDY_SITES.keys()),
    value=list(STUDY_SITES.keys())[0],
    label="Study Site:"
)

# Cell 2: Derived state (auto-updates)
selected_site = site_dropdown.value
site_info = STUDY_SITES[selected_site]
```

### Data Loading (Expensive Operation)

**Jupyter:**
```python
search_button = widgets.Button(description="Search")

def on_search_click(b):
    global sentinel2_data
    # ... expensive download ...
    sentinel2_data = result

search_button.on_click(on_search_click)
```

**marimo:**
```python
# Cell 1: Controls
cloud_cover = mo.ui.slider(0, 50, value=20, label="Max Cloud %")
days_back = mo.ui.slider(30, 365, value=90, step=30, label="Days Back")
load_data_button = mo.ui.run_button(label="🛰️ Search Sentinel-2 Data")

# Cell 2: Conditional execution
mo.stop(not load_data_button.value, "Click button to load data")

# Only runs when button clicked
sentinel2_data = load_sentinel2_cached(
    site_info["bounds"],
    cloud_cover.value,
    days_back.value
)
```

**Key Patterns:**
- `mo.ui.run_button()` → replaces action buttons
- `mo.stop()` → prevents expensive auto-execution
- Sliders/dropdowns auto-propagate changes

---

## Reactive Workflow Chains

### Chain 1: Site Selection
```
site_dropdown → selected_site → site_info → map_visualization
```

### Chain 2: Data Acquisition
```
[cloud_cover, days_back, load_button] → sentinel2_search → best_item → sentinel2_data
```

### Chain 3: Mangrove Detection
```
sentinel2_data → indices[ndvi,ndwi,savi] → mangrove_mask → detection_viz
```

### Chain 4: Biomass Estimation
```
[ndvi_data, mangrove_mask] → biomass_data → statistics → [isopleth_map, histogram]
```

### Chain 5: Export
```
biomass_data → summary_df → export_csv
```

**Auto-propagation:**
- Changing `cloud_cover` slider → re-searches → re-loads data → re-detects → re-estimates
- Use `mo.ui.run_button()` to break auto-propagation for expensive operations

---

## Plotly Integration Strategy

### Static Plotly (Current Jupyter)

```python
fig = go.Figure()
fig.add_trace(go.Scattermap(...))
fig.show()  # Just displays, no interaction
```

### Interactive Plotly (marimo)

```python
# Cell 1: Create interactive plot
map_plot = mo.ui.plotly(
    go.Figure(
        data=[go.Scattermap(...)],
        layout={"mapbox": {"style": "satellite"}}
    )
)
map_plot  # Display in cell output

# Cell 2: Use selections
selected_points = map_plot.value
mo.md(f"Selected {len(selected_points)} points")
```

### Enhanced Visualizations

1. **Interactive Study Area Map**
   - Select custom regions for analysis
   - Zoom to specific areas

2. **Brushable NDVI Scatter**
   - Select pixels → show in biomass distribution
   - Linked highlighting across views

3. **Threshold Tuning**
   - Sliders for NDVI/NDWI thresholds
   - Real-time mask update
   - Compare detection results

4. **Interactive Isopleth Map**
   - Click contours → show pixel details
   - Select regions → compute sub-area statistics

---

## Handling Expensive Operations

### Data Caching Strategy

```python
import os
from pathlib import Path

CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

def load_sentinel2_cached(bounds, cloud_cover, days_back):
    """Load with file-based caching"""
    cache_files = {
        "red": CACHE_DIR / "red.tif",
        "green": CACHE_DIR / "green.tif",
        "nir": CACHE_DIR / "nir.tif",
    }

    if all(f.exists() for f in cache_files.values()):
        # Load from cache (instant)
        return load_from_geotiff(cache_files)
    else:
        # Download and cache
        data = download_sentinel2(bounds, cloud_cover, days_back)
        save_to_geotiff(data, cache_files)
        return data
```

### Prevent Auto-Execution

```python
# Only run expensive cell when button clicked
detect_button = mo.ui.run_button(label="🌿 Detect Mangroves")
mo.stop(not detect_button.value, "Click to start detection")

# Rest of cell only executes when button clicked
indices = calculate_indices(sentinel2_data)
mangrove_mask = detect_mangroves(indices)
```

---

## File Structure

```
ospd-mangrove-demo/
├── mangrove_workflow.ipynb          # Original Jupyter (preserved)
├── mangrove_workflow_marimo.py      # New marimo notebook
├── run_mangrove_workflow.py         # Non-interactive script
├── data_cache/                      # Cached satellite data
│   ├── red.tif
│   ├── green.tif
│   └── nir.tif
├── docs/
│   ├── MARIMO_DESIGN.md            # This file
│   ├── MARIMO_USAGE.md             # User guide
│   └── MARIMO_MIGRATION.md         # Conversion log
└── requirements.txt                # Include marimo
```

---

## Development Workflow

### Iterative Loop with Claude Code

```bash
# Terminal 1: marimo with file watching
marimo edit --watch mangrove_workflow_marimo.py

# Terminal 2: Claude Code session
# 1. Claude suggests changes
# 2. Writes to .py file
# 3. marimo detects change → reloads
# 4. Validate in browser
# 5. Iterate
```

### Testing Checklist

After each iteration:

- [ ] Notebook loads without errors
- [ ] All cells execute in correct order
- [ ] Variables flow through dependency graph
- [ ] Widgets respond to interactions
- [ ] Visualizations render correctly
- [ ] Output CSV matches Jupyter version
- [ ] Can run as script: `python mangrove_workflow_marimo.py`
- [ ] No global variable conflicts
- [ ] Caching works correctly

---

## Expected Challenges

### 1. Variable Redefinition

**Problem:** marimo prohibits defining same variable in multiple cells

**Solution:**
```python
# ❌ Error: 'data' defined in two cells
# Cell 1
data = load_raw()

# Cell 2
data = process(data)  # ERROR!

# ✅ Solution: Use different names or single cell
# Cell 1
raw_data = load_raw()

# Cell 2
processed_data = process(raw_data)
```

### 2. Threading for Progress Indicators

**Problem:** Jupyter notebook uses threading for progress dots

**Solution:** Remove threading, use marimo's built-in progress or simple messages

### 3. Clear Output Pattern

**Problem:** Jupyter uses `clear_output(wait=True)`

**Solution:** Not needed! marimo cells automatically replace their output

### 4. Display Multiple Outputs

**Problem:** Jupyter allows multiple `display()` calls

**Solution:** Return tuple or use `mo.vstack()` / `mo.hstack()`

```python
# ❌ Jupyter pattern
display(fig1)
print("Some text")
display(fig2)

# ✅ marimo pattern
mo.vstack([
    fig1,
    mo.md("Some text"),
    fig2
])
```

---

## Success Metrics

### Functional Requirements

✅ **Parity with Jupyter**
- Same data processing logic
- Identical CSV outputs
- All visualizations present

✅ **Enhanced Interactivity**
- Reactive widget updates
- Interactive Plotly selections
- Real-time threshold tuning

✅ **Reproducibility**
- Deterministic execution
- No hidden state
- Version control friendly

### Performance Requirements

✅ **Caching**
- Sentinel-2 data cached to disk
- Sub-second reload from cache

✅ **Selective Execution**
- Expensive operations gated by run buttons
- No unnecessary re-computation

### Usability Requirements

✅ **Documentation**
- Clear usage instructions
- Widget behavior explained
- Comparison with Jupyter version

✅ **Deployment**
- Works as script
- Works as web app
- Works in marimo editor

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| 1. Setup | 15 min | Branch, docs, install |
| 2. Convert | 30 min | Auto-convert + fix errors |
| 3. Refactor | 1-2 hrs | Reactive architecture |
| 4. Enhance | 1 hr | Plotly interactivity |
| 5. Validate | 30 min | Test outputs, document |
| **Total** | **3-4 hrs** | Complete migration |

---

## References

- [marimo Documentation](https://docs.marimo.io/)
- [Migrating from Jupyter](https://docs.marimo.io/guides/coming_from/jupyter/)
- [Claude Code + marimo](https://marimo.io/blog/claude-code)
- [Plotly Integration](https://docs.marimo.io/guides/working_with_data/plotting/#plotly)
