from __future__ import annotations

from land_modeling_tool.desk.control_strategy import compute_control_strategy
from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.fatal_gates import gate_guidance
from land_modeling_tool.desk.legal_control import compute_legal_control
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.models.types import ParcelRecord
from land_modeling_tool.scoring.evidence import build_evidence_pack


def _bullet(items: list[str]) -> str:
    if not items:
        return "- None identified"
    return "\n".join(f"- {item}" for item in items)


def _gate_lines(parcel: ParcelRecord) -> str:
    lines: list[str] = []
    for gate in parcel.fatal.gates:
        severity = gate.severity.value.upper()
        status = "PASS" if gate.passed else "FAIL"
        lines.append(f"- [{severity}] {gate.gate_id}: {status} — {gate.notes}")
    return "\n".join(lines) or "- None"


def _facts(parcel: ParcelRecord, best_cat: str, fit: float) -> list[str]:
    return [
        f"Parcel {parcel.parcel_id} in {parcel.county} County ({parcel.acreage:.1f} ac).",
        f"Owner of record: {parcel.owner} ({parcel.owner_count} owner(s), {parcel.ownership_years:.0f} yr hold).",
        f"Assessed basis ~${parcel.acquisition.basis_per_acre:,.0f}/ac from county roll.",
        f"Zoning: {parcel.zoning}; entitlement path: {parcel.entitlement_path.value}.",
        f"Power: {parcel.power.utility_territory or 'unknown'} territory, "
        f"{parcel.power.transmission_voltage_kv}kV, substation {parcel.power.substation_miles:.1f} mi.",
        f"Water/sewer score {parcel.water.score:.2f}; sewer {parcel.water.sewer_miles:.1f} mi.",
        f"Floodway {parcel.floodway_pct:.0%}, wetlands {parcel.wetland_pct:.0%}, frontage {parcel.frontage_ft:.0f} ft.",
        f"Model fit peak: {best_cat} ({fit:.2f}); buy score {parcel.buy_score:.2f} ({parcel.buy_action}).",
    ]


def _assumptions(parcel: ParcelRecord, deal_math) -> list[str]:
    return [
        "County assessor value approximates current market unless a listing price is supplied.",
        f"Exit buyers include {', '.join(parcel.acquisition.exit_buyers) or 'strategic infrastructure capital'}.",
        f"Scenario bands use desk config multipliers; max basis ${deal_math.max_basis_per_acre:,.0f}/ac.",
        "Utility MW readiness proxies are indicative until confirmed by the serving utility.",
        f"Recommended control posture: {deal_math.recommended_control.replace('_', ' ')}.",
    ]


def _open_diligence(parcel: ParcelRecord, evidence_pack) -> list[str]:
    items = list(evidence_pack.diligence_questions)
    if parcel.fatal.soft_risks:
        items.append(f"Stress-test soft risks: {', '.join(parcel.fatal.soft_risks)}")
    return items


def _legal_risks(legal) -> list[str]:
    risks = list(legal.hard_blockers)
    risks.extend(f"Soft: {risk}" for risk in legal.soft_risks)
    risks.extend(
        [
            f"Title confidence {legal.title:.0%}, access {legal.access:.0%}, "
            f"seller authority {legal.seller_authority:.0%}.",
            f"Contract instrument: {legal.contract.instrument_type.value.replace('_', ' ')} "
            f"(binding={legal.contract.binding}, exclusive={legal.contract.exclusive}).",
        ]
    )
    return risks


def _business_risks(parcel: ParcelRecord, thesis) -> list[str]:
    risks = [
        f"Primary thesis: {thesis.primary_thesis}; backup: {thesis.backup_thesis}.",
        f"Hiddenness {parcel.acquisition.hiddenness.value}; listed={parcel.listed}.",
    ]
    if parcel.fatal.blockers:
        risks.append(f"Hard blockers: {', '.join(parcel.fatal.blockers)}")
    if parcel.fatal.soft_risks:
        risks.append(f"Soft risks: {', '.join(parcel.fatal.soft_risks)}")
    if thesis.weak_theses:
        risks.append(f"Weak theses: {', '.join(thesis.weak_theses)}")
    return risks


def render_memo(parcel: ParcelRecord) -> str:
    best_cat, fit = parcel.fit.best_category()
    thesis = build_thesis_matrix(parcel)
    deal_math = compute_deal_math(parcel)
    legal = compute_legal_control(parcel)
    control = compute_control_strategy(parcel, legal_score=legal, deal_math=deal_math, thesis=thesis)
    evidence_pack = build_evidence_pack(parcel)
    guidance = gate_guidance(parcel)
    reject_condition = next((line for line in guidance if "Reject unless:" in line), None)
    if not reject_condition:
        reject_condition = "No soft-gate reject condition triggered."

    hard_blockers = ", ".join(parcel.fatal.blockers) or "none"
    soft_risks = ", ".join(parcel.fatal.soft_risks) or "none"
    reject_unless = (
        f"Reject unless: {soft_risks} are resolved with documented diligence evidence."
        if parcel.fatal.soft_risks
        else "No soft-gate reject condition triggered."
    )
    exits = ", ".join(parcel.acquisition.exit_buyers)

    return f"""# Diligence Memo: {parcel.parcel_id}

## Executive Verdict
- Composite score: {parcel.composite_score:.2f}
- Buy score: {parcel.buy_score:.2f} ({parcel.buy_action})
- Deal math verdict: {deal_math.verdict}
- Serious shortlist: {parcel.serious_shortlist}
- Confidence: {parcel.confidence.value.replace('_', ' ')}
- {reject_unless}

## Primary Thesis
{thesis.primary_thesis.replace('_', ' ')} — {thesis.why_now}

Backup thesis: {thesis.backup_thesis.replace('_', ' ')}.

## Facts
{_bullet(_facts(parcel, best_cat, fit))}

## Assumptions
{_bullet(_assumptions(parcel, deal_math))}

## Open Diligence
{_bullet(_open_diligence(parcel, evidence_pack))}

## Legal Risks
{_bullet(_legal_risks(legal))}

## Business Risks
{_bullet(_business_risks(parcel, thesis))}

## Deal Math Summary
- Basis: ${deal_math.basis_per_acre:,.0f}/ac (market today ${deal_math.market_value_today:,.0f}/ac)
- Downside / base / upside: ${deal_math.downside_per_acre:,.0f} / ${deal_math.base_value_per_acre:,.0f} / ${deal_math.upside_per_acre:,.0f} per ac
- Total value bands: ${deal_math.downside_value:,.0f} / ${deal_math.base_value:,.0f} / ${deal_math.upside_value:,.0f}
- Max basis (do not exceed): ${deal_math.max_basis_per_acre:,.0f}/ac (${deal_math.do_not_exceed_price:,.0f} total)
- Max option premium: ${deal_math.max_option_premium_per_acre:,.0f}/ac
- Recommended strike: ${deal_math.recommended_strike_price:,.0f}/ac
- Expected payoff band: {deal_math.expected_payoff_band}
- Capital at risk: ${deal_math.capital_at_risk:,.0f}
- Probability bucket: {deal_math.probability_bucket}
- Holding period: {deal_math.holding_period_months} months
- Drop-dead: {deal_math.drop_dead_date or 'n/a'}
- Exercise/assign trigger: {deal_math.exercise_or_assign_trigger}
- Upside case: {deal_math.upside_case}
- Downside case: {deal_math.downside_case}

## Control Recommendation (Placeholder Hooks)
- Recommended control: {control.recommended_control.replace('_', ' ')}
- Alternatives: {', '.join(control.alternatives) or 'none'}
- Do not control: {control.do_not_control}
- Reason: {control.reason}
- Legal control score: {legal.legal_control_score:.0%}
- Contract instrument: {legal.contract.instrument_type.value.replace('_', ' ')}
- Option fee / strike: ${legal.contract.option_fee_per_acre:,.0f}/ac / ${legal.contract.strike_price_per_acre:,.0f}/ac
- Contingencies: {', '.join(legal.contract.contingencies)}

## Fatal-Flaw Gates
{_gate_lines(parcel)}

Hard blockers: {hard_blockers}

Soft risks: {soft_risks}

Gate guidance:
- {reject_condition}
{_bullet([g for g in guidance if g != reject_condition])}
- {reject_unless}

## Infrastructure Path
- 10-50 MW readiness: {parcel.power.mw_10_50:.2f}
- 100-300 MW readiness: {parcel.power.mw_100_300:.2f}
- 500+ MW readiness: {parcel.power.mw_500_plus:.2f}
- Water/sewer score: {parcel.water.score:.2f}

## Owner Strategy
- Hiddenness: {parcel.acquisition.hiddenness.value}
- Mispricing signal: {parcel.acquisition.mispricing_signal:.2f}
- Exit buyers: {exits}
- Must prove: {', '.join(thesis.must_prove)}

## Kill Criteria
- Any unresolved hard blocker after diligence spend cap
- Utility cannot confirm serveable MW within holding period
- Max basis exceeds ${deal_math.max_basis_per_acre:,.0f}/ac or seller will not grant control instrument

## Next Action
- {control.reason if control.do_not_control else 'Run open diligence items, then execute owner outreach using call sheet.'}
"""


def memo_sections(parcel: ParcelRecord) -> dict[str, list[str] | str]:
    """Structured memo sections for JSON export or UI rendering."""
    best_cat, fit = parcel.fit.best_category()
    thesis = build_thesis_matrix(parcel)
    deal_math = compute_deal_math(parcel)
    legal = compute_legal_control(parcel)
    control = compute_control_strategy(parcel, legal_score=legal, deal_math=deal_math, thesis=thesis)
    evidence_pack = build_evidence_pack(parcel)

    return {
        "parcel_id": parcel.parcel_id,
        "executive_verdict": parcel.buy_action,
        "facts": _facts(parcel, best_cat, fit),
        "assumptions": _assumptions(parcel, deal_math),
        "open_diligence": _open_diligence(parcel, evidence_pack),
        "legal_risks": _legal_risks(legal),
        "business_risks": _business_risks(parcel, thesis),
        "deal_math": deal_math.to_dict(),
        "control_hooks": control.to_dict(),
        "legal_control": legal.to_dict(),
        "gate_guidance": gate_guidance(parcel),
    }
