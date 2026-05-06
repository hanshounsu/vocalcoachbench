from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from typing import Any

from .io import mean
from .taxonomy import normalize_category, normalize_category_list, parentize


def normalize_winner(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"A", "AUDIO A"}:
        return "A"
    if text in {"B", "AUDIO B"}:
        return "B"
    return None


def parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def extract_winner(row: dict[str, Any]) -> tuple[str | None, str]:
    direct = normalize_winner(row.get("winner"))
    if direct:
        return direct, "winner_field"

    text = str(row.get("response_text") or row.get("text") or "").strip()
    parsed = parse_json_object(text)
    winner = normalize_winner((parsed or {}).get("winner"))
    if winner:
        return winner, "json"

    first_line = text.splitlines()[0].strip() if text else ""
    winner = normalize_winner(first_line)
    if winner:
        return winner, "first_line"

    match = re.search(r'["\']?winner["\']?\s*[:=]\s*["\']?(A|B|Audio A|Audio B)["\']?', text, flags=re.IGNORECASE)
    if match:
        winner = normalize_winner(match.group(1))
        if winner:
            return winner, "winner_regex"

    return None, "none"


def reference_prefers(order: list[str], left: str, right: str) -> str:
    return left if order.index(left) < order.index(right) else right


def pairwise_score_against_reference(
    model_pair_winners: dict[tuple[str, str], str | None],
    reference_order: list[str],
) -> tuple[float, float]:
    hits: list[float] = []
    signs: list[int] = []
    for left_index in range(len(reference_order)):
        for right_index in range(left_index + 1, len(reference_order)):
            better = reference_order[left_index]
            worse = reference_order[right_index]
            key = tuple(sorted((better, worse)))
            winner = model_pair_winners.get(key)
            if winner is None:
                hits.append(0.0)
                signs.append(0)
            elif winner == better:
                hits.append(1.0)
                signs.append(1)
            else:
                hits.append(0.0)
                signs.append(-1)
    return float(mean(hits) or 0.0), float(mean(signs) or 0.0)


def reconstruct_order(audio_ids: list[str], model_pair_winners: dict[tuple[str, str], str | None]) -> tuple[list[str], bool, bool]:
    wins = {audio_id: 0 for audio_id in audio_ids}
    missing = False
    for left_index in range(len(audio_ids)):
        for right_index in range(left_index + 1, len(audio_ids)):
            key = tuple(sorted((audio_ids[left_index], audio_ids[right_index])))
            winner = model_pair_winners.get(key)
            if winner is None:
                missing = True
                continue
            wins[winner] += 1
    has_cycle_or_tie = len(set(wins.values())) < len(wins)
    order = sorted(audio_ids, key=lambda audio_id: (-wins[audio_id], audio_id))
    return order, has_cycle_or_tie, missing


def evaluate_direct_triplets(
    pair_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    predictions_by_id: dict[str, dict[str, Any]] = {}
    for row in prediction_rows:
        pair_id = str(row.get("pair_id") or "")
        if pair_id:
            predictions_by_id[pair_id] = row

    rows_by_triplet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pair_rows:
        key = str(pair.get("triplet_instance_id") or pair.get("triplet_id"))
        rows_by_triplet[key].append(pair)

    triplet_metrics: list[dict[str, Any]] = []
    parsed_pairs = 0
    total_pairs = 0
    for triplet_key, triplet_pairs in sorted(rows_by_triplet.items()):
        audio_ids = sorted(
            {str(row.get("audio_a_id")) for row in triplet_pairs}
            | {str(row.get("audio_b_id")) for row in triplet_pairs}
        )
        if len(audio_ids) != 3:
            continue

        model_pair_winners: dict[tuple[str, str], str | None] = {}
        pair_details: list[dict[str, Any]] = []
        for pair in triplet_pairs:
            total_pairs += 1
            prediction = predictions_by_id.get(str(pair.get("pair_id")), {})
            winner, parse_mode = extract_winner(prediction)
            pred_audio_id = None
            if winner == "A":
                pred_audio_id = str(pair.get("audio_a_id"))
            elif winner == "B":
                pred_audio_id = str(pair.get("audio_b_id"))
            if pred_audio_id:
                parsed_pairs += 1
            key = tuple(sorted((str(pair.get("audio_a_id")), str(pair.get("audio_b_id")))))
            model_pair_winners[key] = pred_audio_id
            pair_details.append(
                {
                    "pair_id": pair.get("pair_id"),
                    "audio_a_id": pair.get("audio_a_id"),
                    "audio_b_id": pair.get("audio_b_id"),
                    "pred_winner": winner,
                    "pred_winner_audio_id": pred_audio_id,
                    "winner_parse_mode": parse_mode,
                }
            )

        first = triplet_pairs[0]
        reference_orders = [
            [str(item) for item in order]
            for order in (first.get("reference_orders") or [first.get("human_order") or []])
            if order
        ]
        model_order, has_cycle_or_tie, has_missing_pair = reconstruct_order(audio_ids, model_pair_winners)
        pair_scores: list[float] = []
        tau_scores: list[float] = []
        exact_scores: list[float] = []
        for reference_order in reference_orders:
            pair_acc, tau = pairwise_score_against_reference(model_pair_winners, reference_order)
            pair_scores.append(pair_acc)
            tau_scores.append(tau)
            exact_scores.append(float((not has_missing_pair) and (not has_cycle_or_tie) and model_order == reference_order))

        triplet_metrics.append(
            {
                "triplet_instance_id": triplet_key,
                "triplet_id": first.get("triplet_id"),
                "audio_ids": audio_ids,
                "reference_orders": reference_orders,
                "model_order": model_order,
                "has_cycle_or_tie": has_cycle_or_tie,
                "has_missing_pair": has_missing_pair,
                "direct_pairwise_accuracy": mean(pair_scores),
                "direct_kendall_tau": mean(tau_scores),
                "direct_exact_accuracy": mean(exact_scores),
                "pair_details": pair_details,
            }
        )

    summary = {
        "triplet_n": len(triplet_metrics),
        "pair_n": total_pairs,
        "parsed_pair_rate": (parsed_pairs / total_pairs) if total_pairs else None,
        "direct_pairwise_accuracy": mean([row.get("direct_pairwise_accuracy") for row in triplet_metrics]),
        "direct_kendall_tau": mean([row.get("direct_kendall_tau") for row in triplet_metrics]),
        "direct_exact_accuracy": mean([row.get("direct_exact_accuracy") for row in triplet_metrics]),
        "cycle_or_tie_rate": mean([float(row.get("has_cycle_or_tie")) for row in triplet_metrics]),
        "missing_pair_rate": mean([float(row.get("has_missing_pair")) for row in triplet_metrics]),
    }
    return summary, triplet_metrics


def _extract_score(row: dict[str, Any]) -> float | None:
    for key in ("quality_score_0_5", "score", "quality_score"):
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    text = str(row.get("response_text") or row.get("text") or "").strip()
    parsed = parse_json_object(text)
    if parsed:
        return _extract_score(parsed)
    try:
        return float(text)
    except ValueError:
        return None


def evaluate_score_triplets(
    pair_rows: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scores_by_audio: dict[str, float] = {}
    for row in score_rows:
        audio_id = str(row.get("audio_id") or row.get("sample_id") or "")
        score = _extract_score(row)
        if audio_id and score is not None:
            scores_by_audio[audio_id] = score

    rows_by_triplet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pair_rows:
        key = str(pair.get("triplet_instance_id") or pair.get("triplet_id"))
        rows_by_triplet[key].append(pair)

    triplet_metrics: list[dict[str, Any]] = []
    for triplet_key, triplet_pairs in sorted(rows_by_triplet.items()):
        audio_ids = sorted(
            {str(row.get("audio_a_id")) for row in triplet_pairs}
            | {str(row.get("audio_b_id")) for row in triplet_pairs}
        )
        if len(audio_ids) != 3:
            continue

        available_scores = {audio_id: scores_by_audio.get(audio_id) for audio_id in audio_ids}
        has_missing_score = any(score is None for score in available_scores.values())
        has_score_tie = len({score for score in available_scores.values() if score is not None}) < len(
            [score for score in available_scores.values() if score is not None]
        )
        model_order = sorted(
            audio_ids,
            key=lambda audio_id: (
                -(available_scores[audio_id] if available_scores[audio_id] is not None else float("-inf")),
                audio_id,
            ),
        )

        first = triplet_pairs[0]
        reference_orders = [
            [str(item) for item in order]
            for order in (first.get("reference_orders") or [first.get("human_order") or []])
            if order
        ]

        pair_scores: list[float] = []
        tau_scores: list[float] = []
        exact_scores: list[float] = []
        for reference_order in reference_orders:
            hits: list[float] = []
            signs: list[int] = []
            for left_index in range(len(reference_order)):
                for right_index in range(left_index + 1, len(reference_order)):
                    better = reference_order[left_index]
                    worse = reference_order[right_index]
                    better_score = available_scores.get(better)
                    worse_score = available_scores.get(worse)
                    if better_score is None or worse_score is None or better_score == worse_score:
                        hits.append(0.0)
                        signs.append(0)
                    elif better_score > worse_score:
                        hits.append(1.0)
                        signs.append(1)
                    else:
                        hits.append(0.0)
                        signs.append(-1)
            pair_scores.append(float(mean(hits) or 0.0))
            tau_scores.append(float(mean(signs) or 0.0))
            exact_scores.append(float((not has_missing_score) and (not has_score_tie) and model_order == reference_order))

        triplet_metrics.append(
            {
                "triplet_instance_id": triplet_key,
                "triplet_id": first.get("triplet_id"),
                "audio_ids": audio_ids,
                "reference_orders": reference_orders,
                "scores": available_scores,
                "model_order": model_order,
                "has_score_tie": has_score_tie,
                "has_missing_score": has_missing_score,
                "score_pairwise_accuracy": mean(pair_scores),
                "score_kendall_tau": mean(tau_scores),
                "score_exact_accuracy": mean(exact_scores),
            }
        )

    summary = {
        "triplet_n": len(triplet_metrics),
        "score_pairwise_accuracy": mean([row.get("score_pairwise_accuracy") for row in triplet_metrics]),
        "score_kendall_tau": mean([row.get("score_kendall_tau") for row in triplet_metrics]),
        "score_exact_accuracy": mean([row.get("score_exact_accuracy") for row in triplet_metrics]),
        "score_tie_rate": mean([float(row.get("has_score_tie")) for row in triplet_metrics]),
        "missing_score_rate": mean([float(row.get("has_missing_score")) for row in triplet_metrics]),
    }
    return summary, triplet_metrics


def f1_at_3(pred: list[str], ref: list[str]) -> float:
    if not pred or not ref:
        return 0.0
    return len(set(pred[:3]) & set(ref[:3])) / 3.0


def top1_accuracy(pred: list[str], ref: list[str]) -> float:
    return float(bool(pred and ref and pred[0] == ref[0]))


def ndcg_at_3(pred: list[str], ref: list[str]) -> float:
    ref_set = set(ref[:3])
    dcg = 0.0
    for index, category in enumerate(pred[:3]):
        if category in ref_set:
            dcg += 1.0 / math.log2(index + 2)
    ideal_hits = min(3, len(ref_set))
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def _top3_refs_by_audio(reference_rows: list[dict[str, Any]]) -> dict[str, list[list[str]]]:
    refs: dict[str, list[list[str]]] = defaultdict(list)
    for row in reference_rows:
        audio_id = str(row.get("audio_id") or row.get("sample_id") or "")
        if not audio_id:
            continue
        if isinstance(row.get("references"), list):
            for ref in row["references"]:
                clean = normalize_category_list(ref, limit=3)
                if clean:
                    refs[audio_id].append(clean)
        else:
            clean = normalize_category_list(row.get("top3_issues") or row.get("labels"), limit=3)
            if clean:
                refs[audio_id].append(clean)
    return refs


def evaluate_top3(reference_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    refs_by_audio = _top3_refs_by_audio(reference_rows)
    preds_by_audio = {
        str(row.get("audio_id") or row.get("sample_id")): normalize_category_list(row.get("top3_issues") or row.get("prediction"), limit=3)
        for row in prediction_rows
    }
    metrics: list[dict[str, Any]] = []
    for audio_id, refs in sorted(refs_by_audio.items()):
        pred = preds_by_audio.get(audio_id, [])
        per_ref = []
        for ref in refs:
            per_ref.append(
                {
                    "f1_at_3": f1_at_3(pred, ref),
                    "top1": top1_accuracy(pred, ref),
                    "ndcg_at_3": ndcg_at_3(pred, ref),
                    "parent_f1": f1_at_3(parentize(pred), parentize(ref)),
                }
            )
        metrics.append(
            {
                "audio_id": audio_id,
                "prediction": pred,
                "reference_count": len(refs),
                "f1_at_3": mean([row["f1_at_3"] for row in per_ref]),
                "top1": mean([row["top1"] for row in per_ref]),
                "ndcg_at_3": mean([row["ndcg_at_3"] for row in per_ref]),
                "parent_f1": mean([row["parent_f1"] for row in per_ref]),
            }
        )
    summary = {
        "audio_n": len(metrics),
        "f1_at_3": mean([row.get("f1_at_3") for row in metrics]),
        "top1": mean([row.get("top1") for row in metrics]),
        "ndcg_at_3": mean([row.get("ndcg_at_3") for row in metrics]),
        "parent_f1": mean([row.get("parent_f1") for row in metrics]),
    }
    return summary, metrics


def evaluate_segment(reference_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    preds_by_id = {
        str(row.get("sample_id") or row.get("id")): normalize_category(row.get("category") or row.get("prediction"))
        for row in prediction_rows
    }
    metrics: list[dict[str, Any]] = []
    for row in reference_rows:
        sample_id = str(row.get("sample_id") or row.get("id") or "")
        labels = normalize_category_list(row.get("labels") or row.get("category_intersection") or row.get("categories"))
        pred = preds_by_id.get(sample_id)
        correct = float(pred in labels) if pred and labels else 0.0
        metrics.append(
            {
                "sample_id": sample_id,
                "prediction": pred,
                "labels": labels,
                "match": correct,
            }
        )
    summary = {
        "segment_n": len(metrics),
        "match": mean([row.get("match") for row in metrics]),
    }
    return summary, metrics
