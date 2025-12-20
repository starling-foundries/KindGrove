# Repository File Connections Diagram

This diagram shows how the files in the KindGrove repository are connected and used.

```mermaid
graph TB
    subgraph "User Entry Points"
        README[README.md<br/>Quick Start Guide]
        WIKI[OSPD_WIKI_ENTRY.md<br/>Complete Specification]
    end

    subgraph "Main Workflow"
        NB[mangrove_workflow.ipynb<br/>Interactive Notebook]
        REQ[requirements.txt<br/>Python Dependencies]
        TEST[test_notebook.py<br/>Pre-flight Check]
    end

    subgraph "Documentation"
        DEMO[DEMO_GUIDE.md<br/>Presentation Script]
        VAL[VALIDATION_COMPARISON.md<br/>Scientific Validation]
        CVI[MANGROVE_CVI_INTEGRATION.md<br/>Coastal Integration]
        FUTURE[FUTURE_DATA_SOURCES.md<br/>Expansion Roadmap]
        STATUS[SHAREABLE_STATUS.md<br/>Current Status]
    end

    subgraph "External Data Sources"
        STAC[AWS STAC Catalog<br/>element84]
        S2[Sentinel-2 L2A<br/>AWS Open Data]
    end

    subgraph "Outputs"
        CSV[CSV Summaries<br/>Biomass & Carbon Stats]
        TIFF[GeoTIFF Rasters<br/>Cached Data]
        VIZ[Plotly Visualizations<br/>Interactive Maps]
    end

    README --> NB
    README --> REQ
    README --> TEST
    WIKI --> NB
    WIKI --> DEMO
    WIKI --> VAL

    TEST --> REQ
    TEST --> |Validates| NB

    NB --> |Queries| STAC
    STAC --> |Returns scenes| NB
    NB --> |Downloads| S2
    S2 --> |COG files| NB

    NB --> CSV
    NB --> TIFF
    NB --> VIZ

    DEMO --> |Guides presentation of| NB
    VAL --> |Validates methods in| NB
    CVI --> |Integration scenario for| NB
    FUTURE --> |Expansion plan for| NB
    STATUS --> |Reports on| NB

    style NB fill:#4CAF50,color:#fff
    style README fill:#2196F3,color:#fff
    style WIKI fill:#2196F3,color:#fff
    style STAC fill:#FF9800,color:#fff
    style S2 fill:#FF9800,color:#fff
    style CSV fill:#9C27B0,color:#fff
    style TIFF fill:#9C27B0,color:#fff
    style VIZ fill:#9C27B0,color:#fff
```

## File Dependency Flow

### Setup Phase
```
User → README.md
     → requirements.txt → pip install
     → test_notebook.py → Validates all dependencies
```

### Execution Phase
```
User → mangrove_workflow.ipynb
     → Cell 1-4: Setup (imports, config, study sites, global vars)
     → Cell 6: Initialize study area
     → Cell 8: Query STAC → Download Sentinel-2
     → Cell 11: Calculate indices → Detect mangroves
     → Cell 13: Estimate biomass
     → Cell 15: Export results → CSV, GeoTIFF, Plotly
```

### Documentation Flow
```
WIKI_ENTRY.md → Complete technical specification
              → References all other docs

DEMO_GUIDE.md → Step-by-step presentation
              → Uses WIKI_ENTRY for details

VALIDATION_COMPARISON.md → Scientific credibility
                         → Supports claims in WIKI_ENTRY

MANGROVE_CVI_INTEGRATION.md → Integration scenario
                             → Extends WIKI_ENTRY vision

FUTURE_DATA_SOURCES.md → Expansion roadmap
                        → 10 NASA/ESA data sources

SHAREABLE_STATUS.md → Current progress report
                    → Honest transparency
```

## Data Flow Through Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant NB as Notebook
    participant STAC as AWS STAC Catalog
    participant COG as Sentinel-2 COGs
    participant FS as File System

    U->>NB: Select study area + date range
    NB->>STAC: Query (bbox, cloud_cover, dates)
    STAC-->>NB: List of matching scenes
    NB->>NB: Select best scene (lowest cloud)
    NB->>COG: Download Red, Green, NIR bands
    COG-->>NB: xarray DataArray (3, Y, X)
    NB->>NB: Calculate NDVI, NDWI, SAVI
    NB->>NB: Apply threshold classification
    NB->>NB: Estimate biomass (allometric)
    NB->>NB: Calculate carbon (IPCC)
    NB->>FS: Save CSV summary
    NB->>FS: Cache GeoTIFF rasters
    NB->>U: Display Plotly visualizations
```

## Key Connection Points

1. **requirements.txt** → Ensures all imports in `mangrove_workflow.ipynb` work
2. **test_notebook.py** → Validates `requirements.txt` before running notebook
3. **AWS STAC Catalog** → Provides scene metadata to notebook
4. **Sentinel-2 COGs** → Provides actual pixel data to notebook
5. **WIKI_ENTRY.md** → Master reference for all other documentation
6. **DEMO_GUIDE.md** → Translates WIKI technical details into presentation
7. **VALIDATION_COMPARISON.md** → Backs up scientific claims in WIKI
8. **FUTURE_DATA_SOURCES.md** → Extends WIKI vision with expansion roadmap
