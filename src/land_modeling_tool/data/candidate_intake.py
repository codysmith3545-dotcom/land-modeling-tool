from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from land_modeling_tool.config import DATA_DIR
from land_modeling_tool.data.loaders import load_parcels
from land_modeling_tool.models.types import (
    AcquisitionProfile,
    EntitlementPath,
    FitScores,
    Hiddenness,
    ParcelRecord,
    PowerReadiness,
    WaterWastewaterFit,
)


CANDIDATES_DIR = DATA_DIR / "candidates"
SCHEMA_VERSION = "1.0"

# CSV columns supported for hand intake (subset maps to ParcelRecord)
CSV_FIELDS = [
    "parcel_id",
    "county",
    "acreage",
    "owner",
    "assessed_value",
    "lat",
    "lon",
    "node_id",
    "zoning",
    "flu_aligned",
    "entitlement_path",
    "floodway_pct",
    "wetland_pct",
    "sewer_miles",
    "frontage_ft",
    "owner_count",
    "ownership_years",
    "listed",
    "industrial_park",
    "utility_territory",
    "transmission_voltage_kv",
    "substation_miles",
    "basis_per_acre",
    "downside_value_per_acre",
    "hiddenness",
    "control_method",
    "notes",
    "source",
    "intake_date",
]


def candidates_dir() -> Path:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    return CANDIDATES_DIR


def _parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_float(value: str | float | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _row_to_parcel(row: dict[str, str]) -> ParcelRecord:
    parcel_id = row["parcel_id"].strip()
    acreage = _parse_float(row.get("acreage"), 0.0)
    assessed = _parse_float(row.get("assessed_value"), 0.0)
    basis = _parse_float(row.get("basis_per_acre"), 0.0)
    if basis <= 0 and acreage > 0:
        basis = assessed / acreage

    hiddenness_raw = (row.get("hiddenness") or "hidden").strip().lower()
    try:
        hiddenness = Hiddenness(hiddenness_raw)
    except ValueError:
        hiddenness = Hiddenness.HIDDEN

    entitlement_raw = (row.get("entitlement_path") or "unknown").strip().lower()
    try:
        entitlement = EntitlementPath(entitlement_raw)
    except ValueError:
        entitlement = EntitlementPath.UNKNOWN

    power = PowerReadiness(
        utility_territory=(row.get("utility_territory") or "").strip(),
        transmission_voltage_kv=_parse_float(row.get("transmission_voltage_kv")),
        substation_miles=_parse_float(row.get("substation_miles"), 999.0),
    )

    acquisition = AcquisitionProfile(
        basis_per_acre=basis,
        downside_value_per_acre=_parse_float(row.get("downside_value_per_acre"), basis * 0.85),
        owner_count=int(_parse_float(row.get("owner_count"), 1)),
        hiddenness=hiddenness,
    )

    evidence: list[str] = []
    if row.get("notes"):
        evidence.append(f"intake: {row['notes']}")
    if row.get("source"):
        evidence.append(f"source: {row['source']}")

    return ParcelRecord(
        parcel_id=parcel_id,
        county=row.get("county", "").strip(),
        acreage=acreage,
        owner=(row.get("owner") or "").strip(),
        assessed_value=assessed,
        lat=_parse_float(row.get("lat")),
        lon=_parse_float(row.get("lon")),
        node_id=(row.get("node_id") or "").strip(),
        zoning=(row.get("zoning") or "agricultural").strip(),
        flu_aligned=_parse_bool(row.get("flu_aligned")),
        entitlement_path=entitlement,
        floodway_pct=_parse_float(row.get("floodway_pct")),
        wetland_pct=_parse_float(row.get("wetland_pct")),
        sewer_miles=_parse_float(row.get("sewer_miles"), 999.0),
        frontage_ft=_parse_float(row.get("frontage_ft")),
        owner_count=int(_parse_float(row.get("owner_count"), 1)),
        ownership_years=_parse_float(row.get("ownership_years"), 10.0),
        listed=_parse_bool(row.get("listed")),
        industrial_park=_parse_bool(row.get("industrial_park")),
        power=power,
        water=WaterWastewaterFit(sewer_miles=_parse_float(row.get("sewer_miles"), 999.0)),
        fit=FitScores(),
        acquisition=acquisition,
        evidence=evidence,
    )


def load_candidates_csv(path: Path | None = None) -> list[ParcelRecord]:
    csv_path = path or candidates_dir() / "candidates.csv"
    if not csv_path.exists():
        return []

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_row_to_parcel(row) for row in reader if row.get("parcel_id")]


def load_candidates_json(path: Path | None = None) -> list[ParcelRecord]:
    json_path = path or candidates_dir() / "candidates.json"
    if not json_path.exists():
        return []

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("candidates", [])
    return [_row_to_parcel({k: str(v) if v is not None else "" for k, v in row.items()}) for row in rows]


def load_all_parcels(include_sample: bool = True) -> list[ParcelRecord]:
    """Merge candidate intake with sample parcels; candidates override by parcel_id."""
    by_id: dict[str, ParcelRecord] = {}
    if include_sample:
        for parcel in load_parcels():
            by_id[parcel.parcel_id] = parcel

    for parcel in load_candidates_csv() + load_candidates_json():
        by_id[parcel.parcel_id] = parcel

    return list(by_id.values())


def intake_schema() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "fields": CSV_FIELDS,
        "csv_path": str(candidates_dir() / "candidates.csv"),
        "json_path": str(candidates_dir() / "candidates.json"),
        "notes": "Hand-enter real parcels here. Re-run land-model run to score and queue.",
    }
