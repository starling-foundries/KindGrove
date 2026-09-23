# The OGC Application Package

`mangrove_workflow_ogc_application_package.cwl` is a CWL `$graph` with one Workflow
(`#mangrove-workflow`) and two CommandLineTools, in the shape of the OGC Best Practice for Earth
Observation Application Packages: a bounding-box input, Docker for each step, a self-contained
STAC catalog as the output directory.

```bash
cwltool --validate mangrove_workflow_ogc_application_package.cwl#mangrove-workflow
cwltool --no-match-user --no-read-only \
  mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input.yml
```

| input | default | |
|---|---|---|
| `aoi` | | bounding box (`ogc.yaml#BBox`) |
| `cloud_cover_max` | 20 | percent |
| `days_back` | 90 | search window before today |
| `fingerprint_zone_level` | 11 | DGGRS refinement level of the fingerprints (about 52 m zones) |
| `fingerprint_assets` | `auto` | which assets to fingerprint from their pixels: `auto` (mask assets), `none`, or asset keys |

Output `stac`: a directory with `catalog.json` and one item directory holding the mangrove mask
(GeoTIFF), two CSV summaries, the item JSON and two zone lists.

## Step 1: the analysis

Source: `mangrove_workflow_for_cwl.ipynb`, a self-contained notebook with ipython2cwl type
annotations, converted to the script that runs in
`ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.2`. The item geometry it writes is the
valid-data footprint of the analysis, not the request box. Earth Search access is bounded: every
request has a timeout and a retry budget, every scene fetch has a hard ten-minute deadline, a
scene that cannot be fetched is skipped for the next candidate, and a job with no fetchable
candidate reports the reasons and exits non-zero.

`cwl/Dockerfile.science` builds the image: the repo2docker base from 2025 with the current script
layered on top (`cwl/science/mangrove_workflow_for_cwl`, regenerated from the notebook).

```bash
docker build --platform linux/amd64 -f cwl/Dockerfile.science \
  -t ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.2 .
```

## Step 2: the fingerprints

`cwl/fingerprint.cwl` reads the STAC directory step 1 emits, copies it, and writes the STAC
Fingerprint extension into it: for the item, the fingerprint of its geometry; for the mask asset,
the fingerprint of its covered pixels; for the catalog, the union; each zone list attached as an
asset in the OGC API - DGGS zone list encoding. Asset hrefs are not touched, so the copy is still
a valid stage-out. An item that cannot be fingerprinted passes through unchanged with a warning.
It appends to any application package the same way, and run once at stage-out on a platform it
fingerprints every product of every job with no workflow touched.

| image | contents | size |
|---|---|---|
| `ghcr.io/starling-foundries/stac-fingerprint:0.3.0` | python, the burin-core wheel, pystac, the pystac extension module; geometry fingerprints | 220 MB |
| `ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster` | adds rasterio, for mask assets | 480 MB |

Both run under a 256 MB memory limit on the mangrove output; the CWL asks for 1 GB.

```bash
# the step on its own, against a STAC directory (a two-item sample is checked in)
cwltool --no-match-user --no-read-only cwl/fingerprint.cwl cwl/sample_input.yml

# verify a catalog from the JSON alone; --deep re-polygonises mask assets too
docker run --rm -v "$PWD/outputs:/data:ro" ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster \
  python /app/fingerprint.py --stac /data --check --deep

# tests: hrefs survive, zone lists are OGC and self-verifying, masks reproject, --check catches tampering
uv run pytest
```

If the image cannot be pulled, the package still works without fingerprints: remove `step_2` and
point the `stac` output back to `step_1/result`.

### Building and publishing the fingerprint images

```bash
# wheels: one per architecture into cwl/wheels/ (the Dockerfile picks the one matching uname -m)
cd ../burin-core && docker run --rm -v "$PWD":/io -w /io ghcr.io/pyo3/maturin build --release --out /io/dist-linux
docker run --rm --platform linux/amd64 -v "$PWD":/io -e CARGO_TARGET_DIR=/tmp/t -w /io ghcr.io/pyo3/maturin build --release --out /io/dist-linux-amd64
cp dist-linux*/burin_core-*manylinux*.whl ../KindGrove/cwl/wheels/

# images: two targets × two architectures, built from the repository root
cd ../KindGrove
for t in slim raster; do
  suffix=$([ $t = raster ] && echo -raster)
  docker buildx build --platform linux/arm64 -f cwl/Dockerfile --target $t -t ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-arm64 --load .
  docker buildx build --platform linux/amd64 -f cwl/Dockerfile --target $t -t ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-amd64 --load .
done

# publish (docker login ghcr.io with a token that can write packages), one multi-arch tag per target
for suffix in "" -raster; do
  docker push ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-arm64
  docker push ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-amd64
  docker buildx imagetools create -t ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix \
    ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-amd64 ghcr.io/starling-foundries/stac-fingerprint:0.3.0$suffix-arm64
done
# then pin the CWL by digest: docker buildx imagetools inspect ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster
#   dockerPull: ghcr.io/starling-foundries/stac-fingerprint@sha256:<manifest digest>
```

A new package on GHCR defaults to private; set it public so `dockerPull` works without a login.

## Provenance

`scripts/provenance.py outputs docs/examples/provenance.json` writes one run as a provenance
chain in the shape of the OSPD generic provenance profile (PROV entities, activities, agents),
with a fingerprint on every entity that has ground. See [FINGERPRINTS.md](FINGERPRINTS.md).

Library and specification: https://github.com/starling-foundries/burin-core (Apache-2.0).
pystac support: `stac-extension/python/pystac_fingerprint.py`.
