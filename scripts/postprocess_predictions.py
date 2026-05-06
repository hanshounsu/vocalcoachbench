#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vocalcoachbench.io import read_jsonl, write_jsonl
from vocalcoachbench.postprocess import normalize_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize raw LALM outputs into VocalCoachBench prediction JSONL files.",
    )
    parser.add_argument("--task", required=True, choices=["direct_pairwise", "top3_score", "segment"])
    parser.add_argument("--input", required=True, help="Raw model output JSONL.")
    parser.add_argument("--out", required=True, help="Canonical prediction JSONL output path.")
    parser.add_argument("--print-summary", action="store_true", help="Print parse coverage summary.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = read_jsonl(args.input)
    normalized = normalize_rows(args.task, rows)
    write_jsonl(args.out, normalized)

    if args.print_summary:
        if args.task == "direct_pairwise":
            parsed = sum(1 for row in normalized if row.get("winner") in {"A", "B"})
            key = "winner"
        elif args.task == "top3_score":
            parsed = sum(1 for row in normalized if row.get("top3_issues") or row.get("quality_score_0_5") is not None)
            key = "top3_or_score"
        else:
            parsed = sum(1 for row in normalized if row.get("category"))
            key = "category"
        payload = {"task": args.task, "row_n": len(normalized), f"parsed_{key}_n": parsed}
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
