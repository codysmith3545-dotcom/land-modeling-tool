from __future__ import annotations


def scenario_band_values(acreage: float, per_acre_value: float) -> tuple[float, float]:
    clamped_acreage = max(acreage, 0.0)
    clamped_per_acre = max(per_acre_value, 0.0)
    return clamped_acreage * clamped_per_acre, clamped_per_acre
