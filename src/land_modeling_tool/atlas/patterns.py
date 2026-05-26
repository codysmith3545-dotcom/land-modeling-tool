from __future__ import annotations

import math
from dataclasses import dataclass, field

from land_modeling_tool.models.types import ParcelRecord


@dataclass
class WinnerProfile:
    category: str
    sample_count: int
    means: dict[str, float] = field(default_factory=dict)
    stds: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "sample_count": self.sample_count,
            "means": self.means,
            "stds": self.stds,
        }


FEATURE_KEYS = [
    "acreage",
    "substation_miles",
    "transmission_voltage_kv",
    "sewer_miles",
    "mw_100_300",
    "wetland_pct",
    "floodway_pct",
]


def _feature_vector(parcel: ParcelRecord) -> dict[str, float]:
    return {
        "acreage": parcel.acreage,
        "substation_miles": parcel.power.substation_miles,
        "transmission_voltage_kv": parcel.power.transmission_voltage_kv,
        "sewer_miles": parcel.sewer_miles,
        "mw_100_300": parcel.power.mw_100_300,
        "wetland_pct": parcel.wetland_pct,
        "floodway_pct": parcel.floodway_pct,
    }


def build_winner_profiles(
    winner_parcels: list[ParcelRecord],
    category_by_parcel: dict[str, str],
) -> dict[str, WinnerProfile]:
    by_cat: dict[str, list[ParcelRecord]] = {}
    for parcel in winner_parcels:
        cat = category_by_parcel.get(parcel.parcel_id, "all")
        by_cat.setdefault(cat, []).append(parcel)
        by_cat.setdefault("all", []).append(parcel)

    profiles: dict[str, WinnerProfile] = {}
    for cat, group in by_cat.items():
        if not group:
            continue
        means: dict[str, float] = {}
        stds: dict[str, float] = {}
        for key in FEATURE_KEYS:
            vals = [_feature_vector(p)[key] for p in group]
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / max(len(vals), 1)
            means[key] = mean
            stds[key] = math.sqrt(var) if var > 0 else 1.0
        profiles[cat] = WinnerProfile(category=cat, sample_count=len(group), means=means, stds=stds)
    return profiles


def profile_match_score(parcel: ParcelRecord, profile: WinnerProfile | None) -> float:
    if profile is None or profile.sample_count == 0:
        return 0.5
    vec = _feature_vector(parcel)
    z_scores: list[float] = []
    for key in FEATURE_KEYS:
        mean = profile.means.get(key, vec[key])
        std = profile.stds.get(key, 1.0) or 1.0
        z = abs(vec[key] - mean) / std
        z_scores.append(z)
    avg_z = sum(z_scores) / len(z_scores)
    return max(0.0, min(1.0, 1.0 - avg_z / 4.0))
