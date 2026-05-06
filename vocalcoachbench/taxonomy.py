from __future__ import annotations

CATEGORIES = [
    "PITCH",
    "RHYTHM",
    "DICTION",
    "BREATH",
    "PHONATION",
    "TECHNIQUE",
    "EXPRESSION",
]

CATEGORY_SET = set(CATEGORIES)

PARENT_CATEGORY = {
    "PITCH": "MUSICAL_ACCURACY",
    "RHYTHM": "MUSICAL_ACCURACY",
    "DICTION": "TECHNICAL_PRODUCTION",
    "BREATH": "TECHNICAL_PRODUCTION",
    "PHONATION": "TECHNICAL_PRODUCTION",
    "TECHNIQUE": "TECHNICAL_PRODUCTION",
    "EXPRESSION": "DELIVERY",
}


def normalize_category(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "PITCH_ACCURACY": "PITCH",
        "INTONATION": "PITCH",
        "TIMING": "RHYTHM",
        "ARTICULATION": "DICTION",
        "PRONUNCIATION": "DICTION",
        "RESPIRATION": "BREATH",
        "VOCALIZATION": "PHONATION",
        "TONE": "PHONATION",
        "VOCAL_TECHNIQUE": "TECHNIQUE",
        "MUSICAL_EXPRESSION": "EXPRESSION",
    }
    text = aliases.get(text, text)
    return text if text in CATEGORY_SET else None


def normalize_category_list(values: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        category = normalize_category(value)
        if category is None or category in seen:
            continue
        seen.add(category)
        out.append(category)
        if limit is not None and len(out) >= limit:
            break
    return out


def parentize(categories: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for category in categories:
        parent = PARENT_CATEGORY.get(category)
        if parent and parent not in seen:
            seen.add(parent)
            out.append(parent)
    return out

