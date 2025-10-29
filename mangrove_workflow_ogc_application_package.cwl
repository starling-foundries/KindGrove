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
        type: int
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
          - step_1/output_directory
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
          - output_directory

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
      InitialWorkDirRequirement:
        listing:
        - entryname: outputs/catalog.json
          entry: |-  
              {
                  "id": "catalog",
                  "stac_version": "1.0.0",
                  "links": [
                      {
                          "type": "application/geo+json",
                          "rel": "item",
                          "href": "myMockStacItem.json"
                      },
                      {
                          "type": "application/json",
                          "rel": "self",
                          "href": "catalog.json"
                      }
                  ],
                  "type": "Catalog",
                  "description": "Root catalog"
              }
        - entryname: outputs/myMockStacItem.json
          entry: |-
            {
              "stac_version": "1.0.0",
              "stac_extensions": [
                  "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
                  "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
                  "https://stac-extensions.github.io/view/v1.0.0/schema.json"
              ],
              "type": "Feature",
              "id": "myMockStacItem",
              "geometry": {
                  "type": "Polygon",
                  "coordinates": [
                      [
                          [
                              $( inputs.west ),
                              $( inputs.south )
                          ],
                          [
                              $( inputs.west ),
                              $( inputs.north )
                          ],
                          [
                              $( inputs.east ),
                              $( inputs.north )
                          ],
                          [
                              $( inputs.east ),
                              $( inputs.south )
                          ],
                          [
                              $( inputs.west ),
                              $( inputs.south )
                          ]
                      ]
                  ]
              },
              "properties": {
                  "created": "2020-09-05T06:12:56.899Z",
                  "sentinel:product_id": "S2B_MSIL2A_20191205T083229_N0213_R021_T36RTT_20191205T111147",
                  "sentinel:sequence": "0",
                  "view:off_nadir": 0,
                  "sentinel:valid_cloud_cover": true,
                  "platform": "sentinel-2b",
                  "sentinel:utm_zone": 36,
                  "proj:epsg": 4326,
                  "sentinel:grid_square": "TT",
                  "datetime": "2019-12-05T08:42:04Z",
                  "instruments": [
                      "msi"
                  ],
                  "constellation": "sentinel-2",
                  "eo:cloud_cover": 2.75,
                  "gsd": 10,
                  "sentinel:latitude_band": "R",
                  "data_coverage": 67.28,
                  "updated": "2020-09-05T06:12:56.899Z",
                  "sentinel:data_coverage": 67.28
              },
              "bbox": [
                  $( inputs.west ),
                  $( inputs.south ),
                  $( inputs.east ),
                  $( inputs.north )
              ],

              "assets": {
                  "biomass_summary": {
                      "type": "text/csv ",
                      "href": "biomass_summary.csv"
                  },
                  "carbon_summary": {
                      "type": "text/csv",
                      "href": "carbon_summary.csv"
                  },
                  "mangrove_mask": {
                      "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                      "href": "mangrove_mask.tif",
                      "roles": [
                          "data"
                      ],
                      "title": "Mangrove mask"
                  }
              },
              "links": []
            }


    hints:
      DockerRequirement:
        dockerPull: ghcr.io/geolabs/kindgrove/mangrove-cwl:v0.0.1-rc1
    inputs:
      cloud_cover_max:
        inputBinding:
          prefix: --cloud_cover_max
        type: int
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
      output_directory:
        type: Directory
        outputBinding:
          glob: outputs/.

$namespaces:
  s: https://schema.org/
cwlVersion: v1.0
s:softwareVersion: "0.0.1-rc1"

s:author:
  - class: s:Person
    s:name: Cameron Sajedi

s:codeRepository: "https://github.com/starling-foundries/KindGrove"
s:keywords:
  - OSPD
  - demo
  - mangrove
  - biomass

s:license: "https://raw.githubusercontent.com/starling-foundries/KindGrove/refs/heads/main/LICENSE"


schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf