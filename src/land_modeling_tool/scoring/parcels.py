from __future__ import annotations

from land_modeling_tool.models.types import FitScores, ParcelRecord


def score_fit(parcel: ParcelRecord) -> FitScores:
    acreage = parcel.acreage
    power = parcel.power
    water = parcel.water

    data_center = _clamp(
        0.35 * _tier_score(acreage, 100, 300)
        + 0.30 * power.mw_100_300
        + 0.15 * power.redundancy_proxy
        + 0.10 * water.score
        + 0.10 * (1.0 if parcel.flu_aligned else 0.3)
    )
    power_industrial = _clamp(
        0.30 * _tier_score(acreage, 50, 300)
        + 0.35 * power.mw_10_50
        + 0.20 * (1.0 if parcel.zoning in {"industrial", "agricultural"} else 0.4)
        + 0.15 * water.score
    )
    logistics = _clamp(
        0.40 * _tier_score(acreage, 20, 200)
        + 0.30 * (1.0 if parcel.frontage_ft >= 500 else 0.4)
        + 0.20 * (1.0 if parcel.sewer_miles <= 2 else 0.3)
        + 0.10 * (1.0 if not parcel.industrial_park else 0.5)
    )
    manufacturing = _clamp(
        0.35 * _tier_score(acreage, 20, 500)
        + 0.25 * power.mw_10_50
        + 0.20 * water.score
        + 0.20 * (1.0 if parcel.zoning in {"industrial", "agricultural"} else 0.5)
    )
    residential = _clamp(
        0.35 * _tier_score(acreage, 5, 100)
        + 0.25 * (1.0 if parcel.sewer_miles <= 1 else 0.2)
        + 0.20 * (1.0 if parcel.flu_aligned else 0.3)
        + 0.20 * (1.0 if parcel.floodway_pct < 0.1 else 0.1)
    )
    energy = _clamp(
        0.40 * _tier_score(acreage, 40, 2000)
        + 0.30 * power.mw_10_50
        + 0.20 * (1.0 if parcel.wetland_pct < 0.2 else 0.2)
        + 0.10 * (1.0 if parcel.zoning == "agricultural" else 0.6)
    )
    return FitScores(
        data_center=data_center,
        power_heavy_industrial=power_industrial,
        logistics=logistics,
        manufacturing=manufacturing,
        residential_growth=residential,
        bess_solar_energy=energy,
    )


def score_power_readiness(parcel: ParcelRecord) -> None:
    p = parcel.power
    dist = p.substation_miles
    voltage = p.transmission_voltage_kv
    base = 0.0
    if dist <= 1:
        base += 0.35
    elif dist <= 3:
        base += 0.22
    elif dist <= 5:
        base += 0.10
    if voltage >= 345:
        base += 0.30
    elif voltage >= 138:
        base += 0.20
    elif voltage >= 69:
        base += 0.10
    base += 0.20 * p.redundancy_proxy
    if p.utility_territory:
        base += 0.05
    p.mw_10_50 = _clamp(base)
    p.mw_100_300 = _clamp(base * 0.75 if dist <= 3 and voltage >= 138 else base * 0.35)
    p.mw_500_plus = _clamp(base * 0.55 if dist <= 2 and voltage >= 345 else base * 0.15)


def score_water_fit(parcel: ParcelRecord) -> None:
    sewer = parcel.sewer_miles
    wwtp = parcel.water.wwtp_miles
    score = 0.0
    if sewer <= 0.5:
        score += 0.45
    elif sewer <= 2:
        score += 0.25
    elif sewer <= 5:
        score += 0.10
    if wwtp <= 3:
        score += 0.25
    elif wwtp <= 8:
        score += 0.10
    score += 0.20 * (1.0 - min(parcel.water.withdrawal_risk, 1.0))
    score += 0.10 * (1.0 - min(parcel.water.political_risk, 1.0))
    parcel.water.score = _clamp(score)
    parcel.water.sewer_miles = sewer


def entitlement_path_score(parcel: ParcelRecord) -> float:
    path = parcel.entitlement_path.value
    mapping = {
        "by_right": 1.0,
        "variance": 0.85,
        "special_exception": 0.75,
        "utility_extension": 0.70,
        "rezoning": 0.55,
        "pud": 0.50,
        "annexation": 0.45,
        "comp_plan_amendment": 0.35,
        "unknown": 0.40,
    }
    flu_bonus = 0.15 if parcel.flu_aligned else 0.0
    return _clamp(mapping.get(path, 0.4) + flu_bonus)


def _tier_score(acreage: float, minimum: float, ideal_max: float) -> float:
    if acreage < minimum:
        return max(0.0, acreage / minimum * 0.5)
    if acreage <= ideal_max:
        return 1.0
    return max(0.4, ideal_max / acreage)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
