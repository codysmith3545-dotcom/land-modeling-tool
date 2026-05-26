from __future__ import annotations

import json
from pathlib import Path

from land_modeling_tool.data.candidate_intake import intake_schema, load_all_parcels, load_candidates_csv
from land_modeling_tool.data.loaders import load_nodes, load_parcels
from land_modeling_tool.desk.call_sheets import render_owner_call_sheet
from land_modeling_tool.desk.control_strategy import (
    compute_all_control_strategies,
    compute_control_strategy,
    recommend_control_method,
)
from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.deal_queue import build_deal_queue
from land_modeling_tool.desk.feedback import ExpertFeedback, load_feedback, record_feedback, rejection_summary
from land_modeling_tool.desk.legal_control import compute_all_legal_control, compute_legal_control
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.desk.weekly_report import build_weekly_desk_report
from land_modeling_tool.scoring.nodes import rank_nodes, rank_parcels
from land_modeling_tool.proof.diligence_memo import render_memo


def test_intake_schema():
    schema = intake_schema()
    assert schema["schema_version"] == "1.0"
    assert "parcel_id" in schema["fields"]


def test_load_all_parcels_includes_candidates():
    parcels = load_all_parcels()
    assert len(parcels) >= len(load_parcels())
    ids = {p.parcel_id for p in parcels}
    assert "CAND-001" in ids


def test_thesis_matrix_four_lanes():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    matrix = build_thesis_matrix(parcels[0])
    assert len(matrix.lanes) == 4
    assert matrix.primary_thesis in {lane.lane_id for lane in matrix.lanes}


def test_deal_queue_has_next_action():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    queue = build_deal_queue(parcels, limit=5)
    assert queue
    assert queue[0].next_action
    assert queue[0].fastest_kill_test


def test_legal_control_seven_dimensions():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    score = compute_legal_control(parcels[0])
    assert 0 <= score.legal_control_score <= 1
    for dim in ("title", "access", "seller_authority", "zoning", "environmental", "utility", "contract_control"):
        assert 0 <= getattr(score, dim) <= 1
    assert score.contract.instrument_type
    payload = score.to_dict()
    for key in (
        "title",
        "access",
        "seller_authority",
        "zoning",
        "environmental",
        "utility",
        "contract_control",
        "hard_blockers",
        "soft_risks",
        "contract",
    ):
        assert key in payload


def test_compute_all_legal_control():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    scores = compute_all_legal_control(parcels)
    assert len(scores) == len(parcels)
    assert scores[0].parcel_id == parcels[0].parcel_id


def test_control_strategy_recommends_known_methods():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    parcel = next(p for p in parcels if p.parcel_id == "IN-LAKE-001")
    legal = compute_legal_control(parcel)
    strategy = recommend_control_method(parcel, legal_score=legal)
    assert strategy.recommended_control in {
        "option",
        "assignable_purchase_agreement",
        "phased_assemblage",
        "outright_purchase",
        "do_not_control",
    }
    assert strategy.reason
    assert strategy.to_dict()["recommended_control"] == strategy.recommended_control


def test_control_strategy_do_not_control_on_hard_blockers():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    parcel = next(p for p in parcels if p.parcel_id == "IN-LAKE-006")
    legal = compute_legal_control(parcel)
    assert legal.hard_blockers
    strategy = recommend_control_method(parcel, legal_score=legal)
    assert strategy.do_not_control
    assert strategy.recommended_control == "do_not_control"


def test_compute_all_control_strategies():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    legal_map = {p.parcel_id: compute_legal_control(p) for p in parcels}
    strategies = compute_all_control_strategies(parcels, legal_scores=legal_map)
    assert len(strategies) == len(parcels)
    assert strategies[0].recommended_control


def test_deal_queue_uses_legal_hard_blockers():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    legal_map = {p.parcel_id: compute_legal_control(p) for p in parcels}
    control_map = {
        p.parcel_id: recommend_control_method(p, legal_score=legal_map[p.parcel_id]).recommended_control
        for p in parcels
    }
    queue = build_deal_queue(
        parcels,
        limit=50,
        legal_control=legal_map,
        control_strategy=control_map,
    )
    blocked = next(item for item in queue if item.parcel_id == "IN-LAKE-006")
    assert blocked.next_action == "reject"
    assert blocked.legal_hard_blockers
    assert blocked.recommended_control == "do_not_control"
    assert "Legal hard blocker" in blocked.why


def test_deal_math_max_basis():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    result = compute_deal_math(parcels[0])
    assert result.max_basis_per_acre >= result.downside_per_acre
    assert result.downside_value_per_acre <= result.base_value_per_acre <= result.upside_value_per_acre
    assert result.downside_value <= result.base_value <= result.upside_value
    assert result.recommended_strike_price <= result.max_basis_per_acre
    assert result.probability_bucket in {"high", "med", "low"}
    assert result.holding_period_months > 0
    assert result.capital_at_risk >= result.diligence_cost_estimate
    assert result.exercise_or_assign_trigger
    assert result.verdict in {"pursue", "diligence", "watch", "pass"}


def test_expert_feedback_roundtrip(tmp_path, monkeypatch):
    from land_modeling_tool.desk import feedback as fb

    monkeypatch.setattr(fb, "FEEDBACK_PATH", tmp_path / "rejections.jsonl")
    record_feedback(
        ExpertFeedback(
            parcel_id="TEST-1",
            decision="reject",
            reason_code="not_serveable_power",
            notes="Utility confirmed no MW",
        )
    )
    entries = load_feedback()
    assert len(entries) == 1
    assert rejection_summary()["not_serveable_power"] == 1


def test_control_strategy_do_not_control_when_blocked():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    parcel = parcels[0]
    parcel.fatal.blockers = ["title_not_curable"]
    legal = compute_legal_control(parcel)
    strategy = compute_control_strategy(parcel, legal_score=legal)
    assert strategy.do_not_control is True
    assert strategy.recommended_control == "do_not_control"


def test_pipeline_desk_outputs(tmp_path):
    from land_modeling_tool.pipeline import run_pipeline

    summary = run_pipeline(tmp_path)
    assert summary.get("deal_queue", 0) >= 0
    assert (tmp_path / "deal_queue.json").exists()
    assert (tmp_path / "parcel_thesis_matrix.json").exists()
    assert (tmp_path / "deal_math.json").exists()
    assert (tmp_path / "legal_control.json").exists()
    assert (tmp_path / "control_strategy.json").exists()
    assert (tmp_path / "weekly_desk_report.md").exists()
    assert (tmp_path / "call_sheets").is_dir()

    deal_math_payload = json.loads((tmp_path / "deal_math.json").read_text(encoding="utf-8"))
    legal_payload = json.loads((tmp_path / "legal_control.json").read_text(encoding="utf-8"))
    control_payload = json.loads((tmp_path / "control_strategy.json").read_text(encoding="utf-8"))
    queue_payload = json.loads((tmp_path / "deal_queue.json").read_text(encoding="utf-8"))

    assert deal_math_payload and legal_payload and control_payload
    first = deal_math_payload[0]
    for key in (
        "downside_value",
        "base_value",
        "upside_value",
        "recommended_strike_price",
        "expected_payoff_band",
        "capital_at_risk",
        "do_not_exceed_price",
        "probability_bucket",
        "holding_period_months",
        "diligence_cost_estimate",
        "drop_dead_date",
        "exercise_or_assign_trigger",
    ):
        assert key in first

    assert "legal_control_score" in legal_payload[0]
    assert "hard_blockers" in legal_payload[0]
    assert "recommended_control" in control_payload[0]
    assert "reason" in control_payload[0]
    if queue_payload:
        assert "legal_control_score" in queue_payload[0]
        assert "recommended_control" in queue_payload[0]
        assert "legal_hard_blockers" in queue_payload[0]


def test_reports_surface_control_structure():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    report = build_weekly_desk_report(parcels, nodes=nodes[:3])
    owner_sheet = render_owner_call_sheet(parcels[0])
    assert "Recommended control" in report
    assert "Scenario bands" in report
    assert "Capital at risk" in report
    assert "Recommended control structure" in owner_sheet
    assert "Scenario bands" in owner_sheet
    assert "Exercise / assign trigger" in owner_sheet


def test_diligence_memo_has_phase_two_sections():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    candidate = next((p for p in parcels if p.listed or p.industrial_park), parcels[0])
    memo = render_memo(candidate)
    assert "## Facts" in memo
    assert "## Assumptions" in memo
    assert "## Open Diligence" in memo
    assert "## Legal Risks" in memo
    assert "## Business Risks" in memo
    assert "## Deal Math Summary" in memo
    assert "## Control Recommendation (Placeholder Hooks)" in memo
    assert "Reject unless:" in memo or "No soft-gate reject condition triggered." in memo
