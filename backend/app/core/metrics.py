"""
Application Metrics & Prometheus Telemetry Registry.

Provides lightweight, thread-safe Prometheus metrics collection without heavy external dependencies.
Exposes standard Prometheus exposition format (text/plain; version=0.0.4) at /metrics.
"""

import threading
from collections import defaultdict
from typing import Any

# Standard latency buckets for HTTP requests & AI operations (in seconds)
HTTP_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class MetricsRegistry:
    """Thread-safe in-memory metrics registry formatted for Prometheus scraping."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counters: (name, label_tuple) -> count
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        # Gauges: (name, label_tuple) -> value
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        # Histograms: (name, label_tuple) -> { "buckets": dict[float, int], "sum": float, "count": int }
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}
        self._metric_help: dict[str, str] = {
            "http_requests_total": "Total number of HTTP requests processed by endpoint and status.",
            "http_request_duration_seconds": "HTTP request latency summary across endpoints.",
            "document_processing_seconds": "Duration of PDF/DOCX document extraction and segmentation.",
            "llm_reasoning_seconds": "Latency of Gemini structured reasoning and risk analysis calls.",
            "vector_search_seconds": "Latency of vector similarity retrieval queries.",
            "clauses_analyzed_total": "Total number of legal clauses evaluated by risk tier.",
            "prompt_injections_neutralized_total": "Total number of adversarial prompt injections detected and neutralized.",
            "auth_failures_total": "Total number of unauthorized or invalid login attempts.",
            "active_database_connections": "Current estimated active database connection pool gauge.",
        }
        self._metric_type: dict[str, str] = {
            "http_requests_total": "counter",
            "http_request_duration_seconds": "histogram",
            "document_processing_seconds": "histogram",
            "llm_reasoning_seconds": "histogram",
            "vector_search_seconds": "histogram",
            "clauses_analyzed_total": "counter",
            "prompt_injections_neutralized_total": "counter",
            "auth_failures_total": "counter",
            "active_database_connections": "gauge",
        }

    def _labels_to_key(self, labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((k, str(v)) for k, v in labels.items()))

    def increment(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        key = (name, self._labels_to_key(labels))
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set the current value of a gauge metric."""
        key = (name, self._labels_to_key(labels))
        with self._lock:
            self._gauges[key] = value

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        buckets: tuple[float, ...] = HTTP_LATENCY_BUCKETS,
    ) -> None:
        """Observe a latency duration in a histogram metric."""
        label_key = self._labels_to_key(labels)
        key = (name, label_key)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = {
                    "buckets": {b: 0 for b in buckets},
                    "sum": 0.0,
                    "count": 0,
                }
            hist = self._histograms[key]
            hist["sum"] += value
            hist["count"] += 1
            for b in buckets:
                if value <= b:
                    hist["buckets"][b] += 1

    def generate_exposition(self) -> str:
        """Generate official Prometheus text format exposition."""
        lines: list[str] = []
        with self._lock:
            all_metric_names = set(
                [k[0] for k in self._counters.keys()]
                + [k[0] for k in self._gauges.keys()]
                + [k[0] for k in self._histograms.keys()]
            )

            for name in sorted(all_metric_names):
                help_text = self._metric_help.get(name, f"Application metric {name}")
                m_type = self._metric_type.get(name, "untyped")
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {m_type}")

                # Output Counters
                for (c_name, labels_tuple), val in self._counters.items():
                    if c_name == name:
                        lbl_str = ""
                        if labels_tuple:
                            lbl_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels_tuple) + "}"
                        lines.append(f"{name}{lbl_str} {val}")

                # Output Gauges
                for (g_name, labels_tuple), val in self._gauges.items():
                    if g_name == name:
                        lbl_str = ""
                        if labels_tuple:
                            lbl_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels_tuple) + "}"
                        lines.append(f"{name}{lbl_str} {val}")

                # Output Histograms
                for (h_name, labels_tuple), h_data in self._histograms.items():
                    if h_name == name:
                        base_lbls = dict(labels_tuple)
                        # Buckets
                        for b_val, b_count in sorted(h_data["buckets"].items()):
                            b_dict = {**base_lbls, "le": str(b_val)}
                            b_str = "{" + ",".join(f'{k}="{v}"' for k, v in b_dict.items()) + "}"
                            lines.append(f"{name}_bucket{b_str} {b_count}")
                        # +Inf bucket
                        inf_dict = {**base_lbls, "le": "+Inf"}
                        inf_str = "{" + ",".join(f'{k}="{v}"' for k, v in inf_dict.items()) + "}"
                        lines.append(f"{name}_bucket{inf_str} {h_data['count']}")
                        # Sum and Count
                        s_str = ""
                        if labels_tuple:
                            s_str = "{" + ",".join(f'{k}="{v}"' for k, v in labels_tuple) + "}"
                        lines.append(f"{name}_sum{s_str} {h_data['sum']:.6f}")
                        lines.append(f"{name}_count{s_str} {h_data['count']}")

        return "\n".join(lines) + "\n"


# Global singleton metrics registry
registry = MetricsRegistry()


# Convenience tracking functions
def track_request(method: str, path: str, status_code: int, duration_sec: float) -> None:
    norm_path = path.split("?")[0]
    # Normalize ID-based paths to avoid metric cardinality explosion
    if "/analysis/" in norm_path:
        norm_path = "/api/v1/analysis/{id}"
    elif "/documents/" in norm_path:
        norm_path = "/api/v1/documents/{id}"

    labels = {
        "method": method,
        "endpoint": norm_path,
        "status": str(status_code),
    }
    registry.increment("http_requests_total", labels=labels)
    registry.observe(
        "http_request_duration_seconds",
        duration_sec,
        labels={"method": method, "endpoint": norm_path},
    )


def track_llm_call(model_name: str, duration_sec: float) -> None:
    registry.observe("llm_reasoning_seconds", duration_sec, labels={"model": model_name})


def track_vector_search(duration_sec: float) -> None:
    registry.observe("vector_search_seconds", duration_sec)


def track_clause_risk(risk_level: str) -> None:
    registry.increment("clauses_analyzed_total", labels={"risk_level": risk_level.upper()})


def track_prompt_injection() -> None:
    registry.increment("prompt_injections_neutralized_total")


def track_auth_failure() -> None:
    registry.increment("auth_failures_total")
