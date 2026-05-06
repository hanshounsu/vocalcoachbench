# Post-Processing Raw Model Outputs

The official metric commands consume **canonical prediction JSONL** files, not
raw LALM text. Post-processing is needed only when an inference script saves the
model's unprocessed text response.

The intended file flow is:

```text
model/API response text
  -> raw_outputs/*.jsonl              # optional archive, not scored directly
  -> scripts/postprocess_predictions.py
  -> predictions/*.jsonl              # canonical scorer input
  -> vocalcoachbench evaluate-*
```

If your inference code already writes canonical prediction rows with fields such
as `winner`, `top3_issues`, `quality_score_0_5`, or `category`, you can skip
this step and run the scorer directly.

## Commands

Normalize raw rows before scoring:

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

## Raw Output Rows, Not Scorer Input

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

## Canonical Prediction Rows, Scorer Input

The post-processed output files are canonical prediction files and can be passed
directly to the scorer:

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
