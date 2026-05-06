# VocalCoachBench

Evaluation toolkit for **VocalCoachBench: Benchmarking Audio-Language Models on
Expert Feedback for Singing**.

VocalCoachBench is a benchmark for evaluating audio-language models on expert
vocal coaching feedback for singing. It separates deterministic structured
targets from open-ended feedback evaluation:

- **Direct pairwise triplet ranking**: compare same-song performances through
  three A/B audio comparisons per triplet.
- **Top-3 issue prediction**: rank the three most salient vocal issue categories.
- **Segment-conditioned issue classification**: identify the main issue in an
  expert-consensus vocal segment.
- **Open-ended coaching evaluation**: judge generated diagnosis and correction
  claims against expert atomic claims.

This repository contains the public evaluation code, prompt templates, and data
format documentation. Full dataset files are hosted separately; small toy files
under `examples/` are included only for smoke tests.

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

Run the toy examples:

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

## Prediction Formats

### Direct Pairwise Triplet Ranking

For each pair in the released pair manifest, submit one row:

```json
{"pair_id": "p001_ab", "winner": "A", "confidence": 0.82, "rationale": "..."}
```

The evaluator also accepts raw model text in `response_text` and normalizes
simple answers such as `A`, `B`, or JSON-like strings containing `winner: "A"`.

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

The full benchmark audio and annotation files are distributed separately. Place
downloaded files under `data/` using the JSONL formats in `docs/data_format.md`.
The `data/` directory is ignored by git so that the evaluator repository remains
code-only.

Expected full-data layout:

```text
data/
  triplet_pairs.jsonl
  top3_references.jsonl
  segment_references.jsonl
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

## Notes

- Main triplet ranking uses **direct pairwise comparison**, not scalar quality
  scores.
- Score-derived triplet ranking is provided as an auxiliary diagnostic through
  `evaluate-score-triplet`.
- Open-ended coaching evaluation requires an LLM judge; this repo provides the
  schemas and prompt templates, while judge execution depends on the model/API
  backend used by the benchmark host.
