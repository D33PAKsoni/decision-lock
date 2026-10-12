"""Pure weighted scoring. Bigger scores always mean a better fit; range 0–10."""

import math
from numbers import Real
from typing import Any


def _number(value: Any) -> bool:
    try:
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def score_options(options: list[dict], weights: dict[str, float]) -> dict:
    """Rank 2–5 options on 1–6 criteria with nonnegative normalized weights.

    No missing values are filled. A tie keeps input order and is reported explicitly.
    Large weights are scaled before summing to prevent numeric overflow.
    """
    errors: list[str] = []
    missing: list[str] = []
    if not isinstance(options, list) or not 2 <= len(options) <= 5:
        errors.append("Provide 2–5 options.")
    if not isinstance(weights, dict) or not 1 <= len(weights) <= 6:
        errors.append("Provide 1–6 criteria with weights.")
    if errors:
        return {"status": "invalid_input", "errors": errors}
    for key, value in weights.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            errors.append("Criterion names must be non-empty strings without outer whitespace.")
        if not _number(value) or value < 0:
            errors.append("Weights must be finite, nonnegative numbers.")
    if not errors and max(weights.values()) <= 0:
        errors.append("At least one weight must be greater than zero.")
    names: set[str] = set()
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"Option {index + 1} must have a name and scores.")
            continue
        name = option.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 160:
            errors.append(f"Option {index + 1} needs a name of 1–160 characters.")
            continue
        name = name.strip()
        if name.casefold() in names:
            errors.append("Option names must be unique.")
        names.add(name.casefold())
        scores = option.get("scores")
        if not isinstance(scores, dict):
            missing.append(f"scores for {name}")
            continue
        if set(scores) - set(weights):
            errors.append(f"Scores for {name} include criteria without weights.")
        for criterion in weights:
            if criterion not in scores:
                missing.append(f"{criterion} score for {name}")
            elif not _number(scores[criterion]) or not 0 <= scores[criterion] <= 10:
                errors.append(f"Scores for {name} must be finite numbers between 0 and 10.")
    if errors:
        return {"status": "invalid_input", "errors": errors}
    if missing:
        return {"status": "needs_clarification", "missing": missing}
    maximum = max(weights.values())
    scaled = {key: value / maximum for key, value in weights.items()}
    total = math.fsum(scaled.values())
    normalized = {key: value / total for key, value in scaled.items()}
    ranked = []
    for option in options:
        factors = {key: option["scores"][key] * weight for key, weight in normalized.items()}
        ranked.append(
            {
                "name": option["name"].strip(),
                "weighted_score": math.fsum(factors.values()),
                "factor_breakdown": factors,
                "scores": dict(option["scores"]),
            }
        )
    ranked.sort(key=lambda item: item["weighted_score"], reverse=True)
    best = ranked[0]["weighted_score"]
    tied = [
        item["name"]
        for item in ranked
        if math.isclose(item["weighted_score"], best, rel_tol=1e-12, abs_tol=1e-12)
    ]
    return {
        "status": "ok",
        "ranked_options": ranked,
        "normalized_weights": normalized,
        "tied_for_first": tied if len(tied) > 1 else [],
        "note": "Scores express supplied judgments, not probabilities. Higher is better.",
    }
