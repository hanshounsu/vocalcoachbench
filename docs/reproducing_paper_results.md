# Reproducing Paper Results

This repository is designed to make the benchmark evaluation protocol
inspectable and reusable while keeping provider-specific inference code out of
the public scorer.

## What Is Fully Reproducible Here

Given the released reference files and model prediction JSONL files, the metric
values are deterministic:

```bash
python scripts/evaluate_all.py \
  --data-dir data \
  --predictions-dir predictions \
  --output-dir results
```

This computes:

- direct pairwise triplet ranking,
- top-3 issue prediction,
- auxiliary score-derived triplet ranking,
- segment-conditioned issue classification.

## Model Inference

Model inference is separated from scoring. The template scripts show the
expected adapter boundary:

```bash
python scripts/infer_direct_pairwise_template.py \
  --pairs data/triplet_pairs.jsonl \
  --audio-metadata data/audio_metadata.jsonl \
  --out predictions/my_model_direct_pairwise.jsonl

python scripts/infer_single_audio_template.py \
  --task top3_score \
  --inputs data/audio_metadata.jsonl \
  --out predictions/my_model_top3_score.jsonl

python scripts/infer_single_audio_template.py \
  --task segment \
  --inputs data/segment_metadata.jsonl \
  --out predictions/my_model_segment.jsonl
```

The `call_model(...)` functions in those files are intentionally placeholders.
Users should implement them with their own local model or API backend.
Those scripts can write raw output rows with `response_text`; the raw rows can
then be normalized with `scripts/postprocess_predictions.py` into canonical
prediction JSONL files for scoring.

Closed API models can change over time, and their exact outputs may depend on
model versioning, serving behavior, and decoding settings. For that reason, the
public benchmark package treats prediction JSONL files as the reproducible
interface between model inference and scoring.

## Recommended Paper-Result Workflow

1. Download the benchmark dataset.
2. Run `scripts/prepare_hf_release.py` to create scorer-ready reference files.
3. Generate or download model prediction JSONL files.
4. If needed, normalize raw model outputs with `scripts/postprocess_predictions.py`.
5. Run `scripts/evaluate_all.py`.
6. Use the generated `results/all_metrics.json` to populate result tables.

The scorer itself has no external runtime dependencies beyond Python.
