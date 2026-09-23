# Changelog

## [v0.1.0] - 2026-09-19

Initial proposal, in OGC API - DGGS vocabulary: `fingerprint:root`, `fingerprint:dggrs`,
`fingerprint:zone_level`, `fingerprint:zone_count`, `fingerprint:profile`.

- Fields on Items, Assets, Collections and Catalogs: an Item's fingerprint is of its `geometry`;
  an Asset's is of the ground it actually covers.
- Zone lists travel with the object as assets with role `fingerprint`, in the OGC API - DGGS JSON
  zone list encoding, compact, with the `dggrs-definition` link, so a root is verifiable and
  computable without geometry or raster.
- Text zone identifiers are those of the OGC-registered rHEALPix DGGRS (checked against DGGAL).
- Complements [Projection](https://github.com/stac-extensions/projection) and `file:checksum`.
- `python/pystac_fingerprint.py`: a pystac extension class (`FingerprintExtension.ext(obj)`) with
  `apply_geometry`, `apply_asset`, `verify`, zone list encode/decode.
