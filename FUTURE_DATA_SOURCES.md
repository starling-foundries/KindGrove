# Future Data Sources for Mangrove OSPD
**Advanced Workflow Expansion Opportunities**

This document maps free, openly accessible satellite data from NASA, ESA, and other agencies to potential advanced workflows for the Mangrove Biomass OSPD.

---

## 1. NASA GEDI LiDAR Mission

### Data Characteristics
- **Product**: GEDI L2A/L2B (Canopy Height, Vertical Structure)
- **Resolution**: 25m footprints along orbital tracks
- **Coverage**: ±51.6° latitude (covers all tropical mangroves)
- **Temporal**: 2019-present (ongoing)
- **Access**: NASA Earthdata (free, requires simple login)

### Workflow Integration
**Use Case**: High-biomass stand calibration

**Problem Solved**: Optical NDVI saturates at ~50-70 Mg/ha. GEDI provides direct canopy height measurements up to 150+ Mg/ha.

**Implementation**:
```python
# Pseudo-workflow
gedi_heights = query_gedi(bbox, date_range)
coincident_s2 = match_sentinel2_to_gedi(gedi_heights)

# Train local allometric model
biomass_model = fit_model(
    predictors=['ndvi', 'ndwi', 'gedi_height'],
    target=gedi_heights.biomass
)

# Apply to full Sentinel-2 coverage
biomass_map = biomass_model.predict(sentinel2_data)
```

**Value Proposition**: Reduces uncertainty from ±30% to ±15% for high-biomass stands. Critical for carbon credit verification.

---

## 2. ESA Sentinel-1 SAR

### Data Characteristics
- **Product**: Sentinel-1 GRD (Ground Range Detected), C-band SAR
- **Resolution**: 10m (IW mode)
- **Coverage**: Global, 6-12 day revisit
- **Temporal**: 2014-present
- **Access**: Copernicus Open Access Hub / AWS

### Workflow Integration
**Use Case**: All-weather monitoring and structure mapping

**Problem Solved**: Optical data fails during monsoon season (60-90% cloud cover in Myanmar). SAR penetrates clouds.

**Implementation**:
```python
# Multi-sensor fusion
s1_vv = load_sentinel1(bbox, 'VV')
s1_vh = load_sentinel1(bbox, 'VH')
s2_optical = load_sentinel2(bbox)

# Combine backscatter with optical indices
features = {
    'VV': s1_vv,
    'VH': s1_vh,
    'VV_VH_ratio': s1_vv / s1_vh,
    'NDVI': s2_optical.ndvi
}

biomass_rf = RandomForest().fit(features, field_biomass)
```

**Value Proposition**: Year-round monitoring capability. SAR backscatter correlates with woody biomass structure (R² = 0.65-0.75).

---

## 3. RADARSAT Constellation Mission (Canada)

### Data Characteristics
- **Product**: RCM SAR, C-band (same as S1 but higher res options)
- **Resolution**: 3m (spotlight mode), 5m (ultra-fine mode)
- **Coverage**: Global, including Arctic
- **Temporal**: 2019-present
- **Access**: Open Data Program for research (申請 required)

### Workflow Integration
**Use Case**: High-resolution mangrove structure and canopy gap detection

**Problem Solved**: Sentinel-1's 10m resolution can miss small-scale degradation and fragmentation patterns.

**Implementation**:
- Map individual tree crowns in mature stands
- Detect illegal logging gaps (5-10m clearings)
- Assess restoration site fine-scale heterogeneity
- Validate Sentinel-1/2 coarse products

**Value Proposition**: Showcases Canadian space infrastructure. High-res validation for operational monitoring systems.

---

## 4. Landsat 8/9 OLI (NASA/USGS)

### Data Characteristics
- **Product**: Landsat Collection 2 Level-2
- **Resolution**: 30m multispectral
- **Coverage**: Global, 16-day revisit
- **Temporal**: 1972-present (Landsat 1-9 archive)
- **Access**: USGS Earth Explorer / AWS

### Workflow Integration
**Use Case**: Long-term change detection and historical baseline

**Problem Solved**: Sentinel-2 only available since 2015. Landsat provides 50-year record.

**Implementation**:
```python
# Time series analysis
years = range(1990, 2025, 5)
biomass_timeseries = []

for year in years:
    imagery = load_landsat(bbox, year)
    biomass = estimate_biomass(imagery)
    biomass_timeseries.append(biomass)

# Detect regime shifts
change_points = detect_changes(biomass_timeseries)
```

**Value Proposition**:
- Quantify 2004 Indian Ocean tsunami impact on Myanmar mangroves
- Track Thor Heyerdahl restoration from pre-2015 baseline
- Climate change trend analysis (sea level rise effects)

---

## 5. NASA EMIT Imaging Spectrometer

### Data Characteristics
- **Product**: EMIT L2A Surface Reflectance (hyperspectral)
- **Resolution**: 60m, 285 spectral bands (380-2500 nm)
- **Coverage**: ±52° latitude (tropics/subtropics)
- **Temporal**: 2022-present (ISS mission)
- **Access**: NASA Earthdata / LP DAAC

### Workflow Integration
**Use Case**: Species-level classification and functional diversity

**Problem Solved**: Sentinel-2's 13 bands cannot distinguish mangrove species. EMIT's 285 bands enable spectral unmixing.

**Implementation**:
```python
# Spectral endmember analysis
emit_cube = load_emit(bbox)
endmembers = extract_endmembers(emit_cube, n_species=5)

# Map species composition
species_map = spectral_unmixing(
    emit_cube,
    endmembers=['Rhizophora', 'Avicennia', 'Bruguiera', ...]
)
```

**Value Proposition**:
- Different species have different carbon densities
- Restoration planning needs species-specific biomass models
- Biodiversity monitoring for ecosystem health

---

## 6. ESA Sentinel-3 OLCI

### Data Characteristics
- **Product**: Sentinel-3 OLCI (Ocean and Land Colour Instrument)
- **Resolution**: 300m, 21 spectral bands
- **Coverage**: Global, daily revisit
- **Temporal**: 2016-present
- **Access**: Copernicus Open Access Hub

### Workflow Integration
**Use Case**: Large-scale regional monitoring and early warning

**Problem Solved**: Sentinel-2's 10m resolution takes weeks to cover entire Ayeyarwady Delta. OLCI provides daily snapshots.

**Implementation**:
- Daily mangrove health index for entire Myanmar coast
- Rapid damage assessment after cyclones/typhoons
- Phenology monitoring (flowering, leaf flush)
- Integration with ocean color (sediment plumes, water quality)

**Value Proposition**: Operational early warning system. Detects anomalies triggering high-res Sentinel-2 tasking.

---

## 7. NASA MODIS (Terra/Aqua)

### Data Characteristics
- **Product**: MOD13Q1 (NDVI 16-day composite, 250m)
- **Resolution**: 250m
- **Coverage**: Global, twice-daily
- **Temporal**: 2000-present (20+ years)
- **Access**: NASA Earthdata / LPDAAC

### Workflow Integration
**Use Case**: Climate baseline and trend analysis

**Problem Solved**: Need 20+ year records to detect climate change signals vs natural variability.

**Implementation**:
```python
# Long-term trend analysis
modis_ndvi = load_modis('MOD13Q1', bbox, '2000-01-01', '2025-09-29')

# Decompose signal
trend, seasonal, residual = seasonal_decompose(modis_ndvi)

# Attribution
climate_vars = load_climate_data(bbox)  # temp, precip, sea level
attribution = regression(trend, climate_vars)
```

**Value Proposition**:
- Detect long-term degradation vs recovery trends
- Climate attribution (temperature, precipitation changes)
- Validate Sentinel-2 methods against established MODIS products

---

## 8. NASA SRTM / Copernicus DEM

### Data Characteristics
- **Product**: SRTM (30m), Copernicus GLO-30 (30m)
- **Resolution**: 30m elevation
- **Coverage**: Global (SRTM: ±60°, Copernicus: global)
- **Temporal**: Static (2000 SRTM, 2011-2015 Copernicus)
- **Access**: USGS Earth Explorer / Copernicus

### Workflow Integration
**Use Case**: Tidal inundation modeling and vulnerability assessment

**Problem Solved**: Mangrove carbon stocks at risk from sea level rise. Need elevation-based vulnerability maps.

**Implementation**:
```python
# Sea level rise scenario modeling
dem = load_dem(bbox)
current_sea_level = 0  # meters MSL
slr_scenarios = [0.5, 1.0, 1.5, 2.0]  # meters by 2100

for slr in slr_scenarios:
    inundation_mask = (dem < slr)
    at_risk_biomass = biomass_map[inundation_mask].sum()
    at_risk_carbon = at_risk_biomass * 0.47

    print(f"SLR {slr}m: {at_risk_carbon:.0f} Mg C at risk")
```

**Value Proposition**:
- Climate risk assessment for carbon credit projects
- Prioritize restoration sites by elevation (avoid doomed areas)
- Integration with CVI OSPD (elevation + wave exposure)

---

## 9. Planet Labs Dove Constellation (Commercial with Open Programs)

### Data Characteristics
- **Product**: PlanetScope (3m multispectral)
- **Resolution**: 3m, 4-band (RGB + NIR)
- **Coverage**: Global, daily
- **Temporal**: 2016-present
- **Access**: Education & Research Program (free for qualified users)

### Workflow Integration
**Use Case**: Rapid response and fine-scale validation

**Problem Solved**:
- Sentinel-2's 5-day revisit misses rapid events (storm damage, illegal logging)
- 10m resolution insufficient for small restoration plots

**Implementation**:
- Daily monitoring of active restoration sites
- Rapid damage assessment after cyclones (<24 hour response)
- Fine-scale validation of Sentinel-2 biomass estimates
- Individual tree crown detection in mature stands

**Value Proposition**: Bridge between free coarse data and expensive aerial surveys. Showcases public-private partnership model.

---

## 10. ICESat-2 (NASA)

### Data Characteristics
- **Product**: ATL08 (Land and Vegetation Height)
- **Resolution**: 100m segments along track
- **Coverage**: Global, 91-day repeat
- **Temporal**: 2018-present
- **Access**: NASA Earthdata / NSIDC

### Workflow Integration
**Use Case**: Independent biomass validation

**Problem Solved**: GEDI has limited coverage (shot density). ICESat-2 provides complementary height transects.

**Implementation**:
```python
# Dual-LiDAR fusion
gedi_points = query_gedi(bbox)
icesat2_transects = query_icesat2(bbox)

# Combine for better spatial coverage
lidar_heights = merge_lidar_sources(gedi_points, icesat2_transects)

# Validate Sentinel-2 biomass map
validation_results = validate(biomass_map, lidar_heights)
```

**Value Proposition**:
- Higher spatial sampling than GEDI alone
- Independent validation dataset (different sensor, different agency)
- Polar orbit provides global consistency

---

## Summary: Data Source Priority Matrix

| Data Source | Implementation Effort | Scientific Value | Showcase Value | Priority |
|-------------|----------------------|------------------|----------------|----------|
| **GEDI LiDAR** | Medium | **Very High** | High | **1** |
| **Sentinel-1 SAR** | Medium | **Very High** | Medium | **2** |
| **Landsat 8/9** | Low | High | Medium | **3** |
| **Copernicus DEM** | Low | High | High (CVI link) | **4** |
| **RADARSAT (Canada)** | High | Medium | **Very High** | **5** |
| **MODIS** | Low | Medium | Low | 6 |
| **EMIT Hyperspectral** | High | High | **Very High** | 7 |
| **Sentinel-3 OLCI** | Medium | Medium | Medium | 8 |
| **ICESat-2** | Medium | Medium | Low | 9 |
| **Planet Dove** | Low | Medium | Medium | 10 |

### Recommended Phased Approach

**Phase 1** (Immediate - OGC 2025):
- Get Sentinel-2 workflow working ✅
- Add DEM for sea level rise scenarios (quick win)

**Phase 2** (Post-OGC):
- Add GEDI for high-biomass calibration (high impact)
- Add Sentinel-1 for all-weather capability (operational value)

**Phase 3** (Advanced Demo):
- Landsat time series (climate trend analysis)
- RADARSAT high-res validation (Canadian showcase)

**Phase 4** (Research Frontier):
- EMIT species mapping (cutting edge)
- Multi-sensor machine learning fusion (GEDI + S1 + S2 + EMIT)

---

## OGC Standards Alignment

All proposed data sources support:
- **OGC WCS** (Web Coverage Service): Raster data delivery
- **OGC WMS** (Web Map Service): Visualization
- **STAC**: Data discovery (except RADARSAT, Planet - use proprietary APIs)
- **COG**: Cloud-optimized formats (Sentinel, Landsat on AWS)

This enables true interoperability for the OSPD vision.