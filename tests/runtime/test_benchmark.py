"""Tests for the baseline measurement harness.

The harness is a developer tool, so the tests check that it runs and that
it reports the documented fields rather than asserting exact numbers,
which depend on the machine.
"""

import importlib

import pytest


@pytest.fixture(scope="module")
def benchmark():
    return importlib.import_module("manual.benchmark")


def test_benchmark_reports_the_documented_fields(benchmark, capsys):
    exit_code = benchmark.main(["--skip-concurrency"])

    assert exit_code == 0

    output = capsys.readouterr().out

    assert "Import time" in output
    assert "Resident memory" in output
    assert "Startup without model assets" in output
    assert "Health request mean latency" in output


def test_benchmark_reports_concurrency(benchmark, capsys):
    exit_code = benchmark.main(["--workers", "2"])

    assert exit_code == 0

    output = capsys.readouterr().out

    assert "Throughput" in output
    assert "requests/s" in output


def test_benchmark_measure_import_returns_positive_values(benchmark):
    import_seconds, memory_mb = benchmark.measure_import()

    assert import_seconds > 0
    assert memory_mb > 0


def test_benchmark_measure_startup_returns_timings(benchmark):
    startup = benchmark.measure_startup()

    assert startup["startup_seconds"] >= 0
    assert startup["latency_mean_ms"] >= 0
    assert startup["latency_p95_ms"] >= 0
    assert startup["latency_max_ms"] >= startup["latency_p95_ms"]
