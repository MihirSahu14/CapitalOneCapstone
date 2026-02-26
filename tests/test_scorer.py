from __future__ import annotations

import numpy as np

from src.model.scorer import FraudScorer


class DummyModel:
    def predict_proba(self, _frame):
        return np.array([[0.2, 0.8]])


def test_uniform_percentile_transform():
    scorer = FraudScorer(model=DummyModel(), calibration_scores=np.array([0.1, 0.3, 0.6, 0.9]))
    score = scorer.score({"amount": 10, "merchant": "X", "location": "Y", "timestamp": 123})
    assert 0.74 <= score <= 0.76
