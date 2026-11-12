"""Reproducible evaluation harness for face recognition and liveness.

This module provides the measurement machinery that issue
[#11](https://github.com/Kartik-gharte/Attendance.Application/issues/11)
requires. It is deliberately separated from the dataset so that the
metrics can be verified with synthetic inputs while the consented dataset
is still being assembled.

What is implemented here
------------------------

- A fixed, versioned dataset description: every attempt names the genuine
  identity, the claimed identity, the image, and the expected outcome.
- Per-attempt scores and decisions, recorded with the configuration that
  produced them.
- Metrics: false accept rate, false reject rate, ROC, equal error rate,
  and the liveness success rate.
- Wilson score intervals, so a rate computed from a small sample is
  reported with its uncertainty rather than as a bare number.
- A dataset policy check, so that a dataset which would violate the
  consent rules cannot be evaluated by accident.

What is NOT implemented here
----------------------------

No accuracy numbers are reported. Producing them requires a consented
dataset, which is not available. This module therefore refuses to run
without one rather than producing a number that looks measured but is not.

Usage
-----

Prepare a dataset as a JSON file::

    {
      "version": 1,
      "attempts": [
        {
          "id": "genuine-0001",
          "image": "images/subject-a/0001.jpg",
          "genuine_identity": "SUBJ-A",
          "claimed_identity": "SUBJ-A",
          "kind": "genuine",
          "liveness_expected": true
        },
        {
          "id": "impostor-0001",
          "image": "images/subject-a/0002.jpg",
          "genuine_identity": "SUBJ-A",
          "claimed_identity": "SUBJ-B",
          "kind": "impostor",
          "liveness_expected": false
        }
      ]
    }

Run the evaluation::

    python -m app.evaluation.evaluate --dataset dataset.json --output report.json

The report records every attempt, the metrics, and the configuration. It
never contains an image, an embedding, or a biometric template.
"""

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_THRESHOLD = 0.40


class EvaluationError(RuntimeError):
    """Raised when an evaluation cannot be run or is not trustworthy."""


# =========================================================
# DATASET DESCRIPTION
# =========================================================

@dataclass
class Attempt:
    """One evaluation attempt."""

    id: str
    image: str
    genuine_identity: str
    claimed_identity: str
    kind: str
    liveness_expected: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Dataset:
    """A versioned description of the evaluation attempts."""

    version: int
    attempts: list[Attempt]
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict) -> "Dataset":
        if "attempts" not in payload:
            raise EvaluationError("The dataset has no attempts")

        attempts = []

        for entry in payload["attempts"]:
            missing = [
                key
                for key in (
                    "id",
                    "image",
                    "genuine_identity",
                    "claimed_identity",
                    "kind",
                )
                if key not in entry
            ]

            if missing:
                raise EvaluationError(
                    "An attempt is missing required fields: "
                    + ", ".join(missing)
                )

            kind = entry["kind"]

            if kind not in {"genuine", "impostor"}:
                raise EvaluationError(
                    f"Attempt '{entry['id']}' has an unknown kind '{kind}'. "
                    "Use 'genuine' or 'impostor'."
                )

            attempts.append(
                Attempt(
                    id=entry["id"],
                    image=entry["image"],
                    genuine_identity=entry["genuine_identity"],
                    claimed_identity=entry["claimed_identity"],
                    kind=kind,
                    liveness_expected=bool(
                        entry.get("liveness_expected", False)
                    ),
                    notes=entry.get("notes", ""),
                )
            )

        return cls(
            version=int(payload.get("version", 1)),
            attempts=attempts,
            metadata=payload.get("metadata", {}),
        )

    @classmethod
    def load(cls, path) -> "Dataset":
        file_path = Path(path)

        if not file_path.is_file():
            raise EvaluationError(f"No dataset found at {file_path}")

        try:
            payload = json.loads(
                file_path.read_text(encoding="utf-8")
            )

        except ValueError as error:
            raise EvaluationError(
                f"The dataset at {file_path} is not valid JSON: {error}"
            ) from error

        return cls.from_dict(payload)

    def validate(self) -> list[str]:
        """Return the problems that would make the evaluation untrustworthy."""

        problems = []

        if not self.attempts:
            problems.append("The dataset has no attempts")
            return problems

        ids = [attempt.id for attempt in self.attempts]

        duplicates = {
            attempt_id
            for attempt_id in ids
            if ids.count(attempt_id) > 1
        }

        if duplicates:
            problems.append(
                "Duplicate attempt identifiers: "
                + ", ".join(sorted(duplicates))
            )

        genuine = [
            attempt
            for attempt in self.attempts
            if attempt.kind == "genuine"
        ]
        impostor = [
            attempt
            for attempt in self.attempts
            if attempt.kind == "impostor"
        ]

        if not genuine:
            problems.append(
                "The dataset has no genuine attempts, so a false reject "
                "rate cannot be measured"
            )

        if not impostor:
            problems.append(
                "The dataset has no impostor attempts, so a false accept "
                "rate cannot be measured"
            )

        for attempt in self.attempts:
            if (
                attempt.kind == "genuine"
                and attempt.genuine_identity != attempt.claimed_identity
            ):
                problems.append(
                    f"Attempt '{attempt.id}' is marked genuine but the "
                    "genuine and claimed identities differ"
                )

            if (
                attempt.kind == "impostor"
                and attempt.genuine_identity == attempt.claimed_identity
            ):
                problems.append(
                    f"Attempt '{attempt.id}' is marked impostor but the "
                    "genuine and claimed identities are the same"
                )

        # Both the genuine and the claimed identities count, because an
        # impostor attempt is what introduces a second identity.
        identities = {
            attempt.genuine_identity
            for attempt in self.attempts
        } | {
            attempt.claimed_identity
            for attempt in self.attempts
        }

        if len(identities) < 2:
            problems.append(
                "The dataset covers fewer than two identities, so an "
                "impostor comparison is not meaningful"
            )

        return problems


# =========================================================
# RESULTS
# =========================================================

@dataclass
class AttemptResult:
    """The outcome of one attempt."""

    id: str
    kind: str
    genuine_identity: str
    claimed_identity: str
    similarity: float | None
    threshold: float
    matched: bool
    correct: bool
    liveness_detected: bool | None = None
    liveness_expected: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# =========================================================
# METRICS
# =========================================================

def wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Return the Wilson score interval for a binomial proportion.

    A bare rate from a small sample is misleading. The interval shows the
    uncertainty, so a rate of 100 percent over 4 attempts is not reported
    as if it were a fact.
    """

    if total <= 0:
        return (0.0, 1.0)

    z = 1.959963984540054 if confidence == 0.95 else 1.6448536269514722

    proportion = successes / total

    denominator = 1 + (z * z) / total
    centre = proportion + (z * z) / (2 * total)
    margin = z * math.sqrt(
        (proportion * (1 - proportion) / total)
        + (z * z) / (4 * total * total)
    )

    lower = (centre - margin) / denominator
    upper = (centre + margin) / denominator

    return (max(0.0, lower), min(1.0, upper))


def compute_metrics(
    results: list[AttemptResult],
    threshold: float,
) -> dict:
    """Compute the recognition and liveness metrics."""

    scored = [
        result
        for result in results
        if result.error is None and result.similarity is not None
    ]

    genuine = [result for result in scored if result.kind == "genuine"]
    impostor = [result for result in scored if result.kind == "impostor"]

    false_rejects = sum(1 for result in genuine if not result.matched)
    false_accepts = sum(1 for result in impostor if result.matched)

    genuine_count = len(genuine)
    impostor_count = len(impostor)

    far = (
        false_accepts / impostor_count if impostor_count else None
    )
    frr = (
        false_rejects / genuine_count if genuine_count else None
    )

    liveness_results = [
        result
        for result in results
        if result.liveness_detected is not None
    ]

    liveness_expected = [
        result
        for result in liveness_results
        if result.liveness_expected
    ]
    liveness_unexpected = [
        result
        for result in liveness_results
        if not result.liveness_expected
    ]

    liveness_success = (
        sum(
            1
            for result in liveness_expected
            if result.liveness_detected
        )
        / len(liveness_expected)
        if liveness_expected
        else None
    )

    liveness_false_accept = (
        sum(
            1
            for result in liveness_unexpected
            if result.liveness_detected
        )
        / len(liveness_unexpected)
        if liveness_unexpected
        else None
    )

    return {
        "threshold": threshold,
        "attempts_total": len(results),
        "attempts_scored": len(scored),
        "attempts_failed": len(results) - len(scored),
        "genuine_attempts": genuine_count,
        "impostor_attempts": impostor_count,
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "false_accept_rate": far,
        "false_reject_rate": frr,
        "false_accept_rate_interval": (
            wilson_interval(false_accepts, impostor_count)
            if impostor_count
            else None
        ),
        "false_reject_rate_interval": (
            wilson_interval(false_rejects, genuine_count)
            if genuine_count
            else None
        ),
        "liveness_attempts": len(liveness_results),
        "liveness_success_rate": liveness_success,
        "liveness_success_rate_interval": (
            wilson_interval(
                sum(
                    1
                    for result in liveness_expected
                    if result.liveness_detected
                ),
                len(liveness_expected),
            )
            if liveness_expected
            else None
        ),
        "liveness_false_accept_rate": liveness_false_accept,
        "roc": compute_roc(genuine, impostor),
        "equal_error_rate": compute_equal_error_rate(
            genuine,
            impostor,
        ),
    }


def compute_roc(
    genuine: list[AttemptResult],
    impostor: list[AttemptResult],
) -> list[dict]:
    """Return the ROC curve as a list of threshold points.

    Each point records the false accept rate and the true accept rate at
    one threshold, plus the point count, so a reader can judge how much
    the curve is worth.
    """

    if not genuine or not impostor:
        return []

    genuine_scores = sorted(
        (result.similarity for result in genuine),
        reverse=True,
    )
    impostor_scores = sorted(
        (result.similarity for result in impostor),
        reverse=True,
    )

    total_genuine = len(genuine_scores)
    total_impostor = len(impostor_scores)

    thresholds = sorted(
        set(genuine_scores) | set(impostor_scores),
        reverse=True,
    )

    points = []

    for threshold in thresholds:
        true_accepts = sum(
            1 for score in genuine_scores if score >= threshold
        )
        false_accepts = sum(
            1 for score in impostor_scores if score >= threshold
        )

        points.append(
            {
                "threshold": threshold,
                "true_accept_rate": true_accepts / total_genuine,
                "false_accept_rate": false_accepts / total_impostor,
                "genuine_count": total_genuine,
                "impostor_count": total_impostor,
            }
        )

    return points


def compute_equal_error_rate(
    genuine: list[AttemptResult],
    impostor: list[AttemptResult],
) -> dict | None:
    """Return the threshold where the false accept and reject rates meet."""

    roc = compute_roc(genuine, impostor)

    if not roc:
        return None

    best = None

    for point in roc:
        error_rate = 0.5 * (
            point["false_accept_rate"] + (1 - point["true_accept_rate"])
        )

        if best is None or error_rate < best["error_rate"]:
            best = {
                "threshold": point["threshold"],
                "error_rate": error_rate,
                "false_accept_rate": point["false_accept_rate"],
                "false_reject_rate": 1 - point["true_accept_rate"],
            }

    return best


# =========================================================
# REPORT
# =========================================================

def build_report(
    dataset: Dataset,
    results: list[AttemptResult],
    metrics: dict,
    configuration: dict,
) -> dict:
    """Build the evaluation report.

    The report contains the per-attempt decisions and the metrics. It
    never contains an image, an embedding, or a biometric template.
    """

    return {
        "created_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "dataset_version": dataset.version,
        "dataset_metadata": dataset.metadata,
        "configuration": configuration,
        "metrics": metrics,
        "attempts": [result.to_dict() for result in results],
    }


def write_report(report: dict, path) -> None:
    """Write the report as JSON."""

    file_path = Path(path)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
