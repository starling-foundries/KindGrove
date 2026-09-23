# Running KindGrove

## Prerequisites

- [uv](https://docs.astral.sh/uv/); Python 3.12 is pinned in `.python-version`
- a Rust toolchain (`cargo` on PATH, via [rustup](https://rustup.rs)): `uv sync` builds the
  `burin-core` wheel from source
- `burin-core` checked out next to this repository:
  `git clone https://github.com/starling-foundries/burin-core ../burin-core`
- network access to Earth Search (`earth-search.aws.element84.com`); `data_cache/` is not shipped
- for the application package only: Docker and `cwltool` (`uv tool install cwltool`)

## The notebooks

```bash
uv sync
uv run python scripts/prime_cache.py "Sundarbans"        # once per site: four scenes, ranked by footprint then cloud
uv run marimo run fingerprints_marimo.py                 # the story, thirteen screens
uv run marimo edit mangrove_workflow_marimo.py           # the workflow itself
```

Sites: Sundarbans, Can Gio Biosphere Reserve, Thor Heyerdahl Climate Park, Wunbaik Reserved
Forest. The story notebook opens on whichever sites are cached. To reproduce last year's scene
selection for the first screen: `uv run python scripts/prime_cache.py "Sundarbans" --rule cloud --out temporal_2025`.

Static renders: `docs/fingerprints_demo.html` (the notebook) and `docs/fingerprints_deck.pdf`
(one page per screen). Regenerate with
`uv run marimo export html fingerprints_marimo.py -o docs/fingerprints_demo.html` and
`uv run python scripts/build_deck.py scratchpad/deck`.

## The application package

```bash
cwltool --no-match-user --no-read-only \
  mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input.yml
```

Two steps: the analysis (`mangrove_workflow_for_cwl.ipynb`, converted with ipython2cwl, image
`ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.2`) and the fingerprint step
(`cwl/fingerprint.cwl`, image `ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster`). Output:
`outputs/`, a self-contained STAC catalog. Details, images and verification: [CWL_README.md](CWL_README.md).

## The command line

```bash
uv run python mangrove_workflow_cli.py --west 95.15 --south 15.9 --east 95.35 --north 16.1 \
  --cloud_cover 20 --days_back 90 --output_dir outputs
```

## Tests

```bash
uv run pytest            # the fingerprint step, the pystac module, the network budget
```

## Network

Earth Search can stall, and a process can wedge after the bytes arrive. Every request, the STAC
search and each byte-range read, has a timeout and a retry budget; every scene fetch has a hard
ten-minute deadline whatever is stuck; a scene that cannot be fetched is skipped for the next
candidate; a job with no fetchable candidate fails with the reasons (`earthsearch.py`).
