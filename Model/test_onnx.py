import numpy as np
import pandas as pd
import onnxruntime as rt
from sklearn.metrics import classification_report, roc_auc_score

TEST_PATH   = "archive/fraudTest.csv"
ONNX_PATH   = "data/processed/model.onnx"
CALIB_PATH  = "data/processed/calibration_scores.npy"

SOURCE_FEATURES = [
    "amt", "merchant", "category", "city", "state",
    "city_pop", "lat", "long", "merch_lat", "merch_long",
    "trans_date_trans_time", "dob", "is_fraud",
]

NUMERIC_FEATURES     = ["amount", "city_pop", "hour", "day_of_week", "distance", "age"]
CATEGORICAL_FEATURES = ["merchant", "category", "state"]


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["trans_date_trans_time"])
    df["hour"]        = dt.dt.hour
    df["day_of_week"] = dt.dt.dayofweek
    df["distance"]    = haversine_distance(
        df["lat"], df["long"], df["merch_lat"], df["merch_long"]
    )
    dob = pd.to_datetime(df["dob"])
    df["age"] = (dt - dob).dt.days / 365.25
    return df


def load_frame(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=SOURCE_FEATURES)
    df = df.rename(columns={"amt": "amount"})
    df = engineer_features(df)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["is_fraud"])
    df["is_fraud"] = df["is_fraud"].astype(int)
    return df


def main():
    print("Loading test data...")
    df = load_frame(TEST_PATH)
    y_true = df["is_fraud"].values

    print("Loading ONNX model...")
    session = rt.InferenceSession(ONNX_PATH)
    calibration_scores = np.load(CALIB_PATH)

    inputs = {
        "amount":      df["amount"].values.astype(np.float64).reshape(-1, 1),
        "city_pop":    df["city_pop"].values.astype(np.float64).reshape(-1, 1),
        "hour":        df["hour"].values.astype(np.float64).reshape(-1, 1),
        "day_of_week": df["day_of_week"].values.astype(np.float64).reshape(-1, 1),
        "distance":    df["distance"].values.astype(np.float64).reshape(-1, 1),
        "age":         df["age"].values.astype(np.float64).reshape(-1, 1),
        "merchant":    df["merchant"].values.reshape(-1, 1),
        "category":    df["category"].values.reshape(-1, 1),
        "state":       df["state"].values.reshape(-1, 1),
    }

    print("Running inference...")
    probs = session.run(["probabilities"], inputs)[0][:, 1]

    percentile_scores = np.searchsorted(calibration_scores, probs) / len(calibration_scores)

    preds = (probs >= 0.5).astype(int)
    print(f"\nTotal: {len(y_true):,}  Fraud: {y_true.sum():,}")
    print(f"ROC AUC: {roc_auc_score(y_true, probs):.4f}")
    print(classification_report(y_true, preds))

    print("Sample scores (first 5):")
    for i in range(5):
        print(f"  prob={probs[i]:.4f}  percentile={percentile_scores[i]:.4f}  actual={y_true[i]}")


if __name__ == "__main__":
    main()