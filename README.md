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

## Installation

```bash
git clone https://github.com/<ORG>/VocalCoachBench.git
cd VocalCoachBench
pip install -e .
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

## Notes

- Main triplet ranking uses **direct pairwise comparison**, not scalar quality
  scores.
- Score-derived triplet ranking is provided as an auxiliary diagnostic through
  `evaluate-score-triplet`.
- Open-ended coaching evaluation requires an LLM judge; this repo provides the
  schemas and prompt templates, while judge execution depends on the model/API
  backend used by the benchmark host.
