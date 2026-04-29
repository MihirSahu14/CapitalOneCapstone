"""
test_onnx.py — Validate the ONNX export of the XGBoost fraud detection pipeline.
Expected ROC AUC: ~0.9968
"""

import numpy as np
import pandas as pd
import onnxruntime as rt
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve

TEST_PATH  = "archive/fraudTest.csv"
ONNX_PATH  = "data/processed/20260416_175328/xgb_model.onnx"
CALIB_PATH = "data/processed/20260416_175328/calibration_scores.npy"

SOURCE_COLS = [
    "amt", "merchant", "category", "state",
    "lat", "long", "merch_lat", "merch_long",
    "trans_date_trans_time", "dob", "is_fraud",
]

NUMERIC_FEATURES     = ["amount", "hour", "day_of_week", "distance", "age"]
CATEGORICAL_FEATURES = ["merchant", "category", "state"]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["trans_date_trans_time"])
    df["hour"]        = dt.dt.hour.astype(float)
    df["day_of_week"] = dt.dt.dayofweek.astype(float)
    df["distance"]    = haversine_km(df["lat"], df["long"], df["merch_lat"], df["merch_long"])
    df["age"]         = (dt - pd.to_datetime(df["dob"])).dt.days / 365.25
    return df


def load_test_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=SOURCE_COLS)
    df = df.rename(columns={"amt": "amount"})
    df = engineer_features(df)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["is_fraud"])
    df["is_fraud"] = df["is_fraud"].astype(int)
    return df


def build_onnx_inputs(df: pd.DataFrame) -> dict:
    float_inputs = {
        name: df[name].values.astype(np.float32).reshape(-1, 1)
        for name in NUMERIC_FEATURES
    }
    str_inputs = {
        name: df[name].astype(str).values.reshape(-1, 1).astype(object)
        for name in CATEGORICAL_FEATURES
    }
    return {**float_inputs, **str_inputs}


def main() -> None:
    print("Loading test data...")
    df     = load_test_data(TEST_PATH)
    y_true = df["is_fraud"].values
    print(f"  Rows: {len(y_true):,}  |  Normal: {int((y_true==0).sum()):,}  |  Fraud: {int(y_true.sum()):,}")

    print("\nLoading ONNX model...")
    session            = rt.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
    calibration_scores = np.load(CALIB_PATH)
    print(f"  Inputs : {[i.name for i in session.get_inputs()]}")
    print(f"  Outputs: {[o.name for o in session.get_outputs()]}")

    print("\nRunning inference...")
    probs = session.run(["probabilities"], build_onnx_inputs(df))[0][:, 1]
    print(f"  Prob range: min={probs.min():.6f}  max={probs.max():.6f}  mean={probs.mean():.6f}")

    roc_auc = roc_auc_score(y_true, probs)
    preds   = (probs >= 0.5).astype(int)

    print(f"\n{'='*52}")
    print(f"  ROC AUC : {roc_auc:.4f}   (expected ≈ 0.9968)")
    if abs(roc_auc - 0.9968) > 0.002:
        print("  ⚠  WARNING: ROC AUC deviates — check ONNX export.")
    else:
        print("  ✓  ROC AUC within expected range — ONNX export looks correct.")
    print(f"{'='*52}")

    print("\nClassification report @ threshold=0.50:")
    print(classification_report(y_true, preds, target_names=["normal", "fraud"], digits=4))

    precision_vals, recall_vals, thresholds = precision_recall_curve(y_true, probs)
    print(f"{'Recall target':<18} {'Precision':<14} {'Threshold'}")
    print("-" * 48)
    for target in [0.90, 0.92, 0.95, 0.97, 0.99]:
        candidates = [(p, t) for p, r, t in zip(precision_vals, recall_vals, thresholds) if r >= target]
        if candidates:
            best_p, best_t = max(candidates, key=lambda x: x[0])
            print(f"{target*100:.0f}%{'':<15} {best_p:.4f}{'':<9} {best_t:.4f}")
        else:
            print(f"{target*100:.0f}%{'':<15} not achievable")

    percentiles = np.searchsorted(calibration_scores, probs) / len(calibration_scores)
    fraud_idx   = np.where(y_true == 1)[0][:5]
    normal_idx  = np.where(y_true == 0)[0][:5]
    print(f"\n{'Index':<8} {'Actual':<10} {'Prob':>8}  {'Percentile':>12}")
    print("-" * 44)
    for i in np.concatenate([fraud_idx, normal_idx]):
        label = "FRAUD" if y_true[i] == 1 else "normal"
        print(f"{i:<8} {label:<10} {probs[i]:>8.4f}  {percentiles[i]:>12.4f}")


if __name__ == "__main__":
    main()