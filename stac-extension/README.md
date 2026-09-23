# Fingerprint Extension Specification

- **Title:** Fingerprint
- **Identifier:** <https://starling-foundries.github.io/stac-fingerprint/v0.1.0/schema.json> (provisional)
- **Field Name Prefix:** `fingerprint`
- **Scope:** Item, Asset, Collection, Catalog
- **Extension Maturity Classification:** Proposal
- **Owner:** @cameronsajedi

A fingerprint is an identity for the **ground** a STAC object covers: the SHA-256 root of the
compact list of DGGS zones its footprint covers at a refinement level. The vocabulary is that of
[OGC API - Discrete Global Grid Systems Part 1](https://docs.ogc.org/is/21-038r1/21-038r1.html)
(OGC 21-038r1): *zone*, *refinement level*, *compact zone list*, *DGGRS*. The default DGGRS is
the OGC-registered rHEALPix (<https://www.opengis.net/def/dggrs/OGC/1.0/rHEALPix>), equal-area
and exactly hierarchical, and the zone identifiers are its text zone identifiers.

Two footprints that cover the same ground have the same fingerprint whatever their encoding,
tiling or vertex order; two catalogs compute it independently and agree to the byte; and
fingerprints compose: the union of a collection's items is a fingerprint, the intersection of two
scenes is a fingerprint, the difference between two dates is a fingerprint, each with an exact
area. The zone list a fingerprint names travels with the object, so a reader verifies it, and a
catalog computes with it, without the geometry or the raster it came from.

- Examples:
  - [Item example](examples/item.json): an output of the mangrove application package
  - [Collection example](examples/collection.json)
- [JSON Schema](json-schema/schema.json)
- [pystac support](python/pystac_fingerprint.py)
- [Changelog](CHANGELOG.md)

## Fields

The fields in the table below can be used in these parts of STAC documents:

- [x] Catalogs
- [x] Collections
- [x] Item Properties (incl. Summaries in Collections)
- [x] Assets (both Item and Collection assets)
- [ ] Links

| Field Name              | Type    | Description |
| ----------------------- | ------- | ----------- |
| fingerprint:root        | string  | **REQUIRED.** 64 lowercase hex characters: the SHA-256 root of the compact zone list at `fingerprint:zone_level`. On an Item: of the item `geometry`. On an Asset: of the ground that asset actually covers (its non-nodata, non-zero pixels for a mask). On a Collection or Catalog: the union of its items. |
| fingerprint:dggrs       | string  | **REQUIRED.** The URI of the DGGRS definition (OGC API - DGGS Annex B): `https://www.opengis.net/def/dggrs/OGC/1.0/rHEALPix`. Inheritable from the Collection. |
| fingerprint:zone_level  | integer | **REQUIRED.** The DGGRS refinement level of the zone list (`zone-level` in OGC API - DGGS), 0 to 15. Part of the identity: the same ground at two levels has two roots. Level 11 zones are about 52 m across. |
| fingerprint:zone_count  | integer | The number of zones at `fingerprint:zone_level` covered. Zones at a level are equal-area, so `zone_count` times the zone area is an exact area, and ratios between objects are fair. |
| fingerprint:profile     | string  | **REQUIRED.** 64 hex characters binding what the DGGRS leaves open and the root depends on: the hash function, the ellipsoid integers, the zone-inclusion rule. The registered value for the rHEALPix DGGRS above is `529e59bf3e91e8cbd9dc5190eb9733aef36e8ddc77587f1a9c19ca5e50885807` (`ogc-rhealpix`). Inheritable from the Collection. |

### Item vs Asset

An Item's fingerprint is of its `geometry` and is verifiable from the JSON alone. An Asset's
fingerprint is of the ground that asset covers, which for an analysis output is the detected
extent (a mangrove mask, a burn scar) rather than the scene. An analysis that reports a number
should fingerprint the asset the number was computed from; the Item's fingerprint says which
part of the world was looked at, the Asset's says what was found there.

### Zone list assets

The zone list a fingerprint names SHOULD travel with the object as an asset with role
`fingerprint`, in the OGC API - DGGS JSON zone list encoding
(`https://schemas.opengis.net/ogcapi/dggs/part1/1.0/openapi/schemas/dggs-core/dggs-zones.json`):
a `zones` array of text zone identifiers, compact (a parent stands for its nine children,
recursively), `returnedAreaMetersSquare`, and a link with `rel`
`https://www.opengis.net/def/rel/ogc/1.0/dggrs-definition` to the DGGRS. The asset carries the
same `fingerprint:*` fields as the object it describes, so a reader rebuilds the list at
`fingerprint:zone_level` and hashes it: if the hash equals `fingerprint:root`, the list is the one
the root names, and no geometry or raster is needed for anything a catalog does next.

Conventions: the Item's zone list is asset key `fingerprint`; an asset `X`'s zone list is asset key
`X_fingerprint`.

```json
"assets": {
  "mangrove_mask_tif": {
    "href": "./mangrove_mask.tif", "type": "image/tiff",
    "fingerprint:root": "…", "fingerprint:zone_level": 11, "fingerprint:zone_count": 739
  },
  "mangrove_mask_tif_fingerprint": {
    "href": "./mangrove_mask_tif_fingerprint.json", "type": "application/json", "roles": ["fingerprint"],
    "fingerprint:root": "…", "fingerprint:zone_level": 11, "fingerprint:zone_count": 739
  }
}
```

### The rule, in one paragraph

The zones of a footprint at refinement level L are the level-L zones whose **centre** (the
inverse projection of the planar zone centre) lies in the footprint's interior. The set is held
compact (nine full children become their parent, recursively) and hashed bottom-up with SHA-256
over domain-tagged nodes; a constant subtree hashes to a ladder value, so tiling does not matter.
`fingerprint:root` is that hash. The full rule, the numeric conventions and the conformance
fixtures are in the reference implementation,
[burin-core](https://github.com/starling-foundries/burin-core) (Apache-2.0, Rust with a Python
wheel), whose `SPEC.md` §7 maps every term here to OGC API - DGGS. The text zone identifiers were
checked against DGGAL, the OGC reference library, on 66 probes at levels 0 to 8, polar zones
included.

## What a catalog can do with the fields

- **Computed extent.** A Collection's `fingerprint:root` is the union of its Items', computed
  rather than declared, and its `fingerprint:zone_count` is its exact area in zones.
- **Fair overlap.** Given a query zone list, a server holding the items' zone lists answers, for
  every item, how much of the query it covers and how much of the item lies in the query, as exact
  fractions of equal-area zones. Proposed as a CQL2 function, `fingerprint_fraction(root)`.
- **Diffs.** Two zone lists yield lost, gained and stable zones and a transcript a verifier
  replays without either geometry.
- **Discovery by ground.** Roll zone lists up to a coarse level and count: a map of where the
  catalog's effort is, and same-ground, different-lineage matches.

## Relation to other extensions

- [Projection](https://github.com/stac-extensions/projection): `proj:*` describes an asset's
  native grid; `fingerprint:*` names the ground independent of any grid the data is stored on.
- `file:checksum` identifies bytes; a fingerprint identifies ground. Two files with different
  checksums (a COG and a Zarr store of the same mask) have one fingerprint.
- OGC API - DGGS: the zone list assets are that standard's zone list encoding, so a DGGS API can
  serve or consume them directly; the DGGRS URI is the standard's identifier.

## Contributing

All contributions are subject to the [STAC Specification Code of Conduct](https://github.com/radiantearth/stac-spec/blob/master/CODE_OF_CONDUCT.md).
The prefix, the field names and the registered profile list are the open questions for the STAC
community; the rule and the fixtures are settled by the reference implementation.
