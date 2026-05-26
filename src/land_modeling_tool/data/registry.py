from __future__ import annotations

import json
from pathlib import Path

from land_modeling_tool.config import OUTPUT_DIR, data_sources, prioritized_sources


def summarize_inventory() -> str:
    items = prioritized_sources()
    lines = ["# Data Source Inventory", ""]
    current_group = ""
    for item in items:
        group = item.get("group", "unknown")
        if group != current_group:
            current_group = group
            lines.append(f"## {group.replace('_', ' ').title()}")
            lines.append("")
        priority = item.get("priority", "P2")
        name = item.get("name", item.get("id", "?"))
        tier = item.get("tier", "")
        lines.append(f"- [{priority}] {name} ({tier})")
    lines.append("")
    lines.append(f"Total sources: {len(items)}")
    return "\n".join(lines)


def export_inventory(path: Path | None = None) -> Path:
    out = path or OUTPUT_DIR / "data_source_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "groups": data_sources(),
        "prioritized": prioritized_sources(),
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
