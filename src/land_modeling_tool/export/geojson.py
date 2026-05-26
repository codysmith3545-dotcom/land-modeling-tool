from __future__ import annotations

import json
from pathlib import Path

from land_modeling_tool.atlas.development_atlas import DevelopmentAtlas
from land_modeling_tool.models.types import InfrastructureNode, ParcelRecord


def build_geojson(
    parcels: list[ParcelRecord],
    nodes: list[InfrastructureNode],
    atlas: DevelopmentAtlas | None = None,
) -> dict:
    features = []

    for node in nodes:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [node.lon, node.lat]},
                "properties": {
                    "layer": "node",
                    "id": node.node_id,
                    "name": node.name,
                    "county": node.county,
                    "node_score": round(node.node_score, 3),
                    "node_type": node.node_type,
                },
            }
        )

    if atlas:
        for proj in atlas.projects:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [proj.lon, proj.lat]},
                    "properties": {
                        "layer": "historical_project",
                        "id": proj.project_id,
                        "name": proj.name,
                        "category": proj.category,
                        "county": proj.county,
                        "acreage": proj.total_acreage,
                    },
                }
            )

    for parcel in parcels:
        cat = getattr(parcel, "investment_category", None) or parcel.fit.best_category()[0]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [parcel.lon, parcel.lat]},
                "properties": {
                    "layer": "parcel",
                    "id": parcel.parcel_id,
                    "county": parcel.county,
                    "acreage": parcel.acreage,
                    "owner": parcel.owner,
                    "composite_score": round(parcel.composite_score, 3),
                    "buy_score": round(getattr(parcel, "buy_score", 0), 3),
                    "buy_action": getattr(parcel, "buy_action", "pass"),
                    "category": cat,
                    "serious_shortlist": parcel.serious_shortlist,
                    "hiddenness": parcel.acquisition.hiddenness.value,
                    "blockers": parcel.fatal.blockers,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def write_geojson(path: Path, geojson: dict) -> None:
    path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
