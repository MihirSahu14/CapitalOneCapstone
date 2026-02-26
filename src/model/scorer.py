from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd


@dataclass
class FraudScorer:
    model: Any
    calibration_scores: np.ndarray

    @classmethod
    def load(cls, path: str) -> "FraudScorer":
        artifact = joblib.load(path)
        return cls(
            model=artifact["model"],
            calibration_scores=np.array(artifact["calibration_scores"], dtype=float),
        )

    def _to_uniform_percentile(self, prob: float) -> float:
        # Percentile rank maps model probability into near-uniform [0, 1] score.
        return float(np.searchsorted(self.calibration_scores, prob, side="right") / len(self.calibration_scores))

    def score(self, tx: dict[str, Any]) -> float:
        frame = pd.DataFrame([tx])
        prob = float(self.model.predict_proba(frame)[:, 1][0])
        return self._to_uniform_percentile(prob)
