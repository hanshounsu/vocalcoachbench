from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .io import read_jsonl, write_json
from .metrics import evaluate_direct_triplets, evaluate_score_triplets, evaluate_segment, evaluate_top3


def _print_or_write(payload: dict[str, Any], out: str | None) -> None:
    if out:
        write_json(out, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_evaluate_triplet(args: argparse.Namespace) -> None:
    pair_rows = read_jsonl(args.pairs)
    prediction_rows = read_jsonl(args.predictions)
    summary, per_triplet = evaluate_direct_triplets(pair_rows, prediction_rows)
    payload: dict[str, Any] = {"summary": summary}
    if args.details:
        payload["triplets"] = per_triplet
    _print_or_write(payload, args.out)


def cmd_evaluate_top3(args: argparse.Namespace) -> None:
    reference_rows = read_jsonl(args.references)
    prediction_rows = read_jsonl(args.predictions)
    summary, per_audio = evaluate_top3(reference_rows, prediction_rows)
    payload: dict[str, Any] = {"summary": summary}
    if args.details:
        payload["audios"] = per_audio
    _print_or_write(payload, args.out)


def cmd_evaluate_score_triplet(args: argparse.Namespace) -> None:
    pair_rows = read_jsonl(args.pairs)
    score_rows = read_jsonl(args.scores)
    summary, per_triplet = evaluate_score_triplets(pair_rows, score_rows)
    payload: dict[str, Any] = {"summary": summary}
    if args.details:
        payload["triplets"] = per_triplet
    _print_or_write(payload, args.out)


def cmd_evaluate_segment(args: argparse.Namespace) -> None:
    reference_rows = read_jsonl(args.references)
    prediction_rows = read_jsonl(args.predictions)
    summary, per_segment = evaluate_segment(reference_rows, prediction_rows)
    payload: dict[str, Any] = {"summary": summary}
    if args.details:
        payload["segments"] = per_segment
    _print_or_write(payload, args.out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vocalcoachbench",
        description="Evaluate VocalCoachBench prediction files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    triplet = subparsers.add_parser(
        "evaluate-triplet",
        help="Evaluate direct pairwise triplet ranking predictions.",
    )
    triplet.add_argument("--pairs", required=True, help="Pair manifest JSONL.")
    triplet.add_argument("--predictions", required=True, help="Pairwise prediction JSONL.")
    triplet.add_argument("--out", default=None, help="Optional summary JSON path.")
    triplet.add_argument("--details", action="store_true", help="Include per-triplet metrics.")
    triplet.set_defaults(func=cmd_evaluate_triplet)

    score_triplet = subparsers.add_parser(
        "evaluate-score-triplet",
        help="Evaluate auxiliary score-derived triplet ranking predictions.",
    )
    score_triplet.add_argument("--pairs", required=True, help="Pair manifest JSONL.")
    score_triplet.add_argument("--scores", required=True, help="Single-audio score prediction JSONL.")
    score_triplet.add_argument("--out", default=None, help="Optional summary JSON path.")
    score_triplet.add_argument("--details", action="store_true", help="Include per-triplet metrics.")
    score_triplet.set_defaults(func=cmd_evaluate_score_triplet)

    top3 = subparsers.add_parser(
        "evaluate-top3",
        help="Evaluate top-3 vocal issue predictions.",
    )
    top3.add_argument("--references", required=True, help="Top-3 reference JSONL.")
    top3.add_argument("--predictions", required=True, help="Top-3 prediction JSONL.")
    top3.add_argument("--out", default=None, help="Optional summary JSON path.")
    top3.add_argument("--details", action="store_true", help="Include per-audio metrics.")
    top3.set_defaults(func=cmd_evaluate_top3)

    segment = subparsers.add_parser(
        "evaluate-segment",
        help="Evaluate segment-conditioned issue classification.",
    )
    segment.add_argument("--references", required=True, help="Segment reference JSONL.")
    segment.add_argument("--predictions", required=True, help="Segment prediction JSONL.")
    segment.add_argument("--out", default=None, help="Optional summary JSON path.")
    segment.add_argument("--details", action="store_true", help="Include per-segment metrics.")
    segment.set_defaults(func=cmd_evaluate_segment)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    Path(".").resolve()
    args.func(args)


if __name__ == "__main__":
    main()
