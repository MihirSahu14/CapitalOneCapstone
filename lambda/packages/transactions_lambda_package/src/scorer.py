import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import boto3
import numpy as np
import onnxruntime as rt

from src.config import settings

_scorer_instance = None

STATE_CENTROIDS = {
    "AL": (32.7794, -86.8287), "AK": (64.0685, -153.3694),
    "AZ": (34.2744, -111.6602), "AR": (34.8938, -92.4426),
    "CA": (37.1841, -119.4696), "CO": (38.9972, -105.5478),
    "CT": (41.6219, -72.7273), "DE": (38.9896, -75.5050),
    "FL": (28.6305, -82.4497), "GA": (32.6415, -83.4426),
    "HI": (20.2927, -156.3737), "ID": (44.3509, -114.6130),
    "IL": (40.0417, -89.1965), "IN": (39.8942, -86.2816),
    "IA": (42.0751, -93.4960), "KS": (38.4937, -98.3804),
    "KY": (37.5347, -85.3021), "LA": (31.0689, -91.9968),
    "ME": (45.3695, -69.2428), "MD": (39.0550, -76.7909),
    "MA": (42.2596, -71.8083), "MI": (44.3467, -85.4102),
    "MN": (46.2807, -94.3053), "MS": (32.7364, -89.6678),
    "MO": (38.3566, -92.4580), "MT": (47.0527, -109.6333),
    "NE": (41.5378, -99.7951), "NV": (39.3289, -116.6312),
    "NH": (43.6805, -71.5811), "NJ": (40.1907, -74.6728),
    "NM": (34.4071, -106.1126), "NY": (42.9538, -75.5268),
    "NC": (35.5557, -79.3877), "ND": (47.4501, -100.4659),
    "OH": (40.2862, -82.7937), "OK": (35.5889, -97.4943),
    "OR": (43.9336, -120.5583), "PA": (40.8781, -77.7996),
    "RI": (41.6762, -71.5562), "SC": (33.9169, -80.8964),
    "SD": (44.4443, -100.2263), "TN": (35.8580, -86.3505),
    "TX": (31.4757, -99.3312), "UT": (39.3210, -111.0937),
    "VT": (44.0687, -72.6658), "VA": (37.5215, -78.8537),
    "WA": (47.3826, -120.4472), "WV": (38.6409, -80.6227),
    "WI": (44.6243, -89.9941), "WY": (42.9957, -107.5512),
    "DC": (38.9072, -77.0369),
}

# Geographic center of contiguous US — safe default for unknown states
DEFAULT_CENTROID = (39.5, -98.35)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


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
            print("Downloading model.onnx from S3...")
            s3.download_file(settings.model_s3_bucket, "model.onnx", model_path)

        if not os.path.exists(calib_path):
            print("Downloading calibration_scores.npy from S3...")
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

        # Compute distance: home state centroid → merchant state centroid
        tx_state = tx.get("state", "")
        home_state = tx.get("home_state", "")
        merch_lat, merch_lng = STATE_CENTROIDS.get(tx_state, DEFAULT_CENTROID)
        home_lat, home_lng = STATE_CENTROIDS.get(home_state, DEFAULT_CENTROID)
        distance = haversine(home_lat, home_lng, merch_lat, merch_lng)

        # Compute age from dob stored on account
        dob_str = tx.get("dob", "")
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = (now.replace(tzinfo=None) - dob).days / 365.25
        except (ValueError, TypeError):
            age = 35.0  # fallback to population median if dob missing

        inputs = {
            "amount": np.array([[tx.get("amount", 0.0)]], dtype=np.float32),
            "hour": np.array([[float(now.hour)]], dtype=np.float32),
            "day_of_week": np.array([[float(now.weekday())]], dtype=np.float32),
            "distance": np.array([[distance]], dtype=np.float32),
            "age": np.array([[age]], dtype=np.float32),
            "merchant": np.array([[tx.get("merchant", "")]], dtype=object),
            "category": np.array([[tx.get("category", "")]], dtype=object),
            "state": np.array([[tx_state]], dtype=object),
        }

        prob = float(self.session.run(["probabilities"], inputs)[0][0][1])
        return round(self._to_percentile(prob), 4)


def get_scorer() -> FraudScorer:
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = FraudScorer.load()
    return _scorer_instance