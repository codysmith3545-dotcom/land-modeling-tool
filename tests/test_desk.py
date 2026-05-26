from __future__ import annotations

from pathlib import Path

from land_modeling_tool.data.candidate_intake import intake_schema, load_all_parcels, load_candidates_csv
from land_modeling_tool.data.loaders import load_nodes, load_parcels
from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.deal_queue import build_deal_queue
from land_modeling_tool.desk.feedback import ExpertFeedback, load_feedback, record_feedback, rejection_summary
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.scoring.nodes import rank_nodes, rank_parcels


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


def test_deal_math_max_basis():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_all_parcels(), nodes)
    result = compute_deal_math(parcels[0])
    assert result.max_basis_per_acre >= result.downside_per_acre
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


def test_pipeline_desk_outputs(tmp_path):
    from land_modeling_tool.pipeline import run_pipeline

    summary = run_pipeline(tmp_path)
    assert summary.get("deal_queue", 0) >= 0
    assert (tmp_path / "deal_queue.json").exists()
    assert (tmp_path / "parcel_thesis_matrix.json").exists()
    assert (tmp_path / "deal_math.json").exists()
    assert (tmp_path / "weekly_desk_report.md").exists()
    assert (tmp_path / "call_sheets").is_dir()
