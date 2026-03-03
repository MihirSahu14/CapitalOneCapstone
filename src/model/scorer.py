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
        return float(
            np.searchsorted(self.calibration_scores, prob, side="right")
            / len(self.calibration_scores)
        )

    def score(self, tx: dict[str, Any]) -> float:
        # Only pass features the model expects (NO timestamp)
        frame = pd.DataFrame([{
            "amount": tx.get("amount"),
            "merchant": tx.get("merchant"),
            "location": tx.get("location"),
        }])

        prob = float(self.model.predict_proba(frame)[:, 1][0])
        return round(self._to_uniform_percentile(prob), 4)