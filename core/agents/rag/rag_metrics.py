from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Thresholds: (WARN, CRIT)
# WARN: value >= warn → logger.warning
# CRIT: value >= crit → logger.warning with CRIT label
THRESHOLDS: Dict[str, tuple[float, float]] = {
    'total_latency_ms': (2000.0, 5000.0),
    'embedding_latency_ms': (500.0, 1000.0),
    'chromadb_latency_ms': (500.0, 1000.0),
    'bm25_latency_ms': (200.0, 500.0),
    'avg_distance': (1.5, 2.0),
    'rrf_score_top_range': (0.001, 0.0),
}

RESULT_COUNT_RATIO_WARN: float = 0.5


def _check(value: float, threshold: tuple[float, float]) -> str:
    """Higher is worse: latency, distance, etc."""
    warn, crit = threshold
    if value >= crit:
        return 'CRIT'
    if value >= warn:
        return 'WARN'
    return 'PASS'


def _check_lower(value: float, threshold: tuple[float, float]) -> str:
    """Lower is worse: result count ratio, etc."""
    warn, crit = threshold
    if value <= crit:
        return 'CRIT'
    if value <= warn:
        return 'WARN'
    return 'PASS'


@dataclass
class RAGMetrics:
    total_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    chromadb_latency_ms: float = 0.0
    bm25_latency_ms: float = 0.0
    result_count: int = 0
    top_k: int = 10
    avg_distance: float = 0.0
    rrf_score_top_range: float = 0.0

    @property
    def result_count_ratio(self) -> float:
        if self.top_k == 0:
            return 0.0
        return self.result_count / self.top_k

    def status(self) -> Dict[str, str]:
        st: Dict[str, str] = {}
        for key in (
            'total_latency_ms', 'embedding_latency_ms',
            'chromadb_latency_ms', 'bm25_latency_ms',
            'avg_distance',
        ):
            st[key] = _check(getattr(self, key), THRESHOLDS[key])
        st['rrf_score_top_range'] = _check_lower(
            self.rrf_score_top_range, THRESHOLDS['rrf_score_top_range'],
        )
        st['result_count'] = _check_lower(
            self.result_count_ratio,
            (RESULT_COUNT_RATIO_WARN, 0.0),
        )
        return st

    def has_issues(self) -> bool:
        return any(v != 'PASS' for v in self.status().values())

    def log_issues(self, query: str) -> None:
        issues = {k: v for k, v in self.status().items() if v != 'PASS'}
        if not issues:
            return
        logger.warning(
            'RAG threshold exceeded query=%s issues=%s metrics=%s',
            query[:80], issues, asdict(self),
        )

    def to_log(self) -> Dict[str, Any]:
        return {
            'total_latency_ms': round(self.total_latency_ms, 1),
            'embedding_latency_ms': round(self.embedding_latency_ms, 1),
            'chromadb_latency_ms': round(self.chromadb_latency_ms, 1),
            'bm25_latency_ms': round(self.bm25_latency_ms, 1),
            'result_count': self.result_count,
            'top_k': self.top_k,
            'avg_distance': round(self.avg_distance, 3),
            'rrf_score_top_range': round(self.rrf_score_top_range, 4),
        }


class Timer:
    def __init__(self) -> None:
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> Timer:
        self._start: float = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
