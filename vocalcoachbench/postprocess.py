from __future__ import annotations

import re
from typing import Any

from .metrics import normalize_winner, parse_json_object
from .taxonomy import CATEGORIES, normalize_category, normalize_category_list


def _response_text(row: dict[str, Any]) -> str:
    return str(row.get("response_text") or row.get("text") or row.get("raw_output") or "").strip()


def _parsed_response(row: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_json_object(_response_text(row))
    return parsed or {}


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_score(row: dict[str, Any], parsed: dict[str, Any]) -> float | None:
    for source in (row, parsed):
        for key in ("quality_score_0_5", "score", "quality_score"):
            score = _float_or_none(source.get(key))
            if score is not None:
                return max(0.0, min(5.0, score))

    text = _response_text(row)
    patterns = [
        r"quality_score_0_5[\"']?\s*[:=]\s*([0-5](?:\.\d+)?)",
        r"\bscore\b[\"']?\s*[:=]\s*([0-5](?:\.\d+)?)",
        r"\b([0-5](?:\.\d+)?)\s*/\s*5\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            score = _float_or_none(match.group(1))
            if score is not None:
                return max(0.0, min(5.0, score))
    return None


def _extract_confidence(row: dict[str, Any], parsed: dict[str, Any]) -> float | None:
    for source in (row, parsed):
        for key in ("confidence", "score_confidence"):
            confidence = _float_or_none(source.get(key))
            if confidence is not None:
                return max(0.0, min(1.0, confidence))
    return None


def _extract_categories_from_text(text: str, *, limit: int | None = None) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for category_name in CATEGORIES:
        if re.search(rf"\b{re.escape(category_name)}\b", text, flags=re.IGNORECASE):
            category = normalize_category(category_name)
            if category and category not in seen:
                seen.add(category)
                matches.append(category)
                if limit is not None and len(matches) >= limit:
                    return matches
    for match in re.finditer(r"\b[A-Za-z][A-Za-z_\- ]+\b", text):
        category = normalize_category(match.group(0))
        if category and category not in seen:
            seen.add(category)
            matches.append(category)
            if limit is not None and len(matches) >= limit:
                break
    return matches


def normalize_direct_pairwise_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed = _parsed_response(row)
    winner = normalize_winner(row.get("winner")) or normalize_winner(parsed.get("winner"))
    if winner is None:
        text = _response_text(row)
        first_line = text.splitlines()[0].strip() if text else ""
        winner = normalize_winner(first_line)
    if winner is None:
        text = _response_text(row)
        match = re.search(r"\b(?:winner|better|choice|answer|performance)\b.*?\b(?:Audio\s*)?([AB])\b", text, re.IGNORECASE)
        if match:
            winner = normalize_winner(match.group(1))

    out: dict[str, Any] = {"pair_id": row.get("pair_id")}
    for key in ("audio_a_id", "audio_b_id"):
        if key in row:
            out[key] = row[key]
    if winner is not None:
        out["winner"] = winner
    confidence = _extract_confidence(row, parsed)
    if confidence is not None:
        out["confidence"] = confidence
    if parsed.get("rationale"):
        out["rationale"] = str(parsed["rationale"])
    out["response_text"] = _response_text(row)
    return out


def normalize_top3_score_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed = _parsed_response(row)
    issues = normalize_category_list(row.get("top3_issues") or parsed.get("top3_issues"), limit=3)
    if not issues:
        issues = _extract_categories_from_text(_response_text(row), limit=3)

    out: dict[str, Any] = {"audio_id": row.get("audio_id") or row.get("sample_id")}
    if issues:
        out["top3_issues"] = issues
    score = _extract_score(row, parsed)
    if score is not None:
        out["quality_score_0_5"] = score
    confidence = _extract_confidence(row, parsed)
    if confidence is not None:
        out["score_confidence"] = confidence
    if parsed.get("score_rationale"):
        out["score_rationale"] = str(parsed["score_rationale"])
    out["response_text"] = _response_text(row)
    return out


def normalize_segment_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed = _parsed_response(row)
    category = normalize_category(row.get("category") or row.get("prediction") or parsed.get("category"))
    if category is None:
        categories = _extract_categories_from_text(_response_text(row), limit=1)
        category = categories[0] if categories else None

    out: dict[str, Any] = {"sample_id": row.get("sample_id") or row.get("id")}
    if category is not None:
        out["category"] = category
    confidence = _extract_confidence(row, parsed)
    if confidence is not None:
        out["confidence"] = confidence
    if parsed.get("rationale"):
        out["rationale"] = str(parsed["rationale"])
    out["response_text"] = _response_text(row)
    return out


def normalize_rows(task: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if task == "direct_pairwise":
        return [normalize_direct_pairwise_row(row) for row in rows]
    if task == "top3_score":
        return [normalize_top3_score_row(row) for row in rows]
    if task == "segment":
        return [normalize_segment_row(row) for row in rows]
    raise ValueError(f"Unsupported task: {task}. Expected one of: direct_pairwise, top3_score, segment.")


def category_vocabulary() -> list[str]:
    return list(CATEGORIES)
