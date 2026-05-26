from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from land_modeling_tool.config import load_yaml
from land_modeling_tool.models.types import ParcelRecord


class ContractInstrumentType(str, Enum):
    NDA = "nda"
    LOI = "loi"
    OPTION = "option"
    ROFR = "rofr"
    ROFO = "rofo"
    PSA = "purchase_sale_agreement"
    LEASE_OPTION = "lease_option"
    EASEMENT = "easement"
    ACCESS_AGREEMENT = "access_agreement"
    EXCLUSIVITY = "exclusivity_agreement"


@dataclass
class LegalControlRecord:
    instrument_type: ContractInstrumentType
    binding: bool = True
    exclusive: bool = True
    assignment_allowed: bool = True
    recordable: bool = False
    contingencies: list[str] = field(default_factory=list)
    option_fee_per_acre: float = 0.0
    strike_price_per_acre: float = 0.0
    extension_fee_per_acre: float = 0.0
    diligence_deadline_days: int = 90
    title_objection_deadline_days: int = 30
    survey_deadline_days: int = 60
    closing_days: int = 180
    extension_windows: int = 1
    no_shop: bool = False
    seller_cooperation_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_type": self.instrument_type.value,
            "binding": self.binding,
            "exclusive": self.exclusive,
            "assignment_allowed": self.assignment_allowed,
            "recordable": self.recordable,
            "contingencies": self.contingencies,
            "option_fee_per_acre": round(self.option_fee_per_acre, 2),
            "strike_price_per_acre": round(self.strike_price_per_acre, 2),
            "extension_fee_per_acre": round(self.extension_fee_per_acre, 2),
            "diligence_deadline_days": self.diligence_deadline_days,
            "title_objection_deadline_days": self.title_objection_deadline_days,
            "survey_deadline_days": self.survey_deadline_days,
            "closing_days": self.closing_days,
            "extension_windows": self.extension_windows,
            "no_shop": self.no_shop,
            "seller_cooperation_required": self.seller_cooperation_required,
        }


@dataclass
class LegalControlScore:
    parcel_id: str
    title: float
    access: float
    seller_authority: float
    zoning: float
    environmental: float
    utility: float
    contract_control: float
    legal_control_score: float
    hard_blockers: list[str] = field(default_factory=list)
    soft_risks: list[str] = field(default_factory=list)
    contract: LegalControlRecord = field(default_factory=lambda: LegalControlRecord(instrument_type=ContractInstrumentType.OPTION))

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "title": round(self.title, 3),
            "access": round(self.access, 3),
            "seller_authority": round(self.seller_authority, 3),
            "zoning": round(self.zoning, 3),
            "environmental": round(self.environmental, 3),
            "utility": round(self.utility, 3),
            "contract_control": round(self.contract_control, 3),
            "legal_control_score": round(self.legal_control_score, 3),
            "hard_blockers": self.hard_blockers,
            "soft_risks": self.soft_risks,
            "contract": self.contract.to_dict(),
        }


def _desk_config() -> dict[str, Any]:
    return load_yaml("desk.yaml")


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def _infer_contract(parcel: ParcelRecord) -> LegalControlRecord:
    instrument = ContractInstrumentType.OPTION
    if parcel.listed:
        instrument = ContractInstrumentType.PSA
    elif parcel.owner_count >= 3:
        instrument = ContractInstrumentType.ROFO

    basis = parcel.acquisition.basis_per_acre
    option_fee = basis * 0.03 if basis > 0 else 0.0
    return LegalControlRecord(
        instrument_type=instrument,
        assignment_allowed=parcel.listed or parcel.owner_count > 1,
        contingencies=["title", "survey", "utility", "zoning"],
        option_fee_per_acre=option_fee,
        strike_price_per_acre=basis,
        extension_fee_per_acre=option_fee * 0.5,
        no_shop=parcel.acquisition.hiddenness.value == "hidden",
    )


def compute_legal_control(parcel: ParcelRecord) -> LegalControlScore:
    cfg = _desk_config().get("legal_control", {})
    hard_blocker_cutoff = float(cfg.get("hard_blocker_score", 0.35))

    title = _clamp(0.95 - max(0, parcel.owner_count - 1) * 0.12 - (0.12 if parcel.fatal.blockers else 0.0))
    access = _clamp(0.9 - (0.7 if parcel.frontage_ft <= 0 else 0.0) - (0.15 if parcel.frontage_ft < 100 and parcel.frontage_ft > 0 else 0.0))
    seller_authority = _clamp(0.9 - max(0, parcel.owner_count - 1) * 0.15 + min(parcel.ownership_years / 100, 0.1))
    zoning = _clamp(0.85 + (0.1 if parcel.flu_aligned else -0.25) + (-0.15 if parcel.zoning.lower() in {"ag", "agricultural", "a-1"} else 0.0))
    environmental = _clamp(0.9 - parcel.wetland_pct / 120 - parcel.floodway_pct / 80)
    utility_power = max(parcel.power.mw_10_50, parcel.power.mw_100_300, parcel.power.mw_500_plus)
    utility = _clamp(0.65 * utility_power + 0.35 * max(0.0, 1.0 - (parcel.sewer_miles / 10)))
    contract_control = _clamp(
        0.75
        + (0.1 if parcel.acquisition.hiddenness.value == "hidden" else -0.05)
        + (0.1 if parcel.listed else 0.0)
        - max(0, parcel.owner_count - 1) * 0.08
    )

    hard_blockers = list(parcel.fatal.blockers)
    soft_risks: list[str] = []

    if access <= hard_blocker_cutoff:
        hard_blockers.append("no_insurable_access")
    elif access < 0.6:
        soft_risks.append("access_uncertain")

    if title <= hard_blocker_cutoff:
        hard_blockers.append("title_control_uncertain")
    elif title < 0.6:
        soft_risks.append("multi_owner_title_complexity")

    if seller_authority <= hard_blocker_cutoff:
        hard_blockers.append("seller_authority_unproven")
    elif seller_authority < 0.55:
        soft_risks.append("seller_authority_needs_curative_work")

    if zoning <= hard_blocker_cutoff:
        hard_blockers.append("zoning_path_unlikely")
    elif zoning < 0.55:
        soft_risks.append("zoning_rezoning_risk")

    if environmental <= hard_blocker_cutoff:
        hard_blockers.append("environmental_constraints_material")
    elif environmental < 0.6:
        soft_risks.append("wetland_or_floodway_mitigation_risk")

    if utility <= hard_blocker_cutoff:
        hard_blockers.append("utility_service_unproven")
    elif utility < 0.6:
        soft_risks.append("utility_timeline_uncertain")

    if contract_control < 0.55:
        soft_risks.append("weak_contract_control_position")

    overall = _clamp((title + access + seller_authority + zoning + environmental + utility + contract_control) / 7)
    contract = _infer_contract(parcel)

    return LegalControlScore(
        parcel_id=parcel.parcel_id,
        title=title,
        access=access,
        seller_authority=seller_authority,
        zoning=zoning,
        environmental=environmental,
        utility=utility,
        contract_control=contract_control,
        legal_control_score=overall,
        hard_blockers=sorted(set(hard_blockers)),
        soft_risks=sorted(set(soft_risks)),
        contract=contract,
    )


def compute_all_legal_control(parcels: list[ParcelRecord]) -> list[LegalControlScore]:
    return [compute_legal_control(parcel) for parcel in parcels]
