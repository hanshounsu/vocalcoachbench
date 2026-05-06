# VocalCoachBench

Evaluation toolkit for **VocalCoachBench: Benchmarking Audio-Language Models on
Expert Feedback for Singing**.

VocalCoachBench is a benchmark for evaluating audio-language models on expert
vocal coaching feedback for singing. This repository contains the scorer,
prompt templates, post-processing utilities, and data preparation scripts.

- **Direct pairwise triplet ranking**: compare same-song performances through
  three A/B audio comparisons per triplet.
- **Top-3 issue prediction**: rank the three most salient vocal issue categories.
- **Segment-conditioned issue classification**: identify the main issue in an
  expert-consensus vocal segment.
- **Open-ended coaching prompts**: structured diagnosis and correction claim
  templates for hosted or provider-specific judge pipelines.

Full dataset files are hosted separately. Small files under `examples/` are
included only for smoke tests.

## What You Need

This repository is a scorer, not a model inference server. To evaluate a model
on a fresh machine, you need:

- this repository,
- the released benchmark reference files, such as `triplet_pairs.jsonl`,
  `top3_references.jsonl`, and `segment_references.jsonl`,
- your model prediction JSONL files in the formats below.

The scorer does not listen to audio files or call model APIs. Audio files are
needed when generating model predictions, but the metric commands consume only
the released reference JSONL files and prediction JSONL files.

## File Roles

VocalCoachBench uses three different kinds of JSONL files:

| File type | Typical path | Purpose | Used by scorer? |
| --- | --- | --- | --- |
| Reference files | `data/triplet_pairs.jsonl`, `data/top3_references.jsonl` | Released benchmark labels/manifests | Yes |
| Raw model outputs | `raw_outputs/my_model_*.jsonl` | Optional archive of unprocessed LALM text responses | No |
| Prediction files | `predictions/my_model_*.jsonl` | Canonical, post-processed model outputs | Yes |

The evaluator scores **prediction files**, not raw model text. If your inference
code already writes canonical prediction JSONL, no extra normalization step is
needed. If it stores raw LALM text in `response_text`, run
`scripts/postprocess_predictions.py` first.

## Installation

On a fresh Ubuntu server:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv
```

Clone this repository and install the scorer:

```bash
git clone <repository-url> vocalcoachbench
cd vocalcoachbench
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Quick Start

Run the examples:

```bash
vocalcoachbench evaluate-triplet \
  --pairs examples/triplet_pairs.jsonl \
  --predictions examples/direct_pairwise_predictions.jsonl

vocalcoachbench evaluate-top3 \
  --references examples/top3_references.jsonl \
  --predictions examples/top3_predictions.jsonl

vocalcoachbench evaluate-score-triplet \
  --pairs examples/triplet_pairs.jsonl \
  --scores examples/score_predictions.jsonl

vocalcoachbench evaluate-segment \
  --references examples/segment_references.jsonl \
  --predictions examples/segment_predictions.jsonl
```

Each command prints a JSON summary. Add `--out path/to/summary.json` to save it.

You can also evaluate every available task in a directory at once:

```bash
python scripts/evaluate_all.py \
  --data-dir examples \
  --predictions-dir examples \
  --output-dir outputs/example_metrics
```

## Prediction Formats

### Direct Pairwise Triplet Ranking

For each pair in the released pair manifest, submit one row:

```json
{"pair_id": "p001_ab", "winner": "A", "confidence": 0.82, "rationale": "..."}
```

The direct pairwise prompt asks models to return JSON with `winner`,
`confidence`, and `rationale`. The required scoring field is `winner`.

### Top-3 Issue Prediction

```json
{"audio_id": "a001", "top3_issues": ["PITCH", "BREATH", "PHONATION"]}
```

### Segment Classification

```json
{"sample_id": "s001", "category": "PHONATION"}
```

Allowed issue categories:

```text
PITCH, RHYTHM, DICTION, BREATH, PHONATION, TECHNIQUE, EXPRESSION
```

## Repository Layout

```text
vocalcoachbench/      Python package and metric implementations
prompts/              Prompt templates used in the paper
examples/             Tiny runnable examples
docs/                 Data and submission format docs
scripts/              Convenience scripts
```

## Dataset

The full benchmark audio and annotation files are distributed separately, for
example through a Hugging Face dataset release. After downloading the dataset,
prepare scorer-ready reference files with:

```bash
python scripts/prepare_hf_release.py \
  --hf-root /path/to/downloaded_hf_release \
  --out-dir data
```

The script accepts either the parent download directory or the
`VocalCoachBench_annotations/` directory. It writes the JSONL files consumed by
the scorer under `data/` and, by default, links `data/audio` to the downloaded
release audio directory. The `data/` directory is ignored by git so that the
evaluator repository remains code-only. See `docs/huggingface_dataset.md` for
the expected release layout and quick checks.

For triplet ranking, the HF release preserves all raw annotations and marks the
benchmark subset explicitly. `scripts/prepare_hf_release.py` uses
`annotations/triplet_ranking_eval_units.jsonl` and keeps rows where
`benchmark_included == true`.

Expected scorer-ready layout after preparation:

```text
data/
  audio_metadata.jsonl
  triplet_pairs.jsonl
  top3_references.jsonl
  segment_references.jsonl
  segment_metadata.jsonl
  audio/
predictions/
  my_model_direct_pairwise.jsonl
  my_model_top3.jsonl
  my_model_scores.jsonl
  my_model_segment.jsonl
```

Run the full benchmark scorers:

```bash
vocalcoachbench evaluate-triplet \
  --pairs data/triplet_pairs.jsonl \
  --predictions predictions/my_model_direct_pairwise.jsonl \
  --out results/my_model_triplet.json

vocalcoachbench evaluate-top3 \
  --references data/top3_references.jsonl \
  --predictions predictions/my_model_top3.jsonl \
  --out results/my_model_top3.json

vocalcoachbench evaluate-score-triplet \
  --pairs data/triplet_pairs.jsonl \
  --scores predictions/my_model_scores.jsonl \
  --out results/my_model_score_triplet.json

vocalcoachbench evaluate-segment \
  --references data/segment_references.jsonl \
  --predictions predictions/my_model_segment.jsonl \
  --out results/my_model_segment.json
```

Or run all available tasks at once:

```bash
python scripts/evaluate_all.py \
  --data-dir data \
  --predictions-dir predictions \
  --output-dir results
```

## Inference Templates

Provider-specific inference code is kept out of the public scorer to avoid API
key handling, private paths, and vendor-specific dependencies. The template
scripts define the expected prediction-file interface:

```bash
python scripts/infer_direct_pairwise_template.py --help
python scripts/infer_single_audio_template.py --help
```

Implement the `call_model(...)` function in a local copy or adapter script for
your model, then evaluate the resulting JSONL files with the scorer.

## Post-Processing

Post-processing is the optional conversion from raw LALM text to canonical
prediction JSONL:

```text
raw_outputs/*.jsonl  ->  scripts/postprocess_predictions.py  ->  predictions/*.jsonl  ->  scorer
```

For example:

```bash
python scripts/postprocess_predictions.py \
  --task top3_score \
  --input examples/raw_top3_score_outputs.jsonl \
  --out outputs/example_top3_score_predictions.jsonl \
  --print-summary
```

The `examples/raw_*_outputs.jsonl` files are small demonstrations of the
normalizer, not released model outputs. The post-processing rules are documented
in `docs/postprocessing.md`.

## Notes

- Main triplet ranking uses **direct pairwise comparison**, not scalar quality
  scores.
- Score-derived triplet ranking is provided as an auxiliary diagnostic through
  `evaluate-score-triplet`.
- Open-ended coaching evaluation requires a judge model; this repo provides the
  prompt templates and schemas, while judge execution depends on the evaluation
  backend.
- See `docs/reproducing_paper_results.md` for the intended separation between
  model inference and deterministic scoring.
