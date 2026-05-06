#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vocalcoachbench.io import read_jsonl, write_json
from vocalcoachbench.metrics import (
    evaluate_direct_triplets,
    evaluate_score_triplets,
    evaluate_segment,
    evaluate_top3,
)


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def unique_glob(directory: Path, patterns: list[str]) -> Path | None:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(sorted(directory.glob(pattern)))
    unique = sorted(set(matches))
    if len(unique) == 1:
        return unique[0]
    return None


def resolve_prediction(explicit: str | None, directory: Path, patterns: list[str]) -> Path | None:
    if explicit:
        return Path(explicit)
    return unique_glob(directory, patterns)


def evaluate_task(
    name: str,
    summary: dict[str, Any],
    details: list[dict[str, Any]],
    output_dir: Path,
    save_details: bool,
) -> dict[str, Any]:
    task_payload: dict[str, Any] = {"summary": summary}
    write_json(output_dir / f"{name}.json", task_payload)
    if save_details:
        write_json(output_dir / f"{name}_details.json", details)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate all available VocalCoachBench prediction files.",
    )
    parser.add_argument("--data-dir", default="data", help="Directory containing benchmark reference JSONL files.")
    parser.add_argument("--predictions-dir", default="predictions", help="Directory containing model prediction JSONL files.")
    parser.add_argument("--output-dir", default="results", help="Directory for metric JSON outputs.")
    parser.add_argument("--direct-pairwise", default=None, help="Optional direct pairwise prediction JSONL path.")
    parser.add_argument("--top3", default=None, help="Optional top-3 prediction JSONL path.")
    parser.add_argument("--scores", default=None, help="Optional single-audio score prediction JSONL path.")
    parser.add_argument("--segment", default=None, help="Optional segment prediction JSONL path.")
    parser.add_argument("--details", action="store_true", help="Write per-sample detail files.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data_dir = Path(args.data_dir)
    predictions_dir = Path(args.predictions_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pair_manifest = first_existing([data_dir / "triplet_pairs.jsonl", data_dir / "direct_pairwise_pairs.jsonl"])
    top3_refs = data_dir / "top3_references.jsonl"
    segment_refs = data_dir / "segment_references.jsonl"

    direct_predictions = resolve_prediction(
        args.direct_pairwise,
        predictions_dir,
        ["*direct_pairwise*.jsonl", "*pairwise*.jsonl"],
    )
    top3_predictions = resolve_prediction(
        args.top3,
        predictions_dir,
        ["top3_predictions.jsonl", "*_top3_predictions.jsonl", "*_top3.jsonl"],
    )
    score_predictions = resolve_prediction(args.scores, predictions_dir, ["*score*.jsonl", "*scores*.jsonl"])
    segment_predictions = resolve_prediction(
        args.segment,
        predictions_dir,
        ["segment_predictions.jsonl", "*_segment_predictions.jsonl", "*_segment.jsonl"],
    )

    report: dict[str, Any] = {"tasks": {}, "missing": {}}

    if pair_manifest and direct_predictions and direct_predictions.exists():
        summary, details = evaluate_direct_triplets(read_jsonl(pair_manifest), read_jsonl(direct_predictions))
        report["tasks"]["direct_pairwise_triplet"] = evaluate_task(
            "direct_pairwise_triplet",
            summary,
            details,
            output_dir,
            args.details,
        )
    else:
        report["missing"]["direct_pairwise_triplet"] = {
            "reference": str(pair_manifest) if pair_manifest else "triplet_pairs.jsonl",
            "prediction": str(direct_predictions) if direct_predictions else "not found",
        }

    if top3_refs.exists() and top3_predictions and top3_predictions.exists():
        summary, details = evaluate_top3(read_jsonl(top3_refs), read_jsonl(top3_predictions))
        report["tasks"]["top3"] = evaluate_task("top3", summary, details, output_dir, args.details)
    else:
        report["missing"]["top3"] = {
            "reference": str(top3_refs),
            "prediction": str(top3_predictions) if top3_predictions else "not found",
        }

    if pair_manifest and score_predictions and score_predictions.exists():
        summary, details = evaluate_score_triplets(read_jsonl(pair_manifest), read_jsonl(score_predictions))
        report["tasks"]["score_triplet"] = evaluate_task("score_triplet", summary, details, output_dir, args.details)
    else:
        report["missing"]["score_triplet"] = {
            "reference": str(pair_manifest) if pair_manifest else "triplet_pairs.jsonl",
            "prediction": str(score_predictions) if score_predictions else "not found",
        }

    if segment_refs.exists() and segment_predictions and segment_predictions.exists():
        summary, details = evaluate_segment(read_jsonl(segment_refs), read_jsonl(segment_predictions))
        report["tasks"]["segment"] = evaluate_task("segment", summary, details, output_dir, args.details)
    else:
        report["missing"]["segment"] = {
            "reference": str(segment_refs),
            "prediction": str(segment_predictions) if segment_predictions else "not found",
        }

    write_json(output_dir / "all_metrics.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
