from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class TemporalFeature:
    parcel_id: str
    feature_key: str
    value: Any
    available_as_of: date
    source_id: str


@dataclass
class TemporalFeatureStore:
    """In-memory parcel-time feature store; swap for Postgres/Parquet in production."""

    features: list[TemporalFeature] = field(default_factory=list)

    def add(self, feature: TemporalFeature) -> None:
        self.features.append(feature)

    def as_of(self, parcel_id: str, as_of: date) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in self.features:
            if f.parcel_id != parcel_id or f.available_as_of > as_of:
                continue
            out[f.feature_key] = f.value
        return out

    def from_snapshots(self, snapshots: list) -> None:
        for snap in snapshots:
            for key, value in snap.features.items():
                self.add(
                    TemporalFeature(
                        parcel_id=snap.parcel_id,
                        feature_key=key,
                        value=value,
                        available_as_of=snap.as_of,
                        source_id="snapshot_import",
                    )
                )
