"""Unit tests for z-score anomaly detection."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

from anomaly import ZScoreDetector


def test_no_anomaly_on_stable_series():
    d = ZScoreDetector(window_size=20, threshold=3.0)
    for v in [48.0, 49.0, 50.0, 51.0, 52.0] * 4:
        d.check("host:cpu", v)
    r = d.check("host:cpu", 50.5)
    assert not r.is_anomaly


def test_anomaly_on_spike():
    d = ZScoreDetector(window_size=20, threshold=2.0)
    for v in [10.0] * 15:
        d.check("host:cpu", v)
    r = d.check("host:cpu", 99.0)
    assert r.is_anomaly
    assert r.z_score > 2.0
