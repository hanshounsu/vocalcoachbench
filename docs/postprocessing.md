# Post-Processing Raw Model Outputs

The official metric commands consume canonical prediction JSONL files. If a
model returns raw text, normalize it before scoring:

```bash
python scripts/postprocess_predictions.py \
  --task direct_pairwise \
  --input raw_outputs/my_model_direct_pairwise_raw.jsonl \
  --out predictions/my_model_direct_pairwise.jsonl \
  --print-summary

python scripts/postprocess_predictions.py \
  --task top3_score \
  --input raw_outputs/my_model_top3_score_raw.jsonl \
  --out predictions/my_model_top3_score.jsonl \
  --print-summary

python scripts/postprocess_predictions.py \
  --task segment \
  --input raw_outputs/my_model_segment_raw.jsonl \
  --out predictions/my_model_segment.jsonl \
  --print-summary
```

## Raw Output Rows

Raw rows must preserve the benchmark identifier and the model text:

```json
{"pair_id": "triplet_001_ab", "response_text": "{\"winner\":\"A\"}"}
{"audio_id": "audio_001", "response_text": "{\"top3_issues\":[\"PITCH\",\"BREATH\",\"PHONATION\"],\"quality_score_0_5\":3.2}"}
{"sample_id": "segment_001", "response_text": "{\"category\":\"PITCH\"}"}
```

The normalizer first parses JSON objects, then applies conservative fallback
rules for simple text answers. It maps category aliases to the seven benchmark
categories and clips confidence to `[0, 1]` and quality scores to `[0, 5]`.

The files named `examples/example_raw_*_outputs.jsonl` are toy demonstrations of
these parsing rules. They are not model prediction files from the paper.

The direct pairwise prompt asks for a JSON object with `winner`, `confidence`,
and `rationale`; a typical raw row therefore contains that JSON string in
`response_text`. The simple-text fallback exists only to handle occasional
non-JSON model outputs without changing the scoring interface.

## Canonical Prediction Rows

The output files can be passed directly to the scorer:

```bash
vocalcoachbench evaluate-triplet \
  --pairs data/triplet_pairs.jsonl \
  --predictions predictions/my_model_direct_pairwise.jsonl

vocalcoachbench evaluate-top3 \
  --references data/top3_references.jsonl \
  --predictions predictions/my_model_top3_score.jsonl

vocalcoachbench evaluate-score-triplet \
  --pairs data/triplet_pairs.jsonl \
  --scores predictions/my_model_top3_score.jsonl

vocalcoachbench evaluate-segment \
  --references data/segment_references.jsonl \
  --predictions predictions/my_model_segment.jsonl
```

For maximum reproducibility, archive both the raw output JSONL files and the
post-processed prediction JSONL files used for scoring.
