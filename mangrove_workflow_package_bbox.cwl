cwlVersion: v1.2
$graph:
- class: Workflow
  id: mangrove-biomass-workflow
  label: Mangrove Biomass Workflow
  
  doc: |
    Workflow for Mangrove Biomass Analysis
    
    This workflow orchestrates the mangrove biomass estimation process using
    Sentinel-2 imagery. It wraps the mangrove_workflow.cwl tool to provide
    a reusable workflow for analyzing different study areas.

  requirements:
    StepInputExpressionRequirement: {}
    InlineJavascriptRequirement: {}
    SchemaDefRequirement:
      types:
        - $import: https://raw.githubusercontent.com/eoap/schemas/0.2.0/ogc.yaml
  
  inputs:
    bounding_box:
      label: Bounding box
      type: https://raw.githubusercontent.com/eoap/schemas/0.2.0/ogc.yaml#BBox
      doc: Area of interest bounding box [west, south, east, north]
    cloud_cover_max:
      label: Cloud cover max
      type: int
      default: 20
      doc: Maximum acceptable cloud cover percentage (0-100)
    days_back:
      label: Days back
      type: int
      default: 90
      doc: Number of days to search backwards from current date

  steps:
    mangrove_analysis:
      label: Mangrove Analysis
      run: '#mangrove-analysis-cl'
      in:
        study_area_west: 
          source: bounding_box
          valueFrom: $(self.bbox[0])
        study_area_south: 
          source: bounding_box
          valueFrom: $(self.bbox[1])
        study_area_east: 
          source: bounding_box
          valueFrom: $(self.bbox[2])
        study_area_north: 
          source: bounding_box
          valueFrom: $(self.bbox[3])
        cloud_cover_max: cloud_cover_max
        days_back: days_back
      out:
        - mangrove_area_summary
        - biomass_summary
  
  outputs:
    mangrove_area_stats:
      label: Mangrove Area Statistics
      type: File
      outputSource: mangrove_analysis/mangrove_area_summary
      doc: CSV file containing mangrove area statistics
  
    biomass_stats:
      label: Biomass Statistics
      type: File
      outputSource: mangrove_analysis/biomass_summary
      doc: CSV file containing biomass and carbon stock totals

- class: CommandLineTool
  id: mangrove-analysis-cl
  
  doc: |
    Mangrove Biomass Estimation Workflow
  
    Estimates above-ground biomass and carbon stocks using Sentinel-2 satellite
    imagery from AWS STAC catalog. Implements threshold-based mangrove detection
    and allometric biomass model validated in Myanmar field studies (R² = 0.72).
  
    Workflow stages:
    1. Study area definition from bounding box
    2. STAC data discovery (Sentinel-2 L2A on AWS)
    3. Vegetation index calculation (NDVI, NDWI, SAVI)
    4. Mangrove detection via thresholds
    5. Biomass estimation (Biomass = 250.5 × NDVI - 75.2)
    6. Carbon accounting (IPCC-compliant)
  
  baseCommand: [python, /app/mangrove_workflow_cli.py]
  
  requirements:
    NetworkAccess:
      networkAccess: true  # Explicitly allow network access
    DockerRequirement:
      dockerPull: ghcr.io/starling-foundries/kindgrove:latest
  
  inputs:
    study_area_west:
      type: float
      doc: Western longitude bound of study area (decimal degrees)
      inputBinding:
        prefix: --west
  
    study_area_south:
      type: float
      doc: Southern latitude bound of study area (decimal degrees)
      inputBinding:
        prefix: --south
  
    study_area_east:
      type: float
      doc: Eastern longitude bound of study area (decimal degrees)
      inputBinding:
        prefix: --east
  
    study_area_north:
      type: float
      doc: Northern latitude bound of study area (decimal degrees)
      inputBinding:
        prefix: --north
  
    cloud_cover_max:
      type: int
      default: 20
      doc: Maximum acceptable cloud cover percentage (0-100)
      inputBinding:
        prefix: --cloud-cover
  
    days_back:
      type: int
      default: 90
      doc: Number of days to search backwards from current date
      inputBinding:
        prefix: --days-back
  
    output_directory:
      type: string
      default: "outputs"
      doc: Directory for output files
      inputBinding:
        prefix: --output-dir
  
  outputs:
    mangrove_area_summary:
      type: File
      doc: CSV file with detected mangrove area statistics
      outputBinding:
        glob: $(inputs.output_directory)/mangrove_area_summary.csv
  
    biomass_summary:
      type: File
      doc: CSV file with biomass and carbon stock totals
      outputBinding:
        glob: $(inputs.output_directory)/biomass_carbon_summary.csv
  
  hints:
    SoftwareRequirement:
      packages:
        - package: numpy
          version: ["1.24.0"]
        - package: pandas
          version: ["2.0.0"]
        - package: xarray
          version: ["2023.1.0"]
        - package: pystac-client
          version: ["0.7.0"]
        - package: stackstac
          version: ["0.5.0"]
        - package: rasterio
          version: ["1.3.0"]
        - package: geopandas
          version: ["0.14.0"]
  
  s:author:
    - class: s:Person
      s:name: Cameron Sajedi
      s:affiliation: Starling Foundries
  
  s:citation: |
    Myanmar Wunbaik Forest (2025): Biomass = 250.5 × NDVI - 75.2 (R² = 0.72)
    IPCC Guidelines (2013): Carbon fraction = 0.47
  
  s:license: https://spdx.org/licenses/MIT
  
  s:keywords:
    - mangrove
    - biomass
    - carbon
    - Sentinel-2
    - STAC
    - remote sensing

$namespaces:
  s: https://schema.org/
