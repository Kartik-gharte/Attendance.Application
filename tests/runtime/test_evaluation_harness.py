"""Tests for the evaluation harness.

The tests verify the machinery with synthetic inputs. They do not assert
any accuracy figure, because no consented dataset is available and any
such number would be fabricated.
"""

import json

import pytest

from app.evaluation.harness import (
    Attempt,
    AttemptResult,
    Dataset,
    EvaluationError,
    build_report,
    compute_equal_error_rate,
    compute_metrics,
    compute_roc,
    wilson_interval,
    write_report,
)


def make_result(
    attempt_id,
    kind,
    similarity,
    threshold=0.40,
    liveness_detected=None,
    liveness_expected=False,
):
    matched = similarity >= threshold if similarity is not None else False

    return AttemptResult(
        id=attempt_id,
        kind=kind,
        genuine_identity="SUBJ-A" if kind == "genuine" else "SUBJ-A",
        claimed_identity="SUBJ-A" if kind == "genuine" else "SUBJ-B",
        similarity=similarity,
        threshold=threshold,
        matched=matched,
        correct=matched if kind == "genuine" else not matched,
        liveness_detected=liveness_detected,
        liveness_expected=liveness_expected,
    )


# =========================================================
# DATASET DESCRIPTION
# =========================================================


def test_dataset_loads_from_a_file(tmp_path):
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text(
        json.dumps(
            {
                "version": 1,
                "attempts": [
                    {
                        "id": "genuine-1",
                        "image": "a.jpg",
                        "genuine_identity": "SUBJ-A",
                        "claimed_identity": "SUBJ-A",
                        "kind": "genuine",
                    },
                    {
                        "id": "impostor-1",
                        "image": "b.jpg",
                        "genuine_identity": "SUBJ-A",
                        "claimed_identity": "SUBJ-B",
                        "kind": "impostor",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    dataset = Dataset.load(dataset_file)

    assert dataset.version == 1
    assert len(dataset.attempts) == 2
    assert dataset.attempts[0].kind == "genuine"


def test_dataset_rejects_a_missing_file(tmp_path):
    with pytest.raises(EvaluationError):
        Dataset.load(tmp_path / "nope.json")


def test_dataset_rejects_invalid_json(tmp_path):
    dataset_file = tmp_path / "dataset.json"
    dataset_file.write_text("{not json", encoding="utf-8")

    with pytest.raises(EvaluationError):
        Dataset.load(dataset_file)


def test_dataset_rejects_a_missing_field():
    with pytest.raises(EvaluationError):
        Dataset.from_dict(
            {
                "attempts": [
                    {
                        "id": "a",
                        "image": "a.jpg",
                        "genuine_identity": "A",
                        "kind": "genuine",
                    }
                ]
            }
        )


def test_dataset_rejects_an_unknown_kind():
    with pytest.raises(EvaluationError):
        Dataset.from_dict(
            {
                "attempts": [
                    {
                        "id": "a",
                        "image": "a.jpg",
                        "genuine_identity": "A",
                        "claimed_identity": "A",
                        "kind": "something-else",
                    }
                ]
            }
        )


# =========================================================
# DATASET VALIDATION
# =========================================================


def build_dataset(attempts):
    return Dataset(version=1, attempts=attempts)


def test_valid_dataset_reports_no_problems():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    assert dataset.validate() == []


def test_validation_rejects_an_empty_dataset():
    dataset = build_dataset([])

    problems = dataset.validate()

    assert any("no attempts" in problem for problem in problems)


def test_validation_requires_genuine_attempts():
    dataset = build_dataset(
        [
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
            Attempt("i2", "c.jpg", "A", "C", "impostor"),
        ]
    )

    problems = dataset.validate()

    assert any("genuine" in problem for problem in problems)


def test_validation_requires_impostor_attempts():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("g2", "a2.jpg", "A", "A", "genuine"),
        ]
    )

    problems = dataset.validate()

    assert any("impostor" in problem for problem in problems)


def test_validation_rejects_duplicate_identifiers():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    problems = dataset.validate()

    assert any("Duplicate" in problem for problem in problems)


def test_validation_rejects_a_mislabelled_genuine_attempt():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "B", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    problems = dataset.validate()

    assert any("marked genuine" in problem for problem in problems)


def test_validation_requires_at_least_two_identities():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    # The impostor attempt uses a second identity, so this dataset is fine.
    assert dataset.validate() == []

    single = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("g2", "a2.jpg", "A", "A", "genuine"),
        ]
    )

    problems = single.validate()

    assert any("two identities" in problem for problem in problems)


# =========================================================
# METRICS
# =========================================================


def test_metrics_report_the_false_accept_and_reject_rates():
    results = [
        make_result("g1", "genuine", 0.90),
        make_result("g2", "genuine", 0.20),
        make_result("i1", "impostor", 0.80),
        make_result("i2", "impostor", 0.10),
    ]

    metrics = compute_metrics(results, threshold=0.40)

    assert metrics["genuine_attempts"] == 2
    assert metrics["impostor_attempts"] == 2
    assert metrics["false_rejects"] == 1
    assert metrics["false_accepts"] == 1
    assert metrics["false_accept_rate"] == 0.5
    assert metrics["false_reject_rate"] == 0.5


def test_metrics_count_the_failed_attempts():
    failed = make_result("g1", "genuine", None)
    failed.error = "RuntimeError: model failure"

    metrics = compute_metrics([failed], threshold=0.40)

    assert metrics["attempts_total"] == 1
    assert metrics["attempts_scored"] == 0
    assert metrics["attempts_failed"] == 1


def test_metrics_report_the_liveness_success_rate():
    results = [
        make_result(
            "g1",
            "genuine",
            0.9,
            liveness_detected=True,
            liveness_expected=True,
        ),
        make_result(
            "g2",
            "genuine",
            0.9,
            liveness_detected=False,
            liveness_expected=True,
        ),
    ]

    metrics = compute_metrics(results, threshold=0.40)

    assert metrics["liveness_attempts"] == 2
    assert metrics["liveness_success_rate"] == 0.5


def test_metrics_report_the_liveness_false_accept_rate():
    results = [
        make_result(
            "i1",
            "impostor",
            0.1,
            liveness_detected=True,
            liveness_expected=False,
        ),
    ]

    metrics = compute_metrics(results, threshold=0.40)

    assert metrics["liveness_false_accept_rate"] == 1.0


def test_roc_reports_the_threshold_points():
    results = [
        make_result("g1", "genuine", 0.90),
        make_result("g2", "genuine", 0.70),
        make_result("i1", "impostor", 0.60),
        make_result("i2", "impostor", 0.30),
    ]

    roc = compute_roc(
        [r for r in results if r.kind == "genuine"],
        [r for r in results if r.kind == "impostor"],
    )

    assert len(roc) == 4

    first = roc[0]

    assert first["threshold"] == 0.90
    assert first["true_accept_rate"] == 0.5
    assert first["false_accept_rate"] == 0.0
    assert first["genuine_count"] == 2
    assert first["impostor_count"] == 2


def test_roc_is_empty_without_both_kinds():
    assert compute_roc([], []) == []
    assert compute_roc([make_result("g1", "genuine", 0.9)], []) == []


def test_equal_error_rate_is_reported():
    results = [
        make_result("g1", "genuine", 0.90),
        make_result("g2", "genuine", 0.80),
        make_result("i1", "impostor", 0.50),
        make_result("i2", "impostor", 0.10),
    ]

    eer = compute_equal_error_rate(
        [r for r in results if r.kind == "genuine"],
        [r for r in results if r.kind == "impostor"],
    )

    assert eer is not None
    assert 0.0 <= eer["error_rate"] <= 1.0
    assert eer["threshold"] in {0.9, 0.8, 0.5, 0.1}


def test_equal_error_rate_is_none_without_data():
    assert compute_equal_error_rate([], []) is None


# =========================================================
# UNCERTAINTY
# =========================================================


def test_wilson_interval_brackets_the_observed_rate():
    lower, upper = wilson_interval(5, 10)

    assert lower < 0.5 < upper


def test_wilson_interval_for_a_perfect_small_sample_is_wide():
    """Four out of four is not the same as four hundred out of four hundred."""

    small_lower, small_upper = wilson_interval(4, 4)
    large_lower, large_upper = wilson_interval(400, 400)

    assert small_upper > large_upper
    assert small_lower < large_lower

    # A perfect small sample cannot rule out a much lower true rate.
    assert small_lower < 0.6
    assert large_lower > 0.99


def test_wilson_interval_for_no_samples_is_the_full_range():
    assert wilson_interval(0, 0) == (0.0, 1.0)


# =========================================================
# REPORT
# =========================================================


def test_report_contains_the_attempts_and_the_metrics():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    results = [
        make_result("g1", "genuine", 0.90),
        make_result("i1", "impostor", 0.10),
    ]

    metrics = compute_metrics(results, threshold=0.40)

    report = build_report(
        dataset,
        results,
        metrics,
        {"face_match_threshold": 0.40},
    )

    assert report["dataset_version"] == 1
    assert len(report["attempts"]) == 2
    assert report["metrics"]["threshold"] == 0.40
    assert report["configuration"]["face_match_threshold"] == 0.40
    assert "created_at" in report


def test_report_contains_no_biometric_material():
    dataset = build_dataset(
        [
            Attempt("g1", "a.jpg", "A", "A", "genuine"),
            Attempt("i1", "b.jpg", "A", "B", "impostor"),
        ]
    )

    results = [
        make_result("g1", "genuine", 0.90),
        make_result("i1", "impostor", 0.10),
    ]

    metrics = compute_metrics(results, threshold=0.40)

    report = build_report(dataset, results, metrics, {})

    serialized = json.dumps(report)

    assert ".npy" not in serialized
    assert "embedding" not in serialized.lower()
    assert "base64" not in serialized


def test_write_report_creates_the_file(tmp_path):
    report = {"metrics": {"threshold": 0.4}, "attempts": []}

    output = tmp_path / "nested" / "report.json"

    write_report(report, output)

    assert output.is_file()
    assert json.loads(output.read_text())["metrics"]["threshold"] == 0.4
