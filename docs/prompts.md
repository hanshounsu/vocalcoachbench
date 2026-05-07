# Prompts

`prompts/` contains the v5 prompt templates used for the benchmark tasks.

- `claim_objective_claims_v5.txt`: structured diagnosis, correction, and strength claims. The raw v5 output key for correction claims is `prescription_claims`.
- `objective_top3_score_v5.txt`: top-3 issue prediction and scalar quality score.
- `structured_segment_v5.txt`: segment-level issue classification.
- `direct_pairwise_triplet_v5.txt`: direct A/B comparison used for main triplet ranking.
- `simple_*.txt`: simple natural-language baselines.

For direct pairwise triplet ranking, the model must receive two labeled audio
inputs corresponding to Audio A and Audio B in the pair manifest. The text
prompt alone is not sufficient if the serving stack does not preserve audio
input order or labels.
