# Data Format

All public files use UTF-8 JSONL: one JSON object per line.

The scorer consumes reference JSONL files and prediction JSONL files. It does
not run model inference. Audio files are used upstream to generate predictions;
the metric commands themselves do not load audio.

`raw_outputs/*.jsonl` files, when used, are optional logs of unprocessed model
text. They are not scored directly. Convert them to canonical prediction JSONL
with `scripts/postprocess_predictions.py`, or write canonical prediction JSONL
directly from your inference code.

## Audio Metadata

Audio metadata should identify the audio without assuming a fixed storage
backend.

```json
{"audio_id": "audio_001", "path": "audio/audio_001.wav", "song_id": "song_12"}
```

`path` can be local, relative to the benchmark root, or a signed URL in hosted
evaluation.

When using the Hugging Face dataset release, create these scorer-ready
metadata/reference files with `scripts/prepare_hf_release.py`. See
`docs/huggingface_dataset.md` for the expected downloaded layout.

## Direct Pairwise Triplet Ranking

The benchmark releases a pair manifest. Each triplet produces three pair rows:
AB, AC, and BC. Models submit a winner for each row.

Manifest row:

```json
{
  "pair_id": "triplet_001_ab",
  "triplet_id": "triplet_001",
  "triplet_instance_id": "triplet_001_refset",
  "audio_a_id": "audio_001_a",
  "audio_b_id": "audio_001_b",
  "reference_orders": [
    ["audio_001_a", "audio_001_b", "audio_001_c"],
    ["audio_001_a", "audio_001_c", "audio_001_b"]
  ]
}
```

Prediction row:

```json
{"pair_id": "triplet_001_ab", "winner": "A", "confidence": 0.82}
```

The evaluator computes pairwise accuracy, Kendall's tau, exact ranking accuracy,
cycle-or-tie rate, and missing-pair rate. If multiple expert reference orders
exist for a triplet, the model is compared against each reference order and the
scores are averaged.

The main triplet set excludes heavily conflicting triplet references. It keeps
triplets whose expert pair directions agree on at least two of the three implied
pairwise preferences.
In the Hugging Face release this policy is already encoded in
`annotations/triplet_ranking_eval_units.jsonl` and
`metadata/triplet_ranking_policy.json`; `scripts/prepare_hf_release.py` uses
those fields directly when preparing `triplet_pairs.jsonl`.

## Auxiliary Score-Derived Triplet Ranking

The auxiliary score-derived metric uses the same triplet manifest, but ranks
the three audios by single-audio scalar quality predictions.

Score prediction row:

```json
{"audio_id": "audio_001_a", "quality_score_0_5": 4.1}
```

This is not the main triplet-ranking protocol.

## Top-3 Issue Prediction

Reference row:

```json
{"audio_id": "audio_001", "references": [["PITCH", "BREATH", "PHONATION"]]}
```

Prediction row:

```json
{"audio_id": "audio_001", "top3_issues": ["PITCH", "PHONATION", "DICTION"]}
```

Metrics are averaged over reference lists for the same audio.

## Segment Classification

Reference row:

```json
{"sample_id": "segment_001", "labels": ["PITCH", "PHONATION"]}
```

Prediction row:

```json
{"sample_id": "segment_001", "category": "PITCH"}
```

The segment metric is exact category match against any accepted expert label.

## Categories

The seven issue categories are:

```text
PITCH, RHYTHM, DICTION, BREATH, PHONATION, TECHNIQUE, EXPRESSION
```
