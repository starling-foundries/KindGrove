#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
id: stac-fingerprint
label: Fingerprints for a STAC catalog

doc: |
  Writes the STAC Fingerprint extension into a STAC catalog: for every item, the SHA-256 root of
  the compact DGGS zone list of its geometry at a refinement level (OGC API - DGGS vocabulary,
  OGC-registered rHEALPix DGGRS), the zone list itself as an asset, the same for mask assets
  (the detected extent, from their pixels), and the union on every collection and the catalog.
  Append it as the last step of an application package: input is the STAC directory the package
  already emits; output is a copy with the fields, asset hrefs untouched. An item that cannot be
  fingerprinted passes through unchanged with a warning. Image 0.3.0 handles geometries;
  0.3.0-raster also polygonises mask assets (--assets auto picks them by key or role).
  Verify a catalog with: python /app/fingerprint.py --stac <dir> --check [--deep]
  See https://github.com/starling-foundries/burin-core.

baseCommand: [python, /app/fingerprint.py]

requirements:
  DockerRequirement:
    dockerPull: ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster
  ResourceRequirement:
    coresMax: 1
    ramMax: 1024

inputs:
  stac:
    type: Directory
    doc: A self-contained STAC catalog directory (catalog.json or collection.json at its root)
    inputBinding:
      prefix: --stac
  zone_level:
    type: int
    default: 11
    doc: DGGRS refinement level of the fingerprints (11 is about 52 m zones)
    inputBinding:
      prefix: --zone-level
  profile:
    type: string
    default: ogc-rhealpix
    doc: ogc-rhealpix (the OGC API-DGGS Annex B rHEALPix DGGRS) or burin-1
    inputBinding:
      prefix: --profile
  assets:
    type: string
    default: auto
    doc: "auto: fingerprint mask assets from their pixels; none; or a comma-separated list of asset keys"
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

$namespaces:
  s: https://schema.org/
s:softwareVersion: 0.3.0
s:license: https://spdx.org/licenses/Apache-2.0
s:author:
  - class: s:Person
    s:name: Cameron Sajedi
