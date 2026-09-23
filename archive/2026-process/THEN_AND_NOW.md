# Then and now: the 2025 mangrove workflow, what OSPD noticed, and what changed

*The mangrove workflow was delivered to the OGC Open Science Persistent Demonstrator in December
2025 with a findings report (`FINDINGS.md`) listing four lessons and seven recommendations. This
page walks each of those to what the 2026 revision does about it, with the numbers, and says
plainly what is still open.*

## The pain points, in the 2025 report's own words

| # | 2025 finding | 2025 fix | what it actually did |
|---|---|---|---|
| 1 | "Some scenes had <1% valid pixels within bbox" | coverage threshold of 1 %, try up to five scenes, lowest cloud first | still ranked by cloud alone: for the Sundarbans it chose 5 % and 3 % coverage scenes while zero-cloud, full-coverage scenes were in the same list |
| 2 | "*Area increased 3x!* was actually just different scene coverage" | scale-independent metrics (fraction, density, mean), by hand | correct in spirit; the comparable region was never computed, so metrics were still over different ground |
| 3 | "Large sites (Sundarbans) span multiple Sentinel-2 tiles" | smaller bboxes or accept variable coverage | accepted variable coverage |
| 4 | NDVI thresholds need context | reverted to 0.4 to 0.95 | fine; but a radiometric defect nobody saw was pushing NDVI past the cap on every scene after January 2022 |
| R1 | "Filter scenes by bbox overlap percentage before download" | not done | |
| R2 | "Always display coverage % in outputs" | coverage % in the table | |
| R3 | multi-scene selection | up to five tries | |
| L1 to L4 | HLS, mosaicking, quality flags, site calibration | not done | |

## What the 2026 revision does

**Recommendation 1, done from the catalog alone.** Every candidate scene's STAC footprint becomes
a fingerprint; one query against an index of them ranks candidates by how much of the study area
each covers, then by cloud. No pixel is read. Implemented in `scripts/prime_cache.py` and the
temporal-load cell of `mangrove_workflow_marimo.py`.

| site | 2025 selection, coverage of bbox per date | comparable region | 2026 selection | comparable region |
|---|---|---|---|---|
| Sundarbans | 5 %, 100 %, 100 %, 3 % | 3 % (25 km²) | 100 %, 100 %, 100 %, 100 % | 100 % (829 km²) |
| Can Gio | 71 %, 71 %, 59 %, 71 % | 29 % (367 km²) | 71 %, 71 %, 71 %, 71 % | 71 % (903 km²) |
| Thor Heyerdahl, Wunbaik | 100 % throughout | unchanged | unchanged | unchanged |

| Sundarbans, 2025 selection | Sundarbans, 2026 selection |
|---|---|
| ![2025](img/sundarbans_selection_2025.jpg) | ![2026](img/sundarbans_selection_2026.jpg) |

| Can Gio, 2025 selection | Can Gio, 2026 selection |
|---|---|
| ![2025](img/can_gio_biosphere_reserve_selection_2025.jpg) | ![2026](img/can_gio_biosphere_reserve_selection_2026.jpg) |

Each panel draws the four scene footprints in colour and their intersection, the comparable region,
in white. The bbox is the white outline.

**Lesson 2, computed rather than hand-built.** The comparable region is the intersection of the
scenes' valid-data roots; the mangrove share of that region is the number that means the same thing
on every date. It is in the demo (`fingerprints_marimo.py`, screen 5), in the flagship notebook
(Coverage Roots section), and in the CSV export (`footprint_root`, `mangrove_root` columns).

**Lesson 3, made visible.** Scenes from one tile share a footprint root to the byte. The Can Gio
bbox straddles tiles 48PXS and 48PYS; no single scene covers it. That is now a fact the catalog
states, and the union of two same-date roots is the mosaicking step the 2025 report listed as
long-term work.

**Lesson 4, sharpened.** The set difference of the 2017 and 2024 mangrove footprints on the fair
grid read as a near-total loss between two January scenes. The cause was a doubly applied
radiometric offset on every scene from processing baseline 04.00 onward (January 2022), which
pushed NDVI past the 0.95 cap and under-detected mangrove. Fixed in the notebook, the CLI, the CWL
notebook and the cache script. Every 2022-or-later number in the 2025 results was affected.

**Recommendation 2, in the item itself.** The application package's last step stamps every STAC
item with the fingerprint of its geometry (now the valid-data footprint, not the request box),
the mask asset with the fingerprint of the detected extent, both zone lists as assets
(`cwl/fingerprint.cwl`), and the collection with the union. The proposed extension is in `stac-extension/`.

## Stalls

Earth Search stalled a download for thirteen minutes at zero CPU during testing, before any
code of ours ran. Last year's loaders would have waited forever. Now every request, the STAC
search and each byte-range read behind stackstac, has a timeout and a retry budget; a scene that
cannot be fetched inside it is skipped for the next candidate; and a job with no fetchable
candidate fails with the reasons, so a platform sees a failed step rather than a hung one. The
same budget is in the CWL science step, the CLI, the cache script and the workflow notebook
(`earthsearch.py`), and a test drives GDAL at a non-routable address to prove it gives up in
seconds.

## A number without its ground

The sharpest version of the problem, and the one that is hard to make visceral in a talk: sometimes
a partial of the survey area is all you have, and you still want the value. The 2025 Sundarbans
table reported four plausible mangrove fractions. Two of them were computed on 5 % and 3 % of the
survey area, and nothing in the table could say so.

![where each number came from](img/sundarbans_where_each_number_came_from.jpg)

With a root, the ground is part of the number's identity, and the caveat stops being prose: five
fields travel with the value (root, profile, resolution, zone count), a reader recomputes the root
from the item's geometry to check it, and the sliver's root is a query key anyone can meet you on.
A partial survey is a fine datapoint. An unnamed partial is not a datapoint at all.

![three series](img/sundarbans_three_series.jpg)

Grey is the 2025 table: four numbers on four pieces of ground, not a series. Its dip in 2020 and
recovery by 2024 is not the forest; it is the ground switching from a dense sliver to the whole
area and back. Red is the honest 2025 series, each scene restricted to the ground all four saw
(25 km²): flat near 80 %. Green is the 2026 series on its own common ground (829 km²): near 65 %
with a real 2020 dip. Both are legitimate; they are different measurements because they are on
different ground, and the root is what says so.

The same idea generalises to observation itself. Nobody sees the whole survey area at once. Each
pass sees a piece, the piece is what its root names, and a best-available-pixel composite is a
union of named pieces whose provenance is a list of roots. Cloud masking is one more mask in the
same algebra. Can Gio, every scene ever selected, most recent first, each contributing the cells no
later scene saw:

![observation ledger](img/can_gio_biosphere_reserve_observation_ledger.jpg)

This is screen 1 of `fingerprints_marimo.py` (`uv run marimo run fingerprints_marimo.py`; static render
at `fingerprints_demo.html`), and screen 7 carries the observation ledger.

## What is still open

- Mosaicking (union of same-date roots into one footprint) is a set operation the core already
  has, but the pixel-level merge is not implemented.
- HLS, quality flags and site-specific calibration are untouched.
- Value roots, committing to biomass values rather than extent, wait on binding the resampling
  and quantization rule into the profile.
- The Docker images for the fingerprint step (`0.3.0`, `0.3.0-raster`) and the science step (`mangrove-cwl:v0.0.2`) are built locally, not yet published.
- Field prefix and package name are placeholders until the STAC community weighs in.

## How to reproduce every number on this page

```bash
uv sync
for s in "Sundarbans" "Can Gio Biosphere Reserve" "Thor Heyerdahl Climate Park" "Wunbaik Reserved Forest"; do
  uv run python scripts/prime_cache.py "$s"        # ranked selection; writes data_cache/temporal/<site>/selection.json
done
uv run marimo run fingerprints_marimo.py             # screens 5 and 6 carry the then-and-now panels and the diff
```

The 2025 selection is what the previous loader produced from the same catalog; it is preserved
locally under `data_cache/temporal_2025/` when this page was generated. It is not shipped
(`data_cache/` is ignored); regenerate it by ranking candidates by cloud cover alone:

```bash
uv run python scripts/prime_cache.py "Sundarbans" --rule cloud --out temporal_2025
```
