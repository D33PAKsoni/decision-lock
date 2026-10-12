import math

import pytest

from decision_lock.scoring import score_options


def options():
    return [
        {
            "name": "Study AWS",
            "scores": {"urgency": 9, "importance": 8, "effort_fit": 8, "reversibility": 7},
        },
        {
            "name": "Side project",
            "scores": {"urgency": 5, "importance": 7, "effort_fit": 6, "reversibility": 8},
        },
    ]


WEIGHTS = {"urgency": 0.4, "importance": 0.3, "effort_fit": 0.2, "reversibility": 0.1}


def test_example_arithmetic_is_83_not_the_document_typo_82():
    result = score_options(options(), WEIGHTS)
    assert result["status"] == "ok"
    assert result["ranked_options"][0]["name"] == "Study AWS"
    assert result["ranked_options"][0]["weighted_score"] == pytest.approx(8.3)
    assert result["ranked_options"][1]["weighted_score"] == pytest.approx(6.1)
    assert sum(result["ranked_options"][0]["factor_breakdown"].values()) == pytest.approx(8.3)


@pytest.mark.parametrize("scale", [2, 0.1, 1e300])
def test_weight_scale_invariance(scale):
    result = score_options(options(), {k: v * scale for k, v in WEIGHTS.items()})
    assert result["normalized_weights"] == pytest.approx(WEIGHTS)
    assert result["ranked_options"][0]["weighted_score"] == pytest.approx(8.3)


@pytest.mark.parametrize("value", [-1, math.nan, math.inf, -math.inf, True, "1", None])
def test_invalid_weight_is_structured(value):
    weights = dict(WEIGHTS, urgency=value)
    assert score_options(options(), weights)["status"] == "invalid_input"


@pytest.mark.parametrize("value", [-0.1, 10.1, math.nan, math.inf, True, "9", None])
def test_invalid_score_is_structured(value):
    items = options()
    items[0]["scores"]["urgency"] = value
    assert score_options(items, WEIGHTS)["status"] == "invalid_input"


def test_missing_scores_are_named_and_never_imputed():
    items = options()
    del items[1]["scores"]["urgency"]
    result = score_options(items, WEIGHTS)
    assert result == {
        "status": "needs_clarification",
        "missing": ["urgency score for Side project"],
    }
    assert "urgency" not in items[1]["scores"]


def test_missing_entire_scores():
    assert score_options([{"name": "A"}, {"name": "B"}], {"fit": 1}) == {
        "status": "needs_clarification",
        "missing": ["scores for A", "scores for B"],
    }


@pytest.mark.parametrize(
    "items,weights",
    [
        ([], {"fit": 1}),
        ([{"name": "A"}], {"fit": 1}),
        ([{"name": "A"}] * 6, {"fit": 1}),
        (None, {"fit": 1}),
        (options(), {}),
        (options(), {str(i): 1 for i in range(7)}),
        (options(), {k: 0 for k in WEIGHTS}),
        (options(), []),
        (
            [{"name": "Same", "scores": {"fit": 2}}, {"name": "same", "scores": {"fit": 3}}],
            {"fit": 1},
        ),
        ([None, None], {"fit": 1}),
        (options(), {" fit ": 1}),
    ],
)
def test_shape_limits_and_duplicate_names(items, weights):
    assert score_options(items, weights)["status"] == "invalid_input"


def test_ties_preserve_order_and_report_no_false_winner():
    result = score_options(
        [
            {"name": "B", "scores": {"fit": 5}},
            {"name": "A", "scores": {"fit": 5}},
        ],
        {"fit": 1},
    )
    assert result["tied_for_first"] == ["B", "A"]
    assert [r["name"] for r in result["ranked_options"]] == ["B", "A"]


def test_zero_weight_still_requires_explicit_score():
    assert (
        score_options(
            [
                {"name": "A", "scores": {"fit": 10}},
                {"name": "B", "scores": {"fit": 0}},
            ],
            {"fit": 1, "reversibility": 0},
        )["status"]
        == "needs_clarification"
    )


def test_unweighted_extra_criterion_is_rejected():
    assert score_options(options(), {"urgency": 1})["status"] == "invalid_input"


def test_oversized_integer_is_rejected_without_arithmetic_crash():
    assert score_options(options(), dict(WEIGHTS, urgency=10**1000))["status"] == "invalid_input"
