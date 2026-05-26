from __future__ import annotations

from land_modeling_tool.models.types import ParcelRecord


def render_memo(parcel: ParcelRecord) -> str:
    best_cat, fit = parcel.fit.best_category()
    gates = "\n".join(
        f"- {g.gate_id}: {'PASS' if g.passed else 'FAIL'} — {g.notes}" for g in parcel.fatal.gates
    )
    evidence = "\n".join(f"- {e}" for e in parcel.evidence)
    blockers = ", ".join(parcel.fatal.blockers) or "none"
    exits = ", ".join(parcel.acquisition.exit_buyers)
    return f"""# Diligence Memo: {parcel.parcel_id}

## Summary
- County: {parcel.county}
- Acreage: {parcel.acreage:.1f}
- Owner: {parcel.owner}
- Best fit: {best_cat} ({fit:.2f})
- Composite score: {parcel.composite_score:.2f}
- Confidence: {parcel.confidence.value}
- Serious shortlist: {parcel.serious_shortlist}

## Investment Thesis
Infrastructure-option play on controllable land with strong {best_cat.replace('_', ' ')} fit before public pricing.

## Power Readiness
- 10-50 MW: {parcel.power.mw_10_50:.2f}
- 100-300 MW: {parcel.power.mw_100_300:.2f}
- 500+ MW: {parcel.power.mw_500_plus:.2f}
- Utility territory: {parcel.power.utility_territory or 'unknown'}
- Substation distance (mi): {parcel.power.substation_miles:.1f}

## Water / Wastewater
- Score: {parcel.water.score:.2f}
- Sewer distance (mi): {parcel.water.sewer_miles:.1f}

## Acquisition
- Basis ($/acre): {parcel.acquisition.basis_per_acre:,.0f}
- Mispricing signal: {parcel.acquisition.mispricing_signal:.2f}
- Hiddenness: {parcel.acquisition.hiddenness.value}
- Control method: {parcel.acquisition.control_method.value}
- Exit buyers: {exits}

## Fatal-Flaw Gates
{gates}

Blockers: {blockers}

## Evidence
{evidence}

## Diligence Checklist
- [ ] Confirm utility capacity with territory planner
- [ ] Verify sewer/water extension path and cost
- [ ] Title review for easements and mineral rights
- [ ] Zoning/comp plan alignment and approval path
- [ ] Drainage outlet and wetland delineation
- [ ] Owner outreach / control strategy
- [ ] Basis vs. downside value underwrite
"""
