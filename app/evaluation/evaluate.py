"""Run a face recognition and liveness evaluation.

The runner loads the biometric models once, evaluates every attempt in the
dataset, and writes a report. It refuses to run without a dataset that
passes the dataset checks, so it cannot produce a number that looks
measured but is not.

Usage::

    python -m app.evaluation.evaluate --dataset dataset.json --output report.json

No accuracy numbers ship with this project. The report is produced only
when a consented dataset is supplied.
"""

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.evaluation.harness import (
    AttemptResult,
    Dataset,
    EvaluationError,
    build_report,
    compute_metrics,
    write_report,
)


logger = get_logger("evaluation.evaluate")


def load_services(settings):
    """Load the biometric services used by the evaluation."""

    from app.core.services import build_services

    return build_services(settings)


def evaluate_attempt(
    attempt,
    services,
    threshold: float,
    embedding_dir: Path,
    dataset_root: Path,
) -> AttemptResult:
    """Evaluate one attempt and return its result."""

    image_path = Path(attempt.image)

    if not image_path.is_absolute():
        image_path = dataset_root / image_path

    base = AttemptResult(
        id=attempt.id,
        kind=attempt.kind,
        genuine_identity=attempt.genuine_identity,
        claimed_identity=attempt.claimed_identity,
        similarity=None,
        threshold=threshold,
        matched=False,
        correct=False,
        liveness_expected=attempt.liveness_expected,
    )

    try:

        face_result = services.attendance_service.verify_face(
            str(image_path),
            attempt.claimed_identity,
        )

    except Exception as error:

        base.error = f"{type(error).__name__}: {error}"
        return base

    similarity = face_result.get("similarity")

    base.similarity = similarity

    if similarity is None:
        base.error = "No similarity was produced"
        return base

    base.matched = similarity >= threshold

    base.correct = (
        base.matched
        if attempt.kind == "genuine"
        else not base.matched
    )

    return base


def evaluate_liveness(
    attempt,
    services,
    threshold: float,
    dataset_root: Path,
) -> bool | None:
    """Return whether a blink was detected in the attempt image."""

    import cv2

    image_path = Path(attempt.image)

    if not image_path.is_absolute():
        image_path = dataset_root / image_path

    image = cv2.imread(str(image_path))

    if image is None:
        return None

    try:

        result = services.liveness_service.process_frame(
            image,
            0,
            False,
        )

    except Exception:
        return None

    return bool(result.get("liveness_verified", False))


def run_evaluation(
    dataset_path,
    output_path=None,
    threshold=None,
    skip_liveness=False,
) -> dict:
    """Run the evaluation and return the report."""

    settings = get_settings()

    if threshold is None:
        threshold = settings.face_match_threshold

    dataset = Dataset.load(dataset_path)

    problems = dataset.validate()

    if problems:
        raise EvaluationError(
            "The dataset cannot be evaluated:\n- "
            + "\n- ".join(problems)
        )

    dataset_root = Path(dataset_path).parent

    services = load_services(settings)

    try:

        results = []

        for attempt in dataset.attempts:

            result = evaluate_attempt(
                attempt,
                services,
                threshold,
                settings.embedding_dir,
                dataset_root,
            )

            if not skip_liveness and attempt.liveness_expected:
                result.liveness_detected = evaluate_liveness(
                    attempt,
                    services,
                    threshold,
                    dataset_root,
                )

            results.append(result)

            logger.info(
                "Evaluated attempt %s: kind=%s similarity=%s matched=%s",
                attempt.id,
                attempt.kind,
                result.similarity,
                result.matched,
            )

    finally:

        services.close()

    metrics = compute_metrics(results, threshold)

    report = build_report(
        dataset,
        results,
        metrics,
        {
            "face_match_threshold": threshold,
            "insightface_model_name": settings.insightface_model_name,
            "mediapipe_model": str(
                settings.mediapipe_face_landmarker_model
            ),
            "liveness_evaluated": not skip_liveness,
        },
    )

    if output_path is not None:
        write_report(report, output_path)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate face recognition and liveness accuracy",
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the dataset description JSON file",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write the evaluation report to",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Similarity threshold (defaults to the configured threshold)",
    )
    parser.add_argument(
        "--skip-liveness",
        action="store_true",
        help="Do not evaluate the liveness check",
    )

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    configure_logging(get_settings())

    try:

        report = run_evaluation(
            dataset_path=args.dataset,
            output_path=args.output,
            threshold=args.threshold,
            skip_liveness=args.skip_liveness,
        )

    except EvaluationError as error:

        logger.error("The evaluation could not be run: %s", error)
        return 1

    except Exception as error:

        logger.error(
            "The evaluation failed: %s: %s",
            type(error).__name__,
            error,
        )
        return 1

    metrics = report["metrics"]

    logger.info("Evaluation complete")
    logger.info(
        "  Attempts: %s scored of %s",
        metrics["attempts_scored"],
        metrics["attempts_total"],
    )
    logger.info(
        "  False accept rate: %s",
        metrics["false_accept_rate"],
    )
    logger.info(
        "  False reject rate: %s",
        metrics["false_reject_rate"],
    )

    if metrics["equal_error_rate"] is not None:
        logger.info(
            "  Equal error rate: %s at threshold %s",
            metrics["equal_error_rate"]["error_rate"],
            metrics["equal_error_rate"]["threshold"],
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
