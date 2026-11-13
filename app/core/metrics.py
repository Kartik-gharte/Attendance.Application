"""Dependency-free metrics for the attendance service.

The service exposes a small set of operational metrics in the Prometheus
text exposition format. No third-party library is used, so the dependency
manifest does not grow for the sake of observability.

Privacy
-------

A metric label must never contain personal data. The route label is the
route *template*, for example ``/attendance/student/{student_id}``, and
never the requested path, which would contain a student identifier.

The templates are matched against the request path with the same
converters that Starlette uses for routing, so the template is exact. A
path that matches no route is labelled ``unmatched``, rather than being
recorded verbatim.

Metric names are fixed. Only the route, the method, and the status code
vary, and none of them are attacker controlled beyond the method and the
status code.

What is measured
----------------

- the number of HTTP requests, by route, method, and status;
- the request duration, as a histogram with fixed buckets;
- whether the database is reachable;
- whether the biometric models are loaded;
- the number of live liveness sessions;
- the number of attendance outcomes.
"""

import threading
import time
from pathlib import Path

from starlette.routing import compile_path

from app.core.logging_config import get_logger


logger = get_logger("core.metrics")

# Duration buckets in seconds. The upper bound is the last bucket, and
# anything slower is counted in it.
DURATION_BUCKETS = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)

UNMATCHED_ROUTE = "unmatched"


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""

    parts = []

    for key in sorted(labels):
        value = str(labels[key]).replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{key}="{value}"')

    return "{" + ",".join(parts) + "}"


def _collect_route_paths(routes, prefix: str = "", seen=None) -> list[str]:
    """Return the path templates of every route.

    The collector walks nested routers, because the way included routers
    are represented differs between framework versions. Only the template
    is collected, never a concrete path.
    """

    if seen is None:
        seen = set()

    paths: list[str] = []

    for route in routes or []:

        if id(route) in seen:
            continue

        seen.add(id(route))

        # Some versions keep an included router behind a wrapper object.
        nested_router = getattr(route, "original_router", None)

        if nested_router is not None:
            paths.extend(
                _collect_route_paths(
                    getattr(nested_router, "routes", []),
                    prefix,
                    seen,
                )
            )
            continue

        path = (
            getattr(route, "path_format", None)
            or getattr(route, "path", None)
        )

        if path:
            paths.append(f"{prefix}{path}")

        sub_routes = getattr(route, "routes", None)

        if sub_routes:
            # A mount contributes a prefix to the routes below it.
            paths.extend(
                _collect_route_paths(
                    sub_routes,
                    f"{prefix}{path}" if path else prefix,
                    seen,
                )
            )

    return paths


class MetricsRegistry:
    """Collects and renders the service metrics.

    The registry is safe to use from several threads, because the
    synchronous endpoints run in a thread pool.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple], float] = {}
        self._gauges: dict[tuple[str, tuple], float] = {}
        self._histograms: dict[tuple[str, tuple], dict[str, float]] = {}
        self._templates: list[tuple] = []
        self._started_at = time.time()

    # ------------------------------------------------------------
    # ROUTE TEMPLATES
    # ------------------------------------------------------------

    def register_routes(self, application) -> None:
        """Collect the route templates so that labels stay free of
        personal data."""

        templates = []

        for path in _collect_route_paths(getattr(application, "routes", [])):
            try:
                regex, _, _ = compile_path(path)
            except Exception:
                continue

            templates.append((regex, path))

        with self._lock:
            self._templates = templates

        logger.debug(
            "Registered %d route template(s) for metric labels",
            len(templates),
        )

    def route_label(self, path: str) -> str:
        """Return the route template for a request path.

        The requested path is never returned, because it can contain a
        student identifier.
        """

        with self._lock:
            templates = list(self._templates)

        for regex, template in templates:
            if regex.match(path):
                return template

        return UNMATCHED_ROUTE

    # ------------------------------------------------------------
    # RECORDING
    # ------------------------------------------------------------

    def increment(self, name: str, value: float = 1.0, **labels) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))

        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, **labels) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))

        with self._lock:
            self._gauges[key] = value

    def observe_duration(self, name: str, seconds: float, **labels) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))

        with self._lock:
            buckets = self._histograms.setdefault(key, {})

            for bound in DURATION_BUCKETS:
                if seconds <= bound:
                    buckets[str(bound)] = buckets.get(str(bound), 0.0) + 1.0

            buckets["+Inf"] = buckets.get("+Inf", 0.0) + 1.0
            buckets["_sum"] = buckets.get("_sum", 0.0) + seconds
            buckets["_count"] = buckets.get("_count", 0.0) + 1.0

    # ------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------

    def render(self) -> str:
        """Render the metrics in the Prometheus text exposition format."""

        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = {
                key: dict(buckets)
                for key, buckets in self._histograms.items()
            }

        lines: list[str] = []

        lines.append("# HELP attendance_up Whether the service is running.")
        lines.append("# TYPE attendance_up gauge")
        lines.append("attendance_up 1")

        uptime = time.time() - self._started_at
        lines.append("# HELP attendance_uptime_seconds Seconds since start.")
        lines.append("# TYPE attendance_uptime_seconds gauge")
        lines.append(f"attendance_uptime_seconds {uptime:.3f}")

        for (name, label_pairs), value in sorted(counters.items()):
            labels = dict(label_pairs)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{_format_labels(labels)} {value}")

        for (name, label_pairs), value in sorted(gauges.items()):
            labels = dict(label_pairs)
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{_format_labels(labels)} {value}")

        for (name, label_pairs), buckets in sorted(histograms.items()):
            labels = dict(label_pairs)

            lines.append(f"# TYPE {name} histogram")

            for bound in DURATION_BUCKETS:
                bucket_labels = dict(labels)
                bucket_labels["le"] = str(bound)
                count = buckets.get(str(bound), 0.0)
                lines.append(
                    f"{name}_bucket{_format_labels(bucket_labels)} {count}"
                )

            inf_labels = dict(labels)
            inf_labels["le"] = "+Inf"
            lines.append(
                f"{name}_bucket{_format_labels(inf_labels)} "
                f"{buckets.get('+Inf', 0.0)}"
            )

            lines.append(f"{name}_sum{_format_labels(labels)} "
                         f"{buckets.get('_sum', 0.0)}")
            lines.append(f"{name}_count{_format_labels(labels)} "
                         f"{buckets.get('_count', 0.0)}")

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Clear every collected metric. Used by the tests."""

        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# The registry is process-wide, matching the single-process deployment
# model. A multi-worker deployment would need one registry per worker.
registry = MetricsRegistry()


def get_registry() -> MetricsRegistry:
    """Return the process-wide metrics registry."""

    return registry
