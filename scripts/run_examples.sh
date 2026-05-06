#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python "$ROOT/scripts/postprocess_predictions.py" \
  --task direct_pairwise \
  --input "$ROOT/examples/raw_direct_pairwise_outputs.jsonl" \
  --out "$ROOT/outputs/example_postprocessed_direct_pairwise.jsonl"

python "$ROOT/scripts/postprocess_predictions.py" \
  --task top3_score \
  --input "$ROOT/examples/raw_top3_score_outputs.jsonl" \
  --out "$ROOT/outputs/example_postprocessed_top3_score.jsonl"

python "$ROOT/scripts/postprocess_predictions.py" \
  --task segment \
  --input "$ROOT/examples/raw_segment_outputs.jsonl" \
  --out "$ROOT/outputs/example_postprocessed_segment.jsonl"

vocalcoachbench evaluate-triplet \
  --pairs "$ROOT/examples/triplet_pairs.jsonl" \
  --predictions "$ROOT/examples/direct_pairwise_predictions.jsonl"

vocalcoachbench evaluate-top3 \
  --references "$ROOT/examples/top3_references.jsonl" \
  --predictions "$ROOT/examples/top3_predictions.jsonl"

vocalcoachbench evaluate-score-triplet \
  --pairs "$ROOT/examples/triplet_pairs.jsonl" \
  --scores "$ROOT/examples/score_predictions.jsonl"

vocalcoachbench evaluate-segment \
  --references "$ROOT/examples/segment_references.jsonl" \
  --predictions "$ROOT/examples/segment_predictions.jsonl"

python "$ROOT/scripts/evaluate_all.py" \
  --data-dir "$ROOT/examples" \
  --predictions-dir "$ROOT/examples" \
  --output-dir "$ROOT/outputs/example_metrics"
