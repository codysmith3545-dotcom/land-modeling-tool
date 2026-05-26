from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from land_modeling_tool.config import DATA_DIR
from land_modeling_tool.models.types import (
    DevelopmentCategory,
    DevelopmentEvent,
    EntitlementPath,
    InfrastructureNode,
    ParcelRecord,
    PowerReadiness,
    WaterWastewaterFit,
)


def _sample_path(name: str) -> Path:
    return DATA_DIR / "sample" / name


def load_nodes() -> list[InfrastructureNode]:
    raw = json.loads(_sample_path("nodes.json").read_text(encoding="utf-8"))
    return [InfrastructureNode(**item) for item in raw]


def load_parcels() -> list[ParcelRecord]:
    raw = json.loads(_sample_path("parcels.json").read_text(encoding="utf-8"))
    parcels: list[ParcelRecord] = []
    for item in raw:
        item = dict(item)
        power = PowerReadiness(**item.pop("power", {}))
        water = WaterWastewaterFit(**item.pop("water", {}))
        if "entitlement_path" in item:
            item["entitlement_path"] = EntitlementPath(item["entitlement_path"])
        parcels.append(ParcelRecord(power=power, water=water, **item))
    return parcels


def load_projects() -> list[DevelopmentEvent]:
    raw = json.loads(_sample_path("projects.json").read_text(encoding="utf-8"))
    events: list[DevelopmentEvent] = []
    date_fields = (
        "land_acquisition_date",
        "first_public_signal_date",
        "rezoning_or_permit_date",
        "announcement_date",
        "construction_start_date",
        "operational_date",
    )
    for item in raw:
        item = dict(item)
        item["category"] = DevelopmentCategory(item["category"])
        for field in date_fields:
            if field in item and item[field]:
                item[field] = date.fromisoformat(item[field])
        events.append(DevelopmentEvent(**item))
    return events


def load_hard_negatives() -> list[str]:
    raw = json.loads(_sample_path("hard_negatives.json").read_text(encoding="utf-8"))
    return list(raw["parcel_ids"])
