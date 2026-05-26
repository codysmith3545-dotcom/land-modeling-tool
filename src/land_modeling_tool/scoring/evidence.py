from __future__ import annotations

from dataclasses import asdict, dataclass, field

from land_modeling_tool.models.types import InfrastructureNode, ParcelRecord


@dataclass
class EvidenceItem:
    source_id: str
    source_type: str
    claim: str
    confidence: float
    available_as_of: str | None = None


@dataclass
class EvidencePack:
    parcel_id: str
    thesis_summary: str
    items: list[EvidenceItem] = field(default_factory=list)
    signals_detected: list[str] = field(default_factory=list)
    diligence_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_evidence_pack(
    parcel: ParcelRecord,
    node: InfrastructureNode | None = None,
    signals: list[str] | None = None,
) -> EvidencePack:
    items: list[EvidenceItem] = []
    best_cat, fit = parcel.fit.best_category()

    if node:
        items.append(
            EvidenceItem(
                source_id=node.node_id,
                source_type="infrastructure_node",
                claim=f"Ranked node {node.name} (score {node.node_score:.2f})",
                confidence=0.85,
            )
        )
    if parcel.power.utility_territory:
        items.append(
            EvidenceItem(
                source_id="utility_territory",
                source_type="power",
                claim=(
                    f"{parcel.power.utility_territory} territory, "
                    f"{parcel.power.transmission_voltage_kv}kV, "
                    f"substation {parcel.power.substation_miles:.1f} mi"
                ),
                confidence=0.80,
            )
        )
    items.append(
        EvidenceItem(
            source_id="fit_model",
            source_type="scoring",
            claim=f"Best fit {best_cat} at {fit:.2f}; composite {parcel.composite_score:.2f}",
            confidence=0.70,
        )
    )
    items.append(
        EvidenceItem(
            source_id="acquisition",
            source_type="desk",
            claim=(
                f"Hiddenness {parcel.acquisition.hiddenness.value}, "
                f"basis ${parcel.acquisition.basis_per_acre:,.0f}/ac, "
                f"control {parcel.acquisition.control_method.value}"
            ),
            confidence=0.65,
        )
    )
    for note in parcel.evidence:
        items.append(
            EvidenceItem(
                source_id="scoring_engine",
                source_type="derived",
                claim=note,
                confidence=0.60,
            )
        )

    questions = [
        "Can utility confirm MW capacity and timeline at this POI?",
        "What is the sewer extension cost and political path?",
        "Are there easements, drains, or title defects blocking assemblage?",
        "Who else is circling this owner or corridor?",
    ]
    if parcel.fatal.blockers:
        questions.insert(0, f"Resolve blockers: {', '.join(parcel.fatal.blockers)}")

    return EvidencePack(
        parcel_id=parcel.parcel_id,
        thesis_summary=(
            f"Infrastructure-option on {parcel.acreage:.0f} ac in {parcel.county} "
            f"for {best_cat.replace('_', ' ')} before market prices scarcity."
        ),
        items=items,
        signals_detected=signals or [],
        diligence_questions=questions,
    )
