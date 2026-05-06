#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vocalcoachbench.io import read_jsonl, write_jsonl


def load_audio_metadata(path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    rows = read_jsonl(path)
    return {str(row["audio_id"]): row for row in rows if row.get("audio_id")}


def audio_path(audio_id: str, pair: dict[str, Any], metadata: dict[str, dict[str, Any]], side: str) -> str | None:
    inline_key = f"audio_{side.lower()}_path"
    if pair.get(inline_key):
        return str(pair[inline_key])
    if audio_id in metadata and metadata[audio_id].get("path"):
        return str(metadata[audio_id]["path"])
    return None


def call_model(prompt: str, audio_a_path: str, audio_b_path: str) -> dict[str, Any]:
    """Replace this function with a model/API call.

    The function should return a dictionary such as:
    {"winner": "A", "confidence": 0.82, "rationale": "..."}

    Keep provider-specific code outside the benchmark package so the public
    scorer stays dependency-light and anonymous-review friendly.
    """
    raise NotImplementedError("Implement call_model() for your audio-language model.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Template for direct pairwise triplet inference.")
    parser.add_argument("--pairs", required=True, help="Pair manifest JSONL.")
    parser.add_argument("--audio-metadata", default=None, help="Optional audio metadata JSONL with audio_id/path.")
    parser.add_argument("--prompt", default="prompts/direct_pairwise_triplet_v5.txt", help="Prompt text file.")
    parser.add_argument("--out", required=True, help="Prediction JSONL output path.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of pairs.")
    parser.add_argument("--resume", action="store_true", help="Skip pair_ids already present in --out.")
    parser.add_argument("--dry-run", action="store_true", help="Write request rows without calling a model.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    pairs = read_jsonl(args.pairs)
    metadata = load_audio_metadata(args.audio_metadata)
    prompt = Path(args.prompt).read_text(encoding="utf-8")
    out_path = Path(args.out)

    existing: dict[str, dict[str, Any]] = {}
    if args.resume and out_path.exists():
        existing = {str(row.get("pair_id")): row for row in read_jsonl(out_path) if row.get("pair_id")}

    rows: list[dict[str, Any]] = list(existing.values())
    pending = [pair for pair in pairs if str(pair.get("pair_id")) not in existing]
    if args.limit is not None:
        pending = pending[: args.limit]

    for pair in pending:
        pair_id = str(pair["pair_id"])
        audio_a_id = str(pair["audio_a_id"])
        audio_b_id = str(pair["audio_b_id"])
        audio_a = audio_path(audio_a_id, pair, metadata, "a")
        audio_b = audio_path(audio_b_id, pair, metadata, "b")
        if (audio_a is None or audio_b is None) and not args.dry_run:
            missing = [audio_id for audio_id, path in ((audio_a_id, audio_a), (audio_b_id, audio_b)) if path is None]
            raise ValueError(f"{pair_id} has unresolved audio path(s): {', '.join(missing)}")

        if args.dry_run:
            result = {
                "response_text": "",
                "dry_run": True,
                "audio_a_path": audio_a,
                "audio_b_path": audio_b,
            }
        else:
            result = call_model(prompt, audio_a, audio_b)

        rows.append(
            {
                "pair_id": pair_id,
                "audio_a_id": audio_a_id,
                "audio_b_id": audio_b_id,
                **result,
            }
        )
        write_jsonl(out_path, rows)


if __name__ == "__main__":
    main()
