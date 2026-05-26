from __future__ import annotations

from dataclasses import dataclass, field

from land_modeling_tool.config import scoring_weights
from land_modeling_tool.models.types import ParcelRecord


@dataclass
class AssemblageCandidate:
    assemblage_id: str
    parcel_ids: list[str]
    county: str
    node_id: str
    owner: str
    total_acreage: float
    owner_count: int
    parcel_count: int
    composite_score: float = 0.0
    fit_peak: float = 0.0
    best_category: str = ""
    serious_shortlist: bool = False
    control_complexity: str = "low"
    notes: list[str] = field(default_factory=list)


def build_assemblages(parcels: list[ParcelRecord]) -> list[AssemblageCandidate]:
    cfg = scoring_weights().get("assemblage", {})
    min_parcels = int(cfg.get("min_parcels", 2))
    max_owners = int(cfg.get("max_owners", 12))
    same_node = bool(cfg.get("same_node_required", True))
    owner_match = bool(cfg.get("owner_match", True))

    groups: dict[tuple[str, str, str], list[ParcelRecord]] = {}
    for parcel in parcels:
        if parcel.owner_count > max_owners:
            continue
        key = (
            parcel.county,
            parcel.node_id if same_node else "*",
            _normalize_owner(parcel.owner) if owner_match else parcel.parcel_id,
        )
        groups.setdefault(key, []).append(parcel)

    candidates: list[AssemblageCandidate] = []
    for idx, ((county, node_id, owner_key), group) in enumerate(sorted(groups.items())):
        if len(group) < min_parcels:
            continue
        total_acreage = sum(p.acreage for p in group)
        owners = {p.owner for p in group}
        fit_peak = max(p.fit.best_category()[1] for p in group)
        best_cat = max(group, key=lambda p: p.composite_score).fit.best_category()[0]
        avg_composite = sum(p.composite_score for p in group) / len(group)
        bonus = min(0.08, 0.02 * (len(group) - 1))
        composite = min(1.0, avg_composite + bonus)
        serious = all(p.fatal.passed_all for p in group) and composite >= 0.55
        complexity = "low" if len(owners) == 1 else "medium" if len(owners) <= 4 else "high"

        candidates.append(
            AssemblageCandidate(
                assemblage_id=f"ASM-{county[:3].upper()}-{idx:03d}",
                parcel_ids=[p.parcel_id for p in group],
                county=county,
                node_id=node_id,
                owner=owner_key if owner_match else "mixed",
                total_acreage=total_acreage,
                owner_count=len(owners),
                parcel_count=len(group),
                composite_score=composite,
                fit_peak=fit_peak,
                best_category=best_cat,
                serious_shortlist=serious,
                control_complexity=complexity,
                notes=[
                    f"{len(group)} parcels, {total_acreage:.0f} total acres",
                    f"Control complexity: {complexity}",
                ],
            )
        )
    return sorted(candidates, key=lambda a: a.composite_score, reverse=True)


def _normalize_owner(owner: str) -> str:
    return owner.strip().lower().replace(",", "").replace(".", "")
