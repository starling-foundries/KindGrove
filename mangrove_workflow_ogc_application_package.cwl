#!/usr/bin/env cwl-runner

$graph:

  - class: CommandLineTool
    id: parse_aoi
    baseCommand: echo
    arguments:
    - --
    requirements:
      InlineJavascriptRequirement: {}
      SchemaDefRequirement:
        types:
          - $import: https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml
      ResourceRequirement:
        coresMax: 1
        ramMax: 512

    hints:
      DockerRequirement:
        dockerPull: alpine:3.22.2

    inputs:
      aoi:
        type: https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml#BBox
        label: "Area of interest"
        doc: "Area of interest defined as a bounding box"
    outputs:
      west:
        type: float
        outputBinding:
          outputEval: $(inputs.aoi.bbox[0])
      south:
        type: float
        outputBinding:
          outputEval: $(inputs.aoi.bbox[1])
      east:
        type: float
        outputBinding:
          outputEval: $(inputs.aoi.bbox[2])
      north:
        type: float
        outputBinding:
          outputEval: $(inputs.aoi.bbox[3])
      output_dir:
        type: string
        outputBinding:
          outputEval: $("outputs")

  - class: CommandLineTool
    id: stac_fingerprint
    label: Fingerprints for the STAC output
    doc: |
      Writes the STAC Fingerprint extension into the catalog the analysis emits: for the item, the
      SHA-256 root of the compact rHEALPix zone list of its geometry (the valid-data footprint);
      for the mangrove mask asset, the root of the detected extent from its pixels; the zone lists
      as assets; the union on the catalog. OGC API - DGGS vocabulary and the OGC-registered
      rHEALPix DGGRS. Two runs that cover the same ground produce the same roots whatever the
      encoding. Items that cannot be fingerprinted pass through unchanged.
      See https://github.com/starling-foundries/burin-core and cwl/fingerprint.cwl.
    baseCommand: [python, /app/fingerprint.py]
    requirements:
      ResourceRequirement:
        coresMax: 1
        ramMax: 1024
    hints:
      DockerRequirement:
        dockerPull: ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster
    inputs:
      stac:
        type: Directory
        inputBinding:
          prefix: --stac
      zone_level:
        type: int
        default: 11
        inputBinding:
          prefix: --zone-level
      assets:
        type: string
        default: auto
        inputBinding:
          prefix: --assets
    arguments:
      - prefix: --out
        valueFrom: outputs
    outputs:
      result:
        type: Directory
        outputBinding:
          glob: outputs

  - class: Workflow
    id: mangrove-workflow
    label: Mangrove Biomass Workflow
    doc: |
      Workflow for Mangrove Biomass Analysis

      This workflow orchestrates the mangrove biomass estimation process using
      Sentinel-2 imagery. It wraps the mangrove_workflow.cwl tool to provide
      a reusable workflow for analyzing different study areas.
    requirements:
      StepInputExpressionRequirement: {}
      ScatterFeatureRequirement: {}
      SubworkflowFeatureRequirement: {}
      InlineJavascriptRequirement: {}
      SchemaDefRequirement:
        types:
          - $import: https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml
    inputs:
      cloud_cover_max:
        label: Maximum Cloud Cover
        doc: Maximum acceptable cloud cover percentage (0-100)
        type: float
      days_back:
        label: Days Back
        doc: Number of days to search backwards from the current date
        type: int
      aoi:
        label: Area of Interest
        doc: Area of interest as a bounding box
        type: https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml#BBox
      fingerprint_zone_level:
        label: Fingerprint zone level
        doc: DGGRS refinement level of the fingerprints written into the STAC output (11 is about 52 m zones)
        type: int
        default: 11
      fingerprint_assets:
        label: Fingerprint assets
        doc: "Which assets to fingerprint from their pixels: auto (mask assets), none, or asset keys"
        type: string
        default: auto

    outputs:
      stac:
        label: STAC output with fingerprints
        type: Directory
        outputSource:
          - step_2/result
    steps:
      parse_aoi:
        run: '#parse_aoi'
        in:
          aoi: aoi
        out:
          - west
          - south
          - east
          - north
          - output_dir
      step_1:
        in:
          cloud_cover_max: cloud_cover_max
          days_back: days_back
          south: parse_aoi/south
          west: parse_aoi/west
          east: parse_aoi/east
          north: parse_aoi/north
          output_dir: parse_aoi/output_dir
        run: '#mangrove_cli'
        out:
          - result
      step_2:
        in:
          stac: step_1/result
          zone_level: fingerprint_zone_level
          assets: fingerprint_assets
        run: '#stac_fingerprint'
        out:
          - result

  # The content below defines the mangrove_cli CommandLineTool
  # It results from the mangrove_workflow_for_cwl.cwl jupyter
  # notebook conversion using the ipython2cwl tool.
  - id: mangrove_cli
    arguments:
    - --
    baseCommand: /app/cwl/bin/mangrove_workflow_for_cwl
    class: CommandLineTool
    requirements:
      InlineJavascriptRequirement: {}
      ResourceRequirement:
        coresMax: 1
        ramMax: 512

    hints:
      DockerRequirement:
        dockerPull: ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.2
    inputs:
      cloud_cover_max:
        inputBinding:
          prefix: --cloud_cover_max
        type: float
      days_back:
        inputBinding:
          prefix: --days_back
        type: int
      east:
        inputBinding:
          prefix: --east
        type: float
      north:
        inputBinding:
          prefix: --north
        type: float
      south:
        inputBinding:
          prefix: --south
        type: float
      west:
        inputBinding:
          prefix: --west
        type: float
      output_dir:
        inputBinding:
          prefix: --output_dir
        type: string
    outputs:
      result:
        type: Directory
        outputBinding:
          glob: outputs

$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: 0.2.0

s:author:
  - class: s:Person
    s:name: Cameron Sajedi

s:contributor:
  - class: s:Person
    s:name: Gérald Fenoy
    s:identifier: "https://orcid.org/0000-0002-9617-8641"

s:keywords:
  - OSPD
  - mangrove
  - biomass

s:codeRepository: "https://github.com/starling-foundries/KindGrove"
s:license: "https://github.com/starling-foundries/KindGrove?tab=MIT-1-ov-file#readme"

schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf
