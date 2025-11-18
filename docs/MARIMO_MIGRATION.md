# marimo Migration Log

**Date Started:** 2025-11-17
**Status:** In Progress
**Original Notebook:** `mangrove_workflow.ipynb`
**Target Notebook:** `mangrove_workflow_marimo.py`

---

## Migration Strategy

### Automatic Conversion
Using marimo's built-in converter:
```bash
marimo convert mangrove_workflow.ipynb -o mangrove_workflow_marimo.py
```

### Post-Conversion Refactoring

The automatic converter provides a starting point, but manual refactoring is required for:

1. **Global Variable Elimination**
   - Replace module-level globals with cell returns
   - Use functional data flow

2. **Widget Migration**
   - `ipywidgets` → `marimo.ui` equivalents
   - Callback pattern → reactive pattern

3. **Display Pattern Updates**
   - Remove `IPython.display.display()`
   - Use cell returns and `mo.vstack/hstack`

4. **Expensive Operation Gating**
   - Add `mo.ui.run_button()` for data loading
   - Use `mo.stop()` to prevent auto-execution

---

## Conversion Checklist

### Phase 1: Setup ✅

- [x] Create feature branch: `feature/marimo-notebook`
- [x] Install marimo: `pip install "marimo[sql]"`
- [x] Download Claude Code prompt
- [x] Create design documentation
- [x] Create this migration log

### Phase 2: Initial Conversion 🔄

- [ ] Run automatic converter
- [ ] Fix syntax errors
- [ ] Resolve variable redefinition conflicts
- [ ] Test basic execution

### Phase 3: Widget Refactoring

- [ ] Replace `widgets.Dropdown` → `mo.ui.dropdown()`
- [ ] Replace `widgets.IntSlider` → `mo.ui.slider()`
- [ ] Replace `widgets.Button` → `mo.ui.run_button()`
- [ ] Remove callback functions
- [ ] Implement reactive dependencies

### Phase 4: Data Flow Refactoring

- [ ] Eliminate global variables
- [ ] Define cell return values
- [ ] Map dependency chains
- [ ] Test reactive updates

### Phase 5: Visualization Enhancement

- [ ] Convert static Plotly → `mo.ui.plotly()`
- [ ] Add interactive selections
- [ ] Implement linked visualizations
- [ ] Add threshold tuning sliders

### Phase 6: Validation

- [ ] Compare CSV outputs with Jupyter version
- [ ] Test all reactive chains
- [ ] Verify caching works
- [ ] Run as script: `python mangrove_workflow_marimo.py`
- [ ] Test as web app: `marimo run mangrove_workflow_marimo.py`

### Phase 7: Documentation

- [ ] Create user guide (MARIMO_USAGE.md)
- [ ] Update README.md
- [ ] Add screenshots
- [ ] Document new features

---

## Detailed Conversion Notes

### Cell-by-Cell Mapping

#### Cell 0: Title (Markdown)
- **Original:** Markdown cell
- **marimo:** `mo.md()` call
- **Status:** Pending

#### Cell 1: Imports
- **Original:** Standard imports + ipywidgets
- **marimo:** Add `import marimo as mo`, remove ipywidgets
- **Status:** Pending

#### Cell 2: Markdown - Configuration
- **Original:** Markdown cell
- **marimo:** `mo.md()` call
- **Status:** Pending

#### Cell 3: Study Sites Dictionary
- **Original:** Define STUDY_SITES
- **marimo:** Same (constants are fine)
- **Status:** Pending

#### Cell 4: Global Variables ⚠️
- **Original:**
  ```python
  selected_site = None
  selected_bounds = None
  # ... etc
  ```
- **marimo:** DELETE - use cell returns instead
- **Status:** Pending

#### Cell 6: Study Area Selection Widget ⚠️
- **Original:** ipywidgets Dropdown + Button + callback
- **marimo:**
  ```python
  site_dropdown = mo.ui.dropdown(
      options=list(STUDY_SITES.keys()),
      value=list(STUDY_SITES.keys())[0],
      label="Study Site:"
  )
  ```
- **Status:** Pending

#### Cell 6 (continued): Map Visualization
- **Original:** Plotly Scattermap in callback
- **marimo:** New cell that depends on site_dropdown
  ```python
  # Separate cell
  selected_site = site_dropdown.value
  site_info = STUDY_SITES[selected_site]

  # Create map (auto-updates when dropdown changes)
  fig = create_study_area_map(site_info)
  mo.ui.plotly(fig)
  ```
- **Status:** Pending

#### Cell 8: Data Search Widget ⚠️
- **Original:** Sliders + Button + callback with download logic
- **marimo:**
  ```python
  # Cell 1: Controls
  cloud_cover = mo.ui.slider(0, 50, value=20, label="Max Cloud %")
  days_back = mo.ui.slider(30, 365, value=90, step=30, label="Days Back")
  load_button = mo.ui.run_button(label="🛰️ Search Sentinel-2")

  # Cell 2: Conditional execution
  mo.stop(not load_button.value)
  sentinel2_data = load_sentinel2_cached(
      site_info["bounds"],
      cloud_cover.value,
      days_back.value
  )
  ```
- **Status:** Pending

#### Cell 9: Diagnostics
- **Original:** Conditional print statements
- **marimo:** Same logic, but depends on sentinel2_data cell
- **Status:** Pending

#### Cell 11: Mangrove Detection ⚠️
- **Original:** Button + callback
- **marimo:**
  ```python
  # Cell 1: Button
  detect_button = mo.ui.run_button(label="🌿 Detect Mangroves")

  # Cell 2: Detection logic
  mo.stop(not detect_button.value or sentinel2_data is None)
  indices = calculate_indices(sentinel2_data)
  mangrove_mask = detect_mangroves(indices)
  ```
- **Status:** Pending

#### Cell 13: Biomass Estimation ⚠️
- **Original:** Button + callback
- **marimo:** Similar pattern to detection
- **Status:** Pending

#### Cell 15: Export
- **Original:** Conditional export
- **marimo:** Depends on biomass_data
- **Status:** Pending

---

## Breaking Changes

### 1. No Global Variables
- **Impact:** High
- **Effort:** Medium
- **Solution:** Refactor to use cell returns

### 2. No Callbacks
- **Impact:** High
- **Effort:** Medium
- **Solution:** Use reactive dependencies

### 3. Threading Removed
- **Impact:** Low
- **Effort:** Low
- **Solution:** Remove progress indicator threading

### 4. Display Pattern
- **Impact:** Medium
- **Effort:** Low
- **Solution:** Use cell returns and mo.vstack

---

## Testing Plan

### Unit Tests
- [ ] Test each function independently
- [ ] Verify calculations match Jupyter version
- [ ] Test caching logic

### Integration Tests
- [ ] Full workflow execution
- [ ] CSV output comparison
- [ ] Interactive widget behavior

### Performance Tests
- [ ] Measure load time with cache
- [ ] Measure load time without cache
- [ ] Test reactive update latency

---

## Known Issues

*To be populated during conversion*

---

## Lessons Learned

*To be populated during conversion*

---

## Next Steps

1. Run automatic converter
2. Fix syntax errors
3. Begin widget refactoring
4. Test iteratively with `marimo edit --watch`

---

## References

- Design Document: `docs/MARIMO_DESIGN.md`
- Original Notebook: `mangrove_workflow.ipynb`
- marimo Docs: https://docs.marimo.io/
