from __future__ import annotations

from land_modeling_tool.config import signal_config
from land_modeling_tool.models.types import ParcelRecord


def load_signal_types() -> list[dict]:
    return signal_config().get("signal_types", [])


def detect_signals(parcel: ParcelRecord) -> list[str]:
    """Rule-based signal detection from parcel attributes (sample / stub for live pipelines)."""
    detected: list[str] = []
    if parcel.power.transmission_voltage_kv >= 345 and parcel.power.substation_miles <= 2:
        detected.append("substation_expansion_permit")
    if parcel.power.mw_100_300 >= 0.6 and parcel.acreage >= 100:
        detected.append("iurc_large_load_petition")
    if parcel.flu_aligned and parcel.entitlement_path.value in {"rezoning", "pud"}:
        detected.append("rezoning_pre_meeting")
    if parcel.sewer_miles <= 2 and parcel.water.score >= 0.5:
        detected.append("sewer_extension_study")
    if parcel.listed:
        detected.append("broker_off_market_chatter")
    return detected


def signal_boost(parcel: ParcelRecord, detected: list[str] | None = None) -> float:
    detected = detected if detected is not None else detect_signals(parcel)
    types = {s["id"]: s for s in load_signal_types()}
    boost = 0.0
    for sig_id in detected:
        spec = types.get(sig_id)
        if spec:
            boost += float(spec.get("boost", 0.0))
    max_boost = float(signal_config().get("scoring", {}).get("max_total_boost", 0.25))
    return min(boost, max_boost)
