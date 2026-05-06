#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vocalcoachbench.io import read_jsonl, write_json, write_jsonl
from vocalcoachbench.taxonomy import normalize_category_list


def release_root(path: str | Path) -> Path:
    root = Path(path)
    if (root / "annotations").exists():
        return root
    nested = root / "VocalCoachBench_annotations"
    if (nested / "annotations").exists():
        return nested
    raise FileNotFoundError(
        f"Could not find annotations/ under {root} or {nested}. "
        "Pass the Hugging Face dataset root or VocalCoachBench_annotations directory."
    )


def pair_agreement(order_a: list[str], order_b: list[str]) -> int:
    hits = 0
    for left, right in itertools.combinations(order_a, 2):
        hits += int((order_a.index(left) < order_a.index(right)) == (order_b.index(left) < order_b.index(right)))
    return hits


def clean_reference_orders(rows: list[dict[str, Any]], policy: str) -> list[list[str]]:
    orders = [[str(item) for item in row["ranked_audio_ids_best_to_worst"]] for row in rows]
    if policy == "all":
        return orders
    if policy != "clean":
        raise ValueError(f"Unknown triplet policy: {policy}")

    if len(orders) == 2:
        return orders if pair_agreement(orders[0], orders[1]) >= 2 else []

    unique_orders: list[list[str]] = []
    for order in orders:
        if order not in unique_orders:
            unique_orders.append(order)
    if len(unique_orders) == 1:
        return [unique_orders[0], unique_orders[0]]
    return []


def build_triplet_pairs(annotation_dir: Path, triplet_policy: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rankings = read_jsonl(annotation_dir / "triplet_rankings.jsonl")
    by_triplet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rankings:
        by_triplet[str(row["triplet_id"])].append(row)

    pair_rows: list[dict[str, Any]] = []
    skipped = 0
    kept_triplets = 0
    for triplet_id, rows in sorted(by_triplet.items()):
        reference_orders = clean_reference_orders(rows, triplet_policy)
        if not reference_orders:
            skipped += 1
            continue

        audio_ids = sorted({audio_id for row in rows for audio_id in row["display_order_audio_ids"]})
        if len(audio_ids) != 3:
            skipped += 1
            continue

        kept_triplets += 1
        for pair_index, (audio_a, audio_b) in enumerate(itertools.combinations(audio_ids, 2), start=1):
            pair_rows.append(
                {
                    "pair_id": f"{triplet_id}_pair_{pair_index}",
                    "triplet_id": triplet_id,
                    "triplet_instance_id": triplet_id,
                    "audio_a_id": audio_a,
                    "audio_b_id": audio_b,
                    "reference_orders": reference_orders,
                }
            )

    summary = {
        "source_annotation_rows": len(rankings),
        "source_triplet_count": len(by_triplet),
        "triplet_policy": triplet_policy,
        "kept_triplet_count": kept_triplets,
        "skipped_triplet_count": skipped,
        "pair_count": len(pair_rows),
    }
    return pair_rows, summary


def build_top3_references(annotation_dir: Path) -> list[dict[str, Any]]:
    by_audio: dict[str, list[list[str]]] = defaultdict(list)
    for row in read_jsonl(annotation_dir / "top3_issue_annotations.jsonl"):
        audio_id = str(row["audio_id"])
        issues = normalize_category_list(row.get("top3_issues"), limit=3)
        if issues:
            by_audio[audio_id].append(issues)
    return [{"audio_id": audio_id, "references": refs} for audio_id, refs in sorted(by_audio.items())]


def build_segment_references(annotation_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(annotation_dir / "segment_consensus_events.jsonl"):
        labels = normalize_category_list(row.get("consensus_issues"))
        rows.append(
            {
                "sample_id": row["event_uid"],
                "audio_id": row.get("audio_id"),
                "labels": labels,
            }
        )
    return rows


def prepared_audio_path(path: object, out_dir: Path) -> str | None:
    if not path:
        return None
    path_text = str(path)
    if Path(path_text).is_absolute():
        return path_text
    return str(out_dir / path_text)


def build_audio_metadata(annotation_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(annotation_dir / "recordings.jsonl"):
        rows.append(
            {
                "audio_id": row.get("audio_id") or str(row["recording_id"]).split("_", 1)[-1],
                "recording_id": row.get("recording_id"),
                "path": prepared_audio_path(row.get("audio_path"), out_dir),
                "audio_filename": row.get("audio_filename"),
                "audio_redistributed": row.get("audio_redistributed"),
                "audio_access": row.get("audio_access"),
                "subset": row.get("subset"),
                "source_dataset": row.get("source_dataset"),
                "song_title": row.get("song_title"),
            }
        )
    return rows


def build_segment_metadata(annotation_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(annotation_dir / "segment_consensus_events.jsonl"):
        rows.append(
            {
                "sample_id": row["event_uid"],
                "audio_id": row.get("audio_id"),
                "path": prepared_audio_path(row.get("clip_path"), out_dir),
                "clip_filename": row.get("clip_filename"),
                "clip_redistributed": row.get("clip_redistributed"),
                "recording_id": row.get("recording_id"),
                "overlap_start": row.get("overlap_start"),
                "overlap_end": row.get("overlap_end"),
                "overlap_duration": row.get("overlap_duration"),
                "source_dataset": row.get("source_dataset"),
            }
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare scorer-ready JSONL files from the VocalCoachBench HF release.")
    parser.add_argument("--hf-root", required=True, help="Path to the downloaded HF release or VocalCoachBench_annotations directory.")
    parser.add_argument("--out-dir", default="data", help="Directory where scorer-ready files will be written.")
    parser.add_argument("--triplet-policy", choices=["clean", "all"], default="clean", help="Triplet reference policy. Default matches the main benchmark setting.")
    parser.add_argument("--no-link-audio", action="store_true", help="Do not create out-dir/audio symlink to the HF release audio directory.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = release_root(args.hf_root)
    annotation_dir = root / "annotations"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    triplet_pairs, triplet_summary = build_triplet_pairs(annotation_dir, args.triplet_policy)
    top3_references = build_top3_references(annotation_dir)
    segment_references = build_segment_references(annotation_dir)
    audio_metadata = build_audio_metadata(annotation_dir, out_dir)
    segment_metadata = build_segment_metadata(annotation_dir, out_dir)

    audio_link_created = False
    audio_source = root / "audio"
    audio_target = out_dir / "audio"
    if not args.no_link_audio and audio_source.exists() and not audio_target.exists():
        audio_target.symlink_to(audio_source, target_is_directory=True)
        audio_link_created = True

    write_jsonl(out_dir / "triplet_pairs.jsonl", triplet_pairs)
    write_jsonl(out_dir / "top3_references.jsonl", top3_references)
    write_jsonl(out_dir / "segment_references.jsonl", segment_references)
    write_jsonl(out_dir / "audio_metadata.jsonl", audio_metadata)
    write_jsonl(out_dir / "segment_metadata.jsonl", segment_metadata)

    summary = {
        "hf_root": str(root),
        "out_dir": str(out_dir),
        **triplet_summary,
        "top3_audio_count": len(top3_references),
        "segment_count": len(segment_references),
        "audio_metadata_count": len(audio_metadata),
        "segment_metadata_count": len(segment_metadata),
        "audio_link_created": audio_link_created,
        "audio_link_path": str(audio_target) if audio_target.exists() else None,
    }
    write_json(out_dir / "prepare_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
