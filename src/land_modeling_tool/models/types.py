from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class DevelopmentCategory(str, Enum):
    DATA_CENTER = "data_center"
    POWER_HEAVY_INDUSTRIAL = "power_heavy_industrial"
    LOGISTICS = "logistics"
    MANUFACTURING = "manufacturing"
    RESIDENTIAL_GROWTH = "residential_growth"
    BESS_SOLAR_ENERGY = "bess_solar_energy"


class EntitlementPath(str, Enum):
    BY_RIGHT = "by_right"
    VARIANCE = "variance"
    REZONING = "rezoning"
    PUD = "pud"
    ANNEXATION = "annexation"
    COMP_PLAN_AMENDMENT = "comp_plan_amendment"
    SPECIAL_EXCEPTION = "special_exception"
    UTILITY_EXTENSION = "utility_extension"
    UNKNOWN = "unknown"


class ControlMethod(str, Enum):
    OPTION = "option"
    ASSIGNABLE_PSA = "assignable_purchase_agreement"
    PHASED_ASSEMBLAGE = "phased_assemblage"
    ROFR = "rofr"
    GROUND_LEASE = "ground_lease"
    OUTRIGHT = "outright_purchase"


class Hiddenness(str, Enum):
    HIDDEN = "hidden"
    SEMI_OBVIOUS = "semi_obvious"
    PRICED = "priced"


class ConfidenceBand(str, Enum):
    HIGH_SCORE_HIGH_CONFIDENCE = "high_score_high_confidence"
    HIGH_SCORE_LOW_CONFIDENCE = "high_score_low_confidence"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class FitScores:
    data_center: float = 0.0
    power_heavy_industrial: float = 0.0
    logistics: float = 0.0
    manufacturing: float = 0.0
    residential_growth: float = 0.0
    bess_solar_energy: float = 0.0

    def best_category(self) -> tuple[str, float]:
        pairs = [
            (DevelopmentCategory.DATA_CENTER.value, self.data_center),
            (DevelopmentCategory.POWER_HEAVY_INDUSTRIAL.value, self.power_heavy_industrial),
            (DevelopmentCategory.LOGISTICS.value, self.logistics),
            (DevelopmentCategory.MANUFACTURING.value, self.manufacturing),
            (DevelopmentCategory.RESIDENTIAL_GROWTH.value, self.residential_growth),
            (DevelopmentCategory.BESS_SOLAR_ENERGY.value, self.bess_solar_energy),
        ]
        cat, score = max(pairs, key=lambda x: x[1])
        return cat, score

    def investment_category(self, priority_map: dict[str, float]) -> tuple[str, float]:
        """Best category weighted by investment priority (P1 > P2 > P3)."""
        pairs = [
            (DevelopmentCategory.DATA_CENTER.value, self.data_center),
            (DevelopmentCategory.POWER_HEAVY_INDUSTRIAL.value, self.power_heavy_industrial),
            (DevelopmentCategory.LOGISTICS.value, self.logistics),
            (DevelopmentCategory.MANUFACTURING.value, self.manufacturing),
            (DevelopmentCategory.RESIDENTIAL_GROWTH.value, self.residential_growth),
            (DevelopmentCategory.BESS_SOLAR_ENERGY.value, self.bess_solar_energy),
        ]
        weighted = [(cat, score * priority_map.get(cat, 1.0)) for cat, score in pairs]
        cat, _ = max(weighted, key=lambda x: x[1])
        raw = dict(pairs)[cat]
        return cat, raw


@dataclass
class PowerReadiness:
    mw_10_50: float = 0.0
    mw_100_300: float = 0.0
    mw_500_plus: float = 0.0
    utility_territory: str = ""
    transmission_voltage_kv: float = 0.0
    substation_miles: float = 999.0
    redundancy_proxy: float = 0.0


@dataclass
class WaterWastewaterFit:
    score: float = 0.0
    sewer_miles: float = 999.0
    wwtp_miles: float = 999.0
    withdrawal_risk: float = 0.0
    political_risk: float = 0.0


@dataclass
class GateResult:
    gate_id: str
    passed: bool
    notes: str = ""


@dataclass
class FatalFlawReport:
    score: float
    gates: list[GateResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def passed_all(self) -> bool:
        return all(g.passed for g in self.gates) and not self.blockers


@dataclass
class AcquisitionProfile:
    attractiveness: float = 0.0
    basis_per_acre: float = 0.0
    downside_value_per_acre: float = 0.0
    owner_count: int = 1
    control_method: ControlMethod = ControlMethod.OPTION
    hiddenness: Hiddenness = Hiddenness.HIDDEN
    mispricing_signal: float = 0.0
    exit_buyers: list[str] = field(default_factory=list)


@dataclass
class InfrastructureNode:
    node_id: str
    node_type: str
    name: str
    county: str
    lat: float
    lon: float
    scarcity: float = 0.0
    capacity_proxy: float = 0.0
    upgrade_momentum: float = 0.0
    political_receptivity: float = 0.0
    buyer_universe: float = 0.0
    time_advantage: float = 0.0

    @property
    def node_score(self) -> float:
        weights = {
            "scarcity": 0.22,
            "capacity_proxy": 0.22,
            "upgrade_momentum": 0.18,
            "political_receptivity": 0.14,
            "buyer_universe": 0.14,
            "time_advantage": 0.10,
        }
        return sum(getattr(self, k) * w for k, w in weights.items())


@dataclass
class ParcelRecord:
    parcel_id: str
    county: str
    acreage: float
    owner: str
    assessed_value: float
    lat: float
    lon: float
    node_id: str = ""
    zoning: str = "agricultural"
    flu_aligned: bool = False
    entitlement_path: EntitlementPath = EntitlementPath.UNKNOWN
    floodway_pct: float = 0.0
    wetland_pct: float = 0.0
    sewer_miles: float = 999.0
    frontage_ft: float = 0.0
    owner_count: int = 1
    ownership_years: float = 10.0
    listed: bool = False
    industrial_park: bool = False
    power: PowerReadiness = field(default_factory=PowerReadiness)
    water: WaterWastewaterFit = field(default_factory=WaterWastewaterFit)
    fit: FitScores = field(default_factory=FitScores)
    acquisition: AcquisitionProfile = field(default_factory=AcquisitionProfile)
    fatal: FatalFlawReport = field(default_factory=lambda: FatalFlawReport(score=0.0))
    confidence: ConfidenceBand = ConfidenceBand.MODERATE
    evidence: list[str] = field(default_factory=list)
    composite_score: float = 0.0
    serious_shortlist: bool = False


@dataclass
class DevelopmentEvent:
    project_id: str
    name: str
    category: DevelopmentCategory
    county: str
    parcel_ids: list[str]
    land_acquisition_date: date | None = None
    first_public_signal_date: date | None = None
    rezoning_or_permit_date: date | None = None
    announcement_date: date | None = None
    construction_start_date: date | None = None
    operational_date: date | None = None


@dataclass
class ParcelTimeSnapshot:
    parcel_id: str
    as_of: date
    features: dict[str, Any]
    label_horizon_months: int = 36
    developed_within_horizon: bool = False
    hard_negative: bool = False


@dataclass
class BacktestMetrics:
    precision_at_50: float
    recall_at_100: float
    lift_over_baseline: float
    winners_in_top_100: int
    total_winners: int
    false_positive_reasons: dict[str, int] = field(default_factory=dict)
