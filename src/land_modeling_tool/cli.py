from __future__ import annotations

import argparse
import json
import sys

from land_modeling_tool.config import OUTPUT_DIR, investment_edge, prioritized_sources
from land_modeling_tool.data.loaders import load_nodes, load_parcels
from land_modeling_tool.data.registry import export_inventory, summarize_inventory
from land_modeling_tool.pipeline import run_pipeline
from land_modeling_tool.scoring.nodes import rank_nodes, rank_parcels, top_shortlist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="land-model",
        description="Infrastructure-option land intelligence for Indiana/Midwest acquisition",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("edge", help="Print investment edge configuration")

    inv = sub.add_parser("inventory", help="Print prioritized data source inventory")
    inv.add_argument("--json", action="store_true", help="Output JSON")

    run = sub.add_parser("run", help="Run full scoring pipeline and write outputs")
    run.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_DIR),
        help="Output directory (default: outputs/)",
    )

    rank = sub.add_parser("rank", help="Rank sample parcels and print top N")
    rank.add_argument("-n", type=int, default=10, help="Number of parcels to show")

    args = parser.parse_args(argv)

    if args.command == "edge":
        print(json.dumps(investment_edge(), indent=2))
        return 0

    if args.command == "inventory":
        if args.json:
            print(json.dumps(prioritized_sources(), indent=2))
        else:
            print(summarize_inventory())
        return 0

    if args.command == "run":
        from pathlib import Path

        summary = run_pipeline(Path(args.output))
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "rank":
        nodes = rank_nodes(load_nodes())
        parcels = rank_parcels(load_parcels(), nodes)
        for parcel in top_shortlist(parcels, limit=args.n):
            cat, fit = parcel.fit.best_category()
            print(
                f"{parcel.parcel_id}\t{parcel.county}\t{parcel.composite_score:.3f}\t"
                f"{cat}\t{fit:.2f}\tshortlist={parcel.serious_shortlist}"
            )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
