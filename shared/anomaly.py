"""
Lightweight z-score anomaly detection for metric streams.
"""
import os
from collections import deque
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Deque, Dict, Optional, Tuple


@dataclass
class AnomalyResult:
    is_anomaly: bool
    z_score: float
    value: float
    mean: float
    stddev: float


class ZScoreDetector:
    """Rolling-window z-score detector per metric key."""

    def __init__(self, window_size: int = 30, threshold: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold
        self._windows: Dict[str, Deque[float]] = {}

    @classmethod
    def from_env(cls) -> "ZScoreDetector":
        threshold = float(os.getenv("ANOMALY_ZSCORE_THRESHOLD", "3.0"))
        window = int(os.getenv("ANOMALY_WINDOW_SIZE", "30"))
        return cls(window_size=window, threshold=threshold)

    def check(self, key: str, value: float) -> AnomalyResult:
        window = self._windows.setdefault(key, deque(maxlen=self.window_size))
        window.append(value)

        if len(window) < 5:
            return AnomalyResult(False, 0.0, value, value, 0.0)

        avg = mean(window)
        spread = stdev(window)
        if spread == 0:
            return AnomalyResult(False, 0.0, value, avg, 0.0)

        z = abs(value - avg) / spread
        return AnomalyResult(z >= self.threshold, z, value, avg, spread)
