# OGC Building Block Integration

KindGrove uses the OGC Bounding Box building block for spatial input.

## Bounding Box

**Building Block:** `ogc.geo.common.data_types.bounding_box`  
**Schema:** https://opengeospatial.github.io/bblocks/annotated-schemas/geo/common/data_types/bounding_box/schema.json  
**Status:** Stable (v1.0.1)

### Format

```json
[west, south, east, north]
```

Example: `[95.15, 15.9, 95.35, 16.1]` (Thor Heyerdahl Climate Park)

### Usage

```python
bbox = [95.15, 15.9, 95.35, 16.1]

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox,
)
```

No conversion needed. Same format works for STAC, CVI, Water Bodies, any OSPD workflow.
