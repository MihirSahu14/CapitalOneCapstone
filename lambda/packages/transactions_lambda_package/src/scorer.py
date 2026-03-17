import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import boto3
import numpy as np
import onnxruntime as rt

from src.config import settings

_scorer_instance = None


@dataclass
class FraudScorer:
    session: rt.InferenceSession
    calibration_scores: np.ndarray

    @classmethod
    def load(cls) -> "FraudScorer":
        model_path = "/tmp/model.onnx"
        calib_path = "/tmp/calibration_scores.npy"

        s3 = boto3.client("s3")

        if not os.path.exists(model_path):
            print(f"Downloading model.onnx from S3...")
            s3.download_file(settings.model_s3_bucket, "model.onnx", model_path)

        if not os.path.exists(calib_path):
            print(f"Downloading calibration_scores.npy from S3...")
            s3.download_file(settings.model_s3_bucket, "calibration_scores.npy", calib_path)

        session = rt.InferenceSession(model_path)
        calibration_scores = np.load(calib_path)

        return cls(session=session, calibration_scores=calibration_scores)

    def _to_percentile(self, prob: float) -> float:
        return float(
            np.searchsorted(self.calibration_scores, prob, side="right")
            / len(self.calibration_scores)
        )

    def score(self, tx: dict[str, Any]) -> float:
        now = datetime.now(timezone.utc)

        inputs = {
            "amount":      np.array([[tx.get("amount", 0.0)]], dtype=np.float64),
            "city_pop":    np.array([[0.0]], dtype=np.float64),
            "hour":        np.array([[float(now.hour)]], dtype=np.float64),
            "day_of_week": np.array([[float(now.weekday())]], dtype=np.float64),
            "distance":    np.array([[0.0]], dtype=np.float64),
            "merchant":    np.array([[tx.get("merchant", "")]]),
            "category":    np.array([[tx.get("category", "")]]),
            "state":       np.array([[tx.get("state", "")]]),
        }

        prob = float(self.session.run(["probabilities"], inputs)[0][0][1])
        return round(self._to_percentile(prob), 4)


def get_scorer() -> FraudScorer:
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = FraudScorer.load()
    return _scorer_instance