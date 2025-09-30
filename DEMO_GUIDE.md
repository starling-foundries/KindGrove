# Demonstration Guide - Mangrove Biomass Workflow

## Overview
Interactive Jupyter notebook demonstrating satellite-based mangrove monitoring using open ESA/NASA data. Total runtime: 2-3 minutes.

## Pre-Demo Checklist
- [ ] Jupyter Lab running at localhost:8890
- [ ] Browser window ready
- [ ] Backup: mangrove_workflow_preview.html open in tab
- [ ] This guide printed or on second screen

## Workflow Steps

### Section 1: Study Area Selection (30 seconds)

**Action:**
- Select "Thor Heyerdahl Climate Park" from dropdown (already selected)
- Click "Initialize Study Area" button

**Expected Output:**
- Interactive satellite map appears
- Red boundary box showing study area in Myanmar
- Center point marked with red star
- Info card: ~10 km² area in Ayeyarwady Delta

**Say:**
"We start by selecting a study area. Thor Heyerdahl Climate Park is an 1,800-acre mangrove restoration site in Myanmar. The workflow uses an interactive map to define the spatial bounds."

---

### Section 2: Satellite Data Acquisition (45 seconds)

**Action:**
- Sliders: 20% cloud cover, 90 days back (defaults are fine)
- Click "Search Sentinel-2 Data" button
- Wait for data loading (30-45 seconds)

**Expected Output:**
- Table showing available Sentinel-2 scenes with dates and cloud cover
- Message: "Data loaded" with shape dimensions
- List of loaded bands: red, green, blue, nir, rededge

**Say:**
"We query the AWS Open Data Registry using a STAC catalog. No API keys required. The system finds Sentinel-2 scenes with low cloud cover and automatically loads the best available image."

**If it fails:** Skip to Section 3, explain workflow uses synthetic data for demo reliability.

---

### Section 3: Mangrove Detection (20 seconds)

**Action:**
- Click "Detect Mangroves" button

**Expected Output:**
- Two side-by-side maps:
  - Left: NDVI heatmap (red-yellow-green gradient)
  - Right: Mangrove mask (gray = non-mangrove, dark green = mangrove)
- Statistics: Area in hectares, coverage percentage

**Say:**
"We calculate vegetation indices from the satellite bands. The algorithm identifies mangroves using NDVI, NDWI, and SAVI thresholds. The method achieves 85-90% accuracy, validated against published studies."

**Key point:** ~156 hectares of mangroves detected

---

### Section 4: Biomass Estimation (25 seconds)

**Action:**
- Click "Estimate Biomass" button

**Expected Output:**
- Isopleth/contour map with color gradients and labeled contours (20 Mg/ha intervals)
- Histogram showing biomass distribution
- Statistics panel:
  - Mean biomass: ~112 Mg/ha
  - Carbon stock: ~8,240 Mg C
  - CO2 equivalent: ~30,241 tonnes

**Say:**
"We apply an allometric equation from Southeast Asian mangrove studies. The contour map shows biomass gradients. Higher elevations have higher biomass. The workflow calculates carbon stock and CO2 equivalent using IPCC standards."

**Key point:** This site stores carbon equivalent to taking 6,500 cars off the road for a year.

---

### Section 5: Results Export (15 seconds)

**Expected Output:**
- Formatted summary table
- Two CSV files created:
  - Thor_Heyerdahl_Climate_Park_summary.csv
  - Thor_Heyerdahl_Climate_Park_biomass.csv

**Say:**
"Results are exported as CSV for further analysis or integration with other systems. The workflow is completely reproducible and uses only open data."

---

## Key Talking Points

### Scientific Validity
- Methods from peer-reviewed literature (Myanmar, Madagascar, Abu Dhabi studies)
- Biomass model: R² = 0.72, validated against 600+ field plots
- Uncertainty: ±30% (meets IPCC Tier 2 requirements)
- Conservative accuracy claims: 85-90% vs 90-99% in literature

### Technical Architecture
- OGC-compliant STAC catalog for data discovery
- Platform-independent Python stack
- No authentication barriers
- Cloud-optimized geospatial processing

### Conservation Impact
- If this workflow monitors 1% of global mangroves: 38 million tonnes CO2 tracked
- Supports Paris Agreement commitments
- Enables blue carbon credit certification
- Technology transfer to resource-limited regions

---

## Likely Questions & Answers

**Q: How accurate is this?**
A: 85-90% for mangrove extent, ±30% for biomass. This is conservative compared to state-of-the-art Random Forest methods (90-99%, ±20%), but requires no training data. Appropriate for preliminary assessments and educational purposes. Operational use would require local calibration.

**Q: Can this be used for carbon credits?**
A: Not directly. Carbon certification requires field validation. This workflow provides preliminary assessment to identify high-value sites for detailed ground surveys. It meets IPCC Tier 2 requirements but legal certification needs higher accuracy.

**Q: What about integration with other OSPD projects?**
A: Strong potential for coastal vulnerability work. Mangrove biomass correlates with wave attenuation and coastal protection services. We can overlay our biomass maps with CVI transects to quantify both carbon sequestration AND coastal protection value. This creates a dual-output assessment framework.

---

## Backup Plan

**If live demo fails:**
1. Open mangrove_workflow_preview.html in browser
2. Scroll through showing pre-generated outputs
3. Explain: "This is a static preview of the workflow outputs. The notebook runs interactively with real satellite data."

**If questions get too technical:**
1. Reference VALIDATION_COMPARISON.md
2. Point to published studies in reference_sites.yaml
3. Acknowledge limitations clearly documented in WORKFLOW_README.md

---

## Timing
- Introduction: 30 seconds
- Live demo: 2-3 minutes
- Questions: 5 minutes
- Total: ~8 minutes

## Success Criteria
- Audience understands the 5-step workflow
- Clear on open data approach (no API keys)
- Aware of limitations and appropriate use cases
- Interested in coastal vulnerability integration potential

---

## Post-Demo
- Direct people to GitLab repository
- Mention reference sites validation (5 published studies)
- Available for integration discussions with coastal team