"""pystac support for the STAC Fingerprint extension.

A fingerprint is the SHA-256 root of the compact list of DGGS zones (OGC API - DGGS terms) a
footprint covers at a refinement level. Vocabulary follows OGC API - DGGS Part 1 (OGC 21-038r1):
*zone*, *refinement level* (`zone-level` in the API), *compact zone list*, *DGGRS*. The zone
identifiers are the text identifiers of the OGC-registered rHEALPix DGGRS
(https://www.opengis.net/def/dggrs/OGC/1.0/rHEALPix): N,O,P,Q,R,S then digits 0-8.

    ext = FingerprintExtension.ext(item, add_if_missing=True)
    tree = ext.apply_geometry(zone_level=11)            # root of item.geometry, zone list attached as asset "fingerprint"
    FingerprintExtension.ext(item.assets["mask"]).apply(tree_of_mask)   # root of an asset's covered pixels
    FingerprintExtension.ext(collection, add_if_missing=True).apply(union_tree)
    FingerprintExtension.verify(item)                    # recompute from geometry and zone lists; raises on mismatch

Requires the burin-core wheel (module `burin_core`). Apache-2.0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generic, TypeVar, Union, cast

import burin_core as bc
import pystac
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension
from pystac.utils import make_absolute_href

__version__ = "0.1.0"

SCHEMA_URI = "https://starling-foundries.github.io/stac-fingerprint/v0.1.0/schema.json"
PREFIX = "fingerprint:"
ROOT_PROP = PREFIX + "root"
DGGRS_PROP = PREFIX + "dggrs"
ZONE_LEVEL_PROP = PREFIX + "zone_level"
ZONE_COUNT_PROP = PREFIX + "zone_count"
PROFILE_PROP = PREFIX + "profile"

ZONE_LIST_ROLE = "fingerprint"
ZONE_LIST_MEDIA_TYPE = "application/json"
ZONE_LIST_SCHEMA = "https://schemas.opengis.net/ogcapi/dggs/part1/1.0/openapi/schemas/dggs-core/dggs-zones.json"
DGGRS_DEFINITION_REL = "https://www.opengis.net/def/rel/ogc/1.0/dggrs-definition"

OGC_RHEALPIX_URI = "https://www.opengis.net/def/dggrs/OGC/1.0/rHEALPix"
# profile name -> (DGGRS URI, burin profile). burin-1 is rHEALPix with a 0° prime meridian, not an OGC-registered DGGRS.
PROFILES: dict[str, tuple[str, bc.Profile]] = {
    "ogc-rhealpix": (OGC_RHEALPIX_URI, bc.OGC_RHEALPIX),
    "burin-1": ("https://github.com/starling-foundries/burin-core/blob/main/SPEC.md#burin-1", bc.BURIN_1),
}
PROFILE_BY_ID = {p.id_hex(): (name, uri, p) for name, (uri, p) in PROFILES.items()}
DEFAULT_PROFILE = "ogc-rhealpix"

T = TypeVar("T", pystac.Item, pystac.Asset, pystac.Collection, pystac.Catalog)


class FingerprintError(ValueError):
    pass


# ---------------------------------------------------------------- zone lists (OGC API - DGGS JSON zone list encoding)

def zone_list(tree: bc.Tree, dggrs_uri: str) -> dict[str, Any]:
    """The tree as an OGC API - DGGS JSON zone list: compact (a parent stands for its nine
    children), text zone identifiers, total area, and the DGGRS definition link the standard requires."""
    zones = [bc.cid_to_suid(c) for c in tree.cells()]
    area = tree.leaf_count() * bc.cell_area_m2(tree.depth, tree.profile)
    return {
        "zones": zones,
        "returnedAreaMetersSquare": area,
        "links": [{"rel": DGGRS_DEFINITION_REL, "href": dggrs_uri, "type": "application/json"}],
    }


def tree_from_zone_list(doc: dict[str, Any], zone_level: int, profile: bc.Profile) -> bc.Tree:
    cids = [bc.suid_to_cid(z) for z in doc["zones"]]
    return bc.Tree.from_cells(cids, zone_level, profile)


def profile_for(name_or_id: str) -> tuple[str, str, bc.Profile]:
    """(name, dggrs_uri, profile) for a registered name or a profile identity."""
    if name_or_id in PROFILES:
        uri, p = PROFILES[name_or_id]
        return name_or_id, uri, p
    if name_or_id in PROFILE_BY_ID:
        return PROFILE_BY_ID[name_or_id]
    raise FingerprintError(f"unknown profile {name_or_id!r}")


# ---------------------------------------------------------------- the extension

class FingerprintExtension(Generic[T], PropertiesExtension, ExtensionManagementMixin[Union[pystac.Item, pystac.Collection, pystac.Catalog]]):
    name = "fingerprint"

    # -- fields
    @property
    def root(self) -> str | None:
        return self._get_property(ROOT_PROP, str)

    @property
    def dggrs(self) -> str | None:
        return self._get_property(DGGRS_PROP, str)

    @property
    def zone_level(self) -> int | None:
        return self._get_property(ZONE_LEVEL_PROP, int)

    @property
    def zone_count(self) -> int | None:
        return self._get_property(ZONE_COUNT_PROP, int)

    @property
    def profile(self) -> str | None:
        return self._get_property(PROFILE_PROP, str)

    def apply(self, tree: bc.Tree, profile_name: str = DEFAULT_PROFILE) -> None:
        """Write the fields of `tree` (its root, DGGRS, refinement level, zone count, profile)."""
        name, uri, p = profile_for(profile_name)
        if p != tree.profile:
            raise FingerprintError("tree profile does not match the named profile")
        self._set_property(ROOT_PROP, tree.root_hex)
        self._set_property(DGGRS_PROP, uri)
        self._set_property(ZONE_LEVEL_PROP, tree.depth)
        self._set_property(ZONE_COUNT_PROP, tree.leaf_count())
        self._set_property(PROFILE_PROP, p.id_hex())

    def burin_profile(self) -> tuple[str, str, bc.Profile]:
        if self.profile is None:
            raise FingerprintError("no fingerprint:profile")
        return profile_for(self.profile)

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> FingerprintExtension[T]:
        if isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(FingerprintExtension[T], ItemFingerprintExtension(obj))
        if isinstance(obj, pystac.Asset):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(FingerprintExtension[T], AssetFingerprintExtension(obj))
        if isinstance(obj, (pystac.Collection, pystac.Catalog)):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(FingerprintExtension[T], ContainerFingerprintExtension(obj))
        raise pystac.ExtensionTypeError(cls._ext_error_message(obj))

    # -- verification
    @classmethod
    def verify(cls, item: pystac.Item, deep_asset_footprints: dict[str, dict] | None = None) -> dict[str, str]:
        """Recompute every fingerprint on an item. The item root is recomputed from `geometry`
        (JSON only). Each zone-list asset is rebuilt and hashed, which proves the list is the
        one the root names. If `deep_asset_footprints` maps asset keys to GeoJSON footprints
        (say, polygonised from the rasters), those assets' roots are recomputed from them too.
        Returns {what: 'ok'}; raises FingerprintError on the first mismatch."""
        out: dict[str, str] = {}
        ext = cls.ext(item)
        if ext.root is None:
            raise FingerprintError(f"{item.id}: no {ROOT_PROP}")
        _, _, p = ext.burin_profile()
        tree = bc.Tree.from_geojson(item.geometry, ext.zone_level, p)
        if tree.root_hex != ext.root:
            raise FingerprintError(f"{item.id}: geometry root {tree.root_hex[:16]}… != declared {ext.root[:16]}…")
        if tree.leaf_count() != ext.zone_count:
            raise FingerprintError(f"{item.id}: zone_count {tree.leaf_count()} != declared {ext.zone_count}")
        out["geometry"] = "ok"
        for key, asset in item.assets.items():
            if ZONE_LIST_ROLE in (asset.roles or []):
                aext = cls.ext(asset)
                _, _, ap = aext.burin_profile()
                doc = json.loads(Path(make_absolute_href(asset.href, item.get_self_href())).read_text())
                rebuilt = tree_from_zone_list(doc, aext.zone_level, ap)
                if rebuilt.root_hex != aext.root:
                    raise FingerprintError(f"{item.id}/{key}: zone list hashes to {rebuilt.root_hex[:16]}…, declared {aext.root[:16]}…")
                target = key[: -len("_fingerprint")] if key.endswith("_fingerprint") else None
                if target and target in item.assets:
                    text = cls.ext(item.assets[target]).root
                    if text != aext.root:
                        raise FingerprintError(f"{item.id}/{target}: root {text} != its zone list's {aext.root}")
                elif key == "fingerprint" and aext.root != ext.root:
                    raise FingerprintError(f"{item.id}: zone list root != item root")
                out[key] = "ok"
        for key, fp in (deep_asset_footprints or {}).items():
            aext = cls.ext(item.assets[key])
            _, _, ap = aext.burin_profile()
            t = bc.Tree.from_geojson(fp, aext.zone_level, ap)
            if t.root_hex != aext.root:
                raise FingerprintError(f"{item.id}/{key}: recomputed {t.root_hex[:16]}… != declared {aext.root[:16]}…")
            out[f"{key} (recomputed)"] = "ok"
        return out


class ItemFingerprintExtension(FingerprintExtension[pystac.Item]):
    def __init__(self, item: pystac.Item):
        self.item = item
        self.properties = item.properties

    def apply_geometry(self, zone_level: int, profile_name: str = DEFAULT_PROFILE, attach_zone_list: bool = True) -> bc.Tree:
        """Fingerprint the item's `geometry`; optionally attach its zone list as asset `fingerprint`."""
        if not self.item.geometry:
            raise FingerprintError("item has no geometry")
        name, uri, p = profile_for(profile_name)
        tree = bc.Tree.from_geojson(self.item.geometry, zone_level, p)
        self.apply(tree, name)
        if attach_zone_list:
            attach_zone_list_asset(self.item, "fingerprint", tree, name, title="Zone list of the item geometry")
        return tree

    def apply_asset(self, key: str, footprint: dict, zone_level: int, profile_name: str = DEFAULT_PROFILE, attach_zone_list: bool = True) -> bc.Tree:
        """Fingerprint the ground an asset actually covers (a footprint polygonised from it) and
        write the fields on that asset; optionally attach the zone list as asset `<key>_fingerprint`."""
        name, uri, p = profile_for(profile_name)
        tree = bc.Tree.from_geojson(footprint, zone_level, p)
        FingerprintExtension.ext(self.item.assets[key]).apply(tree, name)
        if attach_zone_list:
            attach_zone_list_asset(self.item, f"{key}_fingerprint", tree, name, title=f"Zone list of the ground covered by {key}")
        return tree

    def __repr__(self) -> str:
        return f"<ItemFingerprintExtension Item id={self.item.id}>"


class AssetFingerprintExtension(FingerprintExtension[pystac.Asset]):
    def __init__(self, asset: pystac.Asset):
        self.asset_href = asset.href
        self.properties = asset.extra_fields
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        return f"<AssetFingerprintExtension Asset href={self.asset_href}>"


class ContainerFingerprintExtension(FingerprintExtension[Union[pystac.Collection, pystac.Catalog]]):
    """Collections and Catalogs carry the union of their items' fingerprints in their top-level fields."""

    def __init__(self, obj: pystac.Collection | pystac.Catalog):
        self.obj = obj
        self.properties = obj.extra_fields

    def __repr__(self) -> str:
        return f"<ContainerFingerprintExtension {type(self.obj).__name__} id={self.obj.id}>"


# ---------------------------------------------------------------- helpers

def attach_zone_list_asset(item: pystac.Item, key: str, tree: bc.Tree, profile_name: str, title: str) -> pystac.Asset:
    """Write the OGC zone list next to the item file and register it as an asset carrying the
    same fingerprint fields, so a reader can verify the root without any raster or geometry."""
    name, uri, p = profile_for(profile_name)
    self_href = item.get_self_href()
    if self_href is None:
        raise FingerprintError("item has no self href; save the catalog first or set one")
    filename = f"{key}.json" if key == "fingerprint" else f"{key}.json"
    path = Path(self_href).parent / filename
    path.write_text(json.dumps(zone_list(tree, uri), separators=(",", ":")) + "\n")
    asset = pystac.Asset(href=filename, media_type=ZONE_LIST_MEDIA_TYPE, roles=[ZONE_LIST_ROLE], title=title)
    item.add_asset(key, asset)
    FingerprintExtension.ext(asset).apply(tree, name)
    return asset


def union(trees: list[bc.Tree]) -> bc.Tree | None:
    if not trees:
        return None
    u = trees[0]
    for t in trees[1:]:
        u = u.union(t)
    return u
