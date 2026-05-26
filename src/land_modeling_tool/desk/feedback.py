from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from land_modeling_tool.config import DATA_DIR

FEEDBACK_PATH = DATA_DIR / "feedback" / "rejections.jsonl"


@dataclass
class ExpertFeedback:
    parcel_id: str
    decision: str  # reject | pursue | watch | revise_score
    reason_code: str
    notes: str = ""
    reviewer: str = ""
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    def to_dict(self) -> dict:
        return asdict(self)


def feedback_path() -> Path:
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    return FEEDBACK_PATH


def record_feedback(entry: ExpertFeedback) -> None:
    path = feedback_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def load_feedback() -> list[ExpertFeedback]:
    path = feedback_path()
    if not path.exists():
        return []
    entries: list[ExpertFeedback] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        entries.append(ExpertFeedback(**data))
    return entries


def rejection_summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in load_feedback():
        if entry.decision == "reject":
            counts[entry.reason_code] = counts.get(entry.reason_code, 0) + 1
    return counts
