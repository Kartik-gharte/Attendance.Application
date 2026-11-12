"""Measure the baseline startup cost, memory use, and request latency.

This is a developer tool. It measures the service with synthetic data and
without camera or biometric model assets, so it can be run on any machine.

Run it from the project root::

    python -m manual.benchmark

The numbers it reports are the documented baseline. They are measured on a
developer machine and are not a capacity guarantee.
"""

import argparse
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def measure_import() -> tuple[float, float]:
    """Return the import time in seconds and the resident memory in MB.

    The import is measured in a subprocess so that the measurement is not
    polluted by modules that are already loaded.
    """

    import subprocess

    script = (
        "import os, resource, sys, time\n"
        f"sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})\n"
        "start = time.perf_counter()\n"
        "import app.main\n"
        "elapsed = time.perf_counter() - start\n"
        "rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "print(elapsed)\n"
        "print(rss / 1024 / 1024)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"The measurement subprocess failed: {result.stderr[-500:]}"
        )

    lines = result.stdout.strip().split("\n")

    return float(lines[0]), float(lines[1])


def measure_startup() -> dict:
    """Measure the lifespan startup with stubbed biometric services.

    The biometric models are not loaded, so this measures the cost of the
    schema initialization and the service wiring rather than the cost of
    loading the models.
    """

    from dataclasses import dataclass

    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.core.services import AppServices
    from app.main import create_app

    @dataclass
    class StubLivenessService:
        detector: object = None

        def close(self):
            pass

    @dataclass
    class StubFaceService:
        app: object = None

    class StubAttendanceService:
        def verify_face(self, image_path, student_id):
            return {"result": "MATCH", "similarity": 0.9, "threshold": 0.4}

        def create_attendance_result(
            self,
            student_id,
            liveness_verified,
            face_result,
        ):
            return {
                "student_id": student_id,
                "liveness": "VERIFIED",
                "face": "MATCH",
                "similarity": face_result["similarity"],
                "threshold": face_result["threshold"],
                "attendance": "VERIFIED",
            }

    working_dir = tempfile.mkdtemp()
    database_path = Path(working_dir) / "benchmark.db"

    services = AppServices(
        liveness_service=StubLivenessService(),
        face_service=StubFaceService(),
        attendance_service=StubAttendanceService(),
    )

    application = create_app(
        settings=Settings(
            _env_file=None,
            database_path=database_path,
        ),
        service_factory=lambda settings: services,
    )

    start = time.perf_counter()

    with TestClient(application) as client:
        startup_seconds = time.perf_counter() - start

        latencies = []

        # Warm up so that the first request, which pays for the connection
        # setup and the first routing, does not distort the percentiles.
        for _ in range(5):
            client.get("/health/live")

        for _ in range(50):
            request_start = time.perf_counter()
            client.get("/health/live")
            latencies.append((time.perf_counter() - request_start) * 1000)

    return {
        "startup_seconds": startup_seconds,
        "latency_mean_ms": statistics.mean(latencies),
        "latency_p95_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)],
        "latency_max_ms": max(latencies),
    }


def measure_concurrency(workers: int = 8, requests_per_worker: int = 25) -> dict:
    """Measure the throughput of the health endpoint under concurrency."""

    import threading

    from dataclasses import dataclass

    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.core.services import AppServices
    from app.main import create_app

    @dataclass
    class StubLivenessService:
        detector: object = None

        def close(self):
            pass

    @dataclass
    class StubFaceService:
        app: object = None

    class StubAttendanceService:
        pass

    working_dir = tempfile.mkdtemp()
    database_path = Path(working_dir) / "benchmark.db"

    services = AppServices(
        liveness_service=StubLivenessService(),
        face_service=StubFaceService(),
        attendance_service=StubAttendanceService(),
    )

    application = create_app(
        settings=Settings(
            _env_file=None,
            database_path=database_path,
        ),
        service_factory=lambda settings: services,
    )

    latencies: list[float] = []
    lock = threading.Lock()

    def worker(client):
        local = []

        for _ in range(requests_per_worker):
            request_start = time.perf_counter()
            client.get("/health/live")
            local.append((time.perf_counter() - request_start) * 1000)

        with lock:
            latencies.extend(local)

    with TestClient(application) as client:

        start = time.perf_counter()

        threads = [
            threading.Thread(target=worker, args=(client,))
            for _ in range(workers)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.perf_counter() - start

    total = workers * requests_per_worker

    return {
        "requests": total,
        "elapsed_seconds": elapsed,
        "requests_per_second": total / elapsed,
        "latency_mean_ms": statistics.mean(latencies),
        "latency_max_ms": max(latencies),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure the baseline startup cost, memory, and latency",
    )

    parser.add_argument(
        "--skip-concurrency",
        action="store_true",
        help="Skip the concurrency measurement",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of concurrent workers in the concurrency measurement",
    )

    args = parser.parse_args(argv)

    print("=== Baseline measurement ===")
    print()

    import_seconds, memory_mb = measure_import()

    print(f"Import time (app.main):        {import_seconds:.2f} s")
    print(f"Resident memory after import:   {memory_mb:.1f} MB")
    print()

    startup = measure_startup()

    print(
        f"Startup without model assets:   "
        f"{startup['startup_seconds']:.2f} s"
    )
    print(
        f"Health request mean latency:    "
        f"{startup['latency_mean_ms']:.2f} ms"
    )
    print(
        f"Health request p95 latency:     "
        f"{startup['latency_p95_ms']:.2f} ms"
    )
    print()

    if not args.skip_concurrency:

        concurrency = measure_concurrency(workers=args.workers)

        print(
            f"Concurrency ({concurrency['requests']} requests, "
            f"{args.workers} workers):"
        )
        print(
            f"  Throughput:                  "
            f"{concurrency['requests_per_second']:.1f} requests/s"
        )
        print(
            f"  Mean latency:                "
            f"{concurrency['latency_mean_ms']:.2f} ms"
        )
        print(
            f"  Maximum latency:             "
            f"{concurrency['latency_max_ms']:.2f} ms"
        )
        print()

    print(
        "These numbers were measured on a developer machine with the "
        "biometric\nmodels stubbed out. They are a baseline, not a capacity "
        "guarantee."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
