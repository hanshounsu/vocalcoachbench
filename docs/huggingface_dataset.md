# Hugging Face Dataset Layout

The full benchmark dataset is distributed separately from this evaluator
repository. After downloading the dataset, place or symlink the released files
under `data/` in the evaluator checkout.

Expected layout:

```text
data/
  audio_metadata.jsonl
  triplet_pairs.jsonl
  top3_references.jsonl
  segment_references.jsonl
  segment_metadata.jsonl
  audio/
    ...
```

Only the reference JSONL files are required for scoring existing prediction
files. Audio files and metadata are required when generating new model
predictions.

## Required Files

`triplet_pairs.jsonl`
: Pair manifest and triplet references for direct pairwise triplet ranking.

`top3_references.jsonl`
: Expert Top-3 issue references.

`segment_references.jsonl`
: Accepted expert labels for segment-conditioned issue classification.

`audio_metadata.jsonl`
: Audio identifiers and paths for single-audio inference.

`segment_metadata.jsonl`
: Segment identifiers and paths for segment inference.

## Quick Checks

Check that the expected files exist:

```bash
ls data/triplet_pairs.jsonl \
   data/top3_references.jsonl \
   data/segment_references.jsonl
```

Inspect the first few rows:

```bash
head -2 data/triplet_pairs.jsonl
head -2 data/top3_references.jsonl
head -2 data/segment_references.jsonl
```

Run a scorer once you have prediction files:

```bash
python scripts/evaluate_all.py \
  --data-dir data \
  --predictions-dir predictions \
  --output-dir results
```

If the dataset is downloaded into another directory, either symlink it:

```bash
ln -s /path/to/downloaded_dataset data
```

or pass the path explicitly:

```bash
python scripts/evaluate_all.py \
  --data-dir /path/to/downloaded_dataset \
  --predictions-dir predictions \
  --output-dir results
```

## Notes

The evaluator repository intentionally does not include the full audio dataset.
The `data/` directory is ignored by git.
