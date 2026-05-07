# Submission Guide

This repository provides the public scorer. A complete benchmark submission
contains prediction JSONL files for the tasks being evaluated.

The benchmark dataset provides the reference files. Participants provide model
prediction files. The scorer combines those two sets of files to compute metrics.
If a model returns raw text rather than canonical JSONL fields, normalize the
outputs with `scripts/postprocess_predictions.py` before scoring.
The small `examples/raw_*_outputs.jsonl` files only demonstrate this
normalization step.

In other words, `raw_outputs/*.jsonl` is optional and archival; `predictions/*.jsonl`
is the scorer input.

If the benchmark data is downloaded from Hugging Face, first run
`scripts/prepare_hf_release.py` as described in `docs/huggingface_dataset.md`.
Then pass the prepared directory via `--data-dir`.

To evaluate all available tasks in one command:

```bash
python scripts/evaluate_all.py \
  --data-dir data \
  --predictions-dir predictions \
  --output-dir results
```

## Direct Pairwise Triplet Ranking

Run each pair from the released manifest with the direct pairwise prompt:

```bash
vocalcoachbench evaluate-triplet \
  --pairs data/triplet_pairs.jsonl \
  --predictions predictions/my_model_direct_pairwise.jsonl \
  --out results/my_model_triplet.json
```

The model should receive two labeled audio inputs, Audio A and Audio B, and
choose the better performance. The ranking is reconstructed from the three pair
decisions in each triplet.

Auxiliary score-derived triplet ranking can be computed from single-audio
quality scores:

```bash
vocalcoachbench evaluate-score-triplet \
  --pairs data/triplet_pairs.jsonl \
  --scores predictions/my_model_scores.jsonl \
  --out results/my_model_score_triplet.json
```

## Top-3 Issue Prediction

```bash
vocalcoachbench evaluate-top3 \
  --references data/top3_references.jsonl \
  --predictions predictions/my_model_top3.jsonl \
  --out results/my_model_top3.json
```

Submit exactly three issue categories per audio, ordered from most serious to
third most serious.

## Segment-Level Issue Classification

```bash
vocalcoachbench evaluate-segment \
  --references data/segment_references.jsonl \
  --predictions predictions/my_model_segment.jsonl \
  --out results/my_model_segment.json
```

Submit one issue category per short segment.

## Open-Ended Feedback

Open-ended coaching feedback is evaluated through claim extraction and judge
models. The prompt templates in `prompts/` define the expected structured
claims. Judge execution is backend-specific and is not part of the deterministic
scorer CLI.
