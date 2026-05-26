from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def investment_edge() -> dict[str, Any]:
    return load_yaml("investment_edge.yaml")


def data_sources() -> dict[str, Any]:
    return load_yaml("data_sources.yaml")


def scoring_weights() -> dict[str, Any]:
    return load_yaml("scoring_weights.yaml")


def signal_config() -> dict[str, Any]:
    return load_yaml("signals.yaml")


def prioritized_sources() -> list[dict[str, Any]]:
    registry = data_sources()
    items: list[dict[str, Any]] = []
    for group, entries in registry.items():
        for entry in entries:
            items.append({"group": group, **entry})
    order = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(items, key=lambda x: order.get(x.get("priority", "P2"), 9))
