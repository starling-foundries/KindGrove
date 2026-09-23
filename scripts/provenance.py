"""One run of the application package as a provenance chain, in the OSPD generic provenance
profile's shape (W3C PROV objects: Entity / Activity / Agent, flat, linked by id), with a
fingerprint on every entity that has ground.

    uv run python scripts/provenance.py outputs docs/examples/provenance.json

Entities: the Sentinel-2 scene the analysis used (fingerprint of its STAC footprint), the analysis
output item (fingerprint of its geometry, the valid-data footprint) and the mangrove mask
artifact (fingerprint of the extent it detected). Activities: the analysis and the fingerprint
step, typed with candidate terms for the OSPD 2026 process-type register. Agents: the
application package, the workflow engine, the organisation.

The fingerprint fields keep their STAC names so the same key means the same thing in a STAC item
and in a provenance record.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pystac

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stac-extension" / "python"))
import burin_core as bc  # noqa: E402
import pystac_fingerprint as fp  # noqa: E402

EARTH_SEARCH_ITEM = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{id}"
PACKAGE = "https://github.com/starling-foundries/KindGrove/blob/main/mangrove_workflow_ogc_application_package.cwl"
FIELDS = (fp.ROOT_PROP, fp.DGGRS_PROP, fp.ZONE_LEVEL_PROP, fp.ZONE_COUNT_PROP, fp.PROFILE_PROP)


def fields_of(props: dict) -> dict:
    return {k: props[k] for k in FIELDS if k in props}


def scene_entity(scene_id: str, zone_level: int, profile_name: str) -> dict | None:
    """The input scene, fingerprinted from its Earth Search footprint at the same level."""
    try:
        item = pystac.Item.from_file(EARTH_SEARCH_ITEM.format(id=scene_id))
    except Exception as e:  # noqa: BLE001 - offline: still emit the entity, without a fingerprint
        print(f"scene {scene_id} not fetched ({e}); emitted without fingerprint", file=sys.stderr)
        return {"id": EARTH_SEARCH_ITEM.format(id=scene_id), "provType": "prov:Entity", "name": f"Sentinel-2 L2A scene {scene_id}",
                "wasAttributedTo": "https://registry.opendata.aws/sentinel-2-l2a-cogs/"}
    _, _, profile = fp.profile_for(profile_name)
    tree = bc.Tree.from_geojson(item.geometry, zone_level, profile)
    e = {"id": EARTH_SEARCH_ITEM.format(id=scene_id), "provType": "prov:Entity", "name": f"Sentinel-2 L2A scene {scene_id}",
         "generatedAtTime": item.datetime.isoformat().replace("+00:00", "Z") if item.datetime else None,
         "wasAttributedTo": "https://registry.opendata.aws/sentinel-2-l2a-cogs/",
         "eo:cloud_cover": item.properties.get("eo:cloud_cover")}
    ext = fp.FingerprintExtension.ext(item, add_if_missing=True)
    ext.apply(tree, profile_name)
    e.update(fields_of(item.properties))
    return e


def main(out_dir: Path, target: Path) -> None:
    catalog = pystac.read_file(str(out_dir / "catalog.json"))
    items = list(catalog.get_all_items())
    if not items:
        sys.exit("no items in the catalog")
    item = items[-1]
    ext = fp.FingerprintExtension.ext(item)
    if ext.root is None:
        sys.exit("the item carries no fingerprint; run the package first")
    profile_name, _, _ = ext.burin_profile()
    props = item.properties
    item_uri = f"urn:kindgrove:item:{item.id}"
    mask_key = next((k for k, a in item.assets.items() if "mask" in k and fp.ROOT_PROP in a.extra_fields), None)
    when = item.datetime or datetime.now(timezone.utc)
    t_end = when.isoformat().replace("+00:00", "Z")

    scene = scene_entity(props["scene_id"], ext.zone_level, profile_name)
    analysis = {
        "id": "urn:kindgrove:activity:mangrove-biomass-analysis:" + item.id,
        "provType": "prov:Activity",
        "name": "Mangrove biomass estimation",
        "processType": [  # candidate terms for the OSPD 2026 process-type register
            "spectral-index-computation",  # NDVI from red and NIR
            "classification",              # mangrove = 0.4 < NDVI < 0.95
            "regression-model-application",  # biomass = 250.5 × NDVI − 75.2
            "aggregation",                 # area, biomass and carbon totals
        ],
        "endedAtTime": t_end,
        "used": [scene["id"]],
        "wasAssociatedWith": "urn:kindgrove:agent:application-package",
    }
    output = {
        "id": item_uri,
        "provType": "prov:Entity",
        "name": "Mangrove analysis output (STAC item)",
        "generatedAtTime": t_end,
        "wasGeneratedBy": analysis["id"],
        "wasDerivedFrom": [scene["id"]],
        "wasAttributedTo": "urn:kindgrove:agent:application-package",
        "mangrove_area_ha": props.get("mangrove_area_ha"),
        "biomass_tons": props.get("biomass_tons"),
        "carbon_tons": props.get("carbon_tons"),
        **fields_of(props),
    }
    records = [scene, analysis, output]
    if mask_key:
        a = item.assets[mask_key]
        records.append({
            "id": f"{item_uri}#{mask_key}",
            "provType": "prov:Entity",
            "name": "Mangrove detection mask",
            "mediaType": a.media_type,
            "wasGeneratedBy": analysis["id"],
            "wasDerivedFrom": [scene["id"]],
            "hadPrimarySource": item_uri,
            **fields_of(a.extra_fields),
        })
    fingerprinting = {
        "id": "urn:kindgrove:activity:fingerprint:" + item.id,
        "provType": "prov:Activity",
        "name": "Fingerprinting (STAC Fingerprint extension)",
        "processType": ["identification"],
        "used": [item_uri] + ([f"{item_uri}#{mask_key}"] if mask_key else []),
        "wasInformedBy": analysis["id"],
        "wasAssociatedWith": "urn:kindgrove:agent:stac-fingerprint",
    }
    records.append(fingerprinting)
    records += [
        {"id": "urn:kindgrove:agent:application-package", "provType": "prov:SoftwareAgent",
         "name": "KindGrove mangrove biomass OGC Application Package", "softwareVersion": "0.2.0", "url": PACKAGE,
         "actedOnBehalfOf": "urn:kindgrove:agent:starling-foundries"},
        {"id": "urn:kindgrove:agent:stac-fingerprint", "provType": "prov:SoftwareAgent",
         "name": "stac-fingerprint 0.3.0 (burin-core)", "url": "https://github.com/starling-foundries/burin-core",
         "actedOnBehalfOf": "urn:kindgrove:agent:starling-foundries"},
        {"id": "urn:kindgrove:agent:starling-foundries", "provType": "prov:Organization", "name": "Starling Foundries"},
    ]
    records = [{k: v for k, v in r.items() if v is not None} for r in records]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records, indent=2) + "\n")
    print(f"{len(records)} provenance records -> {target}")
    for r in records:
        if fp.ROOT_PROP in r:
            print(f"  {r['name']}: {r[fp.ROOT_PROP][:16]}… ({r[fp.ZONE_COUNT_PROP]} zones)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs"), Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/examples/provenance.json"))
