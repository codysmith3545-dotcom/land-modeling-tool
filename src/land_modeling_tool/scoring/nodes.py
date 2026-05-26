from __future__ import annotations

from land_modeling_tool.models.types import InfrastructureNode, ParcelRecord
from land_modeling_tool.scoring.gates import score_parcel


def rank_nodes(nodes: list[InfrastructureNode]) -> list[InfrastructureNode]:
    return sorted(nodes, key=lambda n: n.node_score, reverse=True)


def rank_parcels(parcels: list[ParcelRecord], nodes: list[InfrastructureNode]) -> list[ParcelRecord]:
    node_map = {n.node_id: n.node_score for n in nodes}
    scored: list[ParcelRecord] = []
    for parcel in parcels:
        node_score = node_map.get(parcel.node_id, 0.3)
        scored.append(score_parcel(parcel, node_score))
    return sorted(scored, key=lambda p: p.composite_score, reverse=True)


def top_shortlist(parcels: list[ParcelRecord], limit: int = 100) -> list[ParcelRecord]:
    serious = [p for p in parcels if p.serious_shortlist]
    fallback = [p for p in parcels if not p.serious_shortlist]
    ordered = serious + fallback
    return ordered[:limit]
