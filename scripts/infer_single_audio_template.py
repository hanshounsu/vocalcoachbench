#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from vocalcoachbench.io import read_jsonl, write_jsonl


PROMPT_BY_TASK = {
    "top3_score": "prompts/objective_top3_score_v5.txt",
    "segment": "prompts/structured_segment_v5.txt",
}


def call_model(prompt: str, audio_path: str, task: str) -> dict[str, Any]:
    """Replace this function with a model/API call.

    For task="top3_score", return fields such as:
    {"top3_issues": ["PITCH", "BREATH", "PHONATION"], "quality_score_0_5": 3.2}

    For task="segment", return fields such as:
    {"category": "PITCH", "confidence": 0.75}
    """
    raise NotImplementedError("Implement call_model() for your audio-language model.")


def row_id(row: dict[str, Any], task: str) -> str:
    key = "sample_id" if task == "segment" else "audio_id"
    return str(row.get(key) or row.get("id") or "")


def row_audio_path(row: dict[str, Any]) -> str:
    return str(row.get("path") or row.get("audio_path") or row.get("audio_id") or row.get("sample_id") or row.get("id"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Template for single-audio VocalCoachBench inference.")
    parser.add_argument("--task", required=True, choices=sorted(PROMPT_BY_TASK), help="Task to run.")
    parser.add_argument("--inputs", required=True, help="Input JSONL with audio_id/path or sample_id/path.")
    parser.add_argument("--prompt", default=None, help="Optional prompt text file.")
    parser.add_argument("--out", required=True, help="Prediction JSONL output path.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of audios.")
    parser.add_argument("--resume", action="store_true", help="Skip ids already present in --out.")
    parser.add_argument("--dry-run", action="store_true", help="Write request rows without calling a model.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    inputs = read_jsonl(args.inputs)
    prompt_path = args.prompt or PROMPT_BY_TASK[args.task]
    prompt = Path(prompt_path).read_text(encoding="utf-8")
    out_path = Path(args.out)

    id_key = "sample_id" if args.task == "segment" else "audio_id"
    existing: dict[str, dict[str, Any]] = {}
    if args.resume and out_path.exists():
        existing = {str(row.get(id_key)): row for row in read_jsonl(out_path) if row.get(id_key)}

    rows: list[dict[str, Any]] = list(existing.values())
    pending = [row for row in inputs if row_id(row, args.task) and row_id(row, args.task) not in existing]
    if args.limit is not None:
        pending = pending[: args.limit]

    for item in pending:
        item_id = row_id(item, args.task)
        audio = row_audio_path(item)
        if args.dry_run:
            result = {"response_text": "", "dry_run": True, "audio_path": audio}
        else:
            result = call_model(prompt, audio, args.task)
        rows.append({id_key: item_id, **result})
        write_jsonl(out_path, rows)


if __name__ == "__main__":
    main()
