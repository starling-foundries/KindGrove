#!/usr/bin/env cwl-runner

$graph:

  - class: Workflow
    id: mangrove-workflow
    label: myMockStacItem workflow
    doc: myMockStacItem workflow
    requirements:
      ScatterFeatureRequirement: {}
      SubworkflowFeatureRequirement: {}
      InlineJavascriptRequirement: {}
    inputs:
      cloud_cover_max:
        type: float
      days_back:
        type: int
      east:
        type: float
      north:
        type: float
      output_dir:
        type: string
      south:
        type: float
      west:
        type: float
    outputs:
      stac:
        type: Directory
        outputSource:
          - step_1/result
    steps:
      step_1:
        in:
          cloud_cover_max: cloud_cover_max
          days_back: days_back
          east: east
          north: north
          output_dir: output_dir
          south: south
          west: west
        run: '#mangrove_cli'
        out:
          - result

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
        dockerPull: ghcr.io/geolabs/kindgrove/mangrove-cwl:v0.0.1-rc6
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
      output_dir:
        inputBinding:
          prefix: --output_dir
        type: string
      south:
        inputBinding:
          prefix: --south
        type: float
      west:
        inputBinding:
          prefix: --west
        type: float
    outputs:
      result:
        type: Directory
        outputBinding:
          glob: outputs

$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: 0.0.1

s:author:
  - class: s:Person
    s:name: Cameron Sajedi

s:keywords:
  - OSPD
  - mangrove
  - biomass

s:codeRepository: "https://github.com/starling-foundries/KindGrove"
s:license: "https://github.com/starling-foundries/KindGrove?tab=MIT-1-ov-file#readme"

schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf
