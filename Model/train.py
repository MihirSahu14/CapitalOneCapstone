import os

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import DoubleTensorType, StringTensorType

TRAIN_PATH = "archive/fraudTrain.csv"
TEST_PATH  = "archive/fraudTest.csv"
ONNX_PATH  = "data/processed/model.onnx"
CALIB_PATH = "data/processed/calibration_scores.npy"

SOURCE_FEATURES = [
    "amt", "merchant", "category", "city", "state",
    "city_pop", "lat", "long", "merch_lat", "merch_long",
    "trans_date_trans_time", "dob", "is_fraud",
]

NUMERIC_FEATURES     = ["amount", "city_pop", "hour", "day_of_week", "distance", "age"]
CATEGORICAL_FEATURES = ["merchant", "category", "state"]
MODEL_FEATURES       = NUMERIC_FEATURES + CATEGORICAL_FEATURES


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
    df = df.dropna(subset=MODEL_FEATURES + ["is_fraud"])
    df["is_fraud"] = df["is_fraud"].astype(int)
    return df


def build_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline(steps=[
        ("preprocess", preprocess),
        ("clf", RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            min_samples_split=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def evaluate(label: str, model: Pipeline, x: pd.DataFrame, y: pd.Series) -> None:
    probs = model.predict_proba(x)[:, 1]
    preds = (probs >= 0.5).astype(int)
    print(f"\n--- {label} ---")
    print(f"ROC AUC: {roc_auc_score(y, probs):.4f}")
    print(classification_report(y, preds))


def main() -> None:
    print("Loading training data...")
    train_df = load_frame(TRAIN_PATH)
    x = train_df[MODEL_FEATURES]
    y = train_df["is_fraud"]

    print(f"Training on {len(x):,} rows...")
    model = build_pipeline()
    model.fit(x, y)

    print("\nLoading held-out test data...")
    test_df = load_frame(TEST_PATH)
    evaluate("Held-out Test Set", model, test_df[MODEL_FEATURES], test_df["is_fraud"])

    # Save calibration scores from full training set
    print("\nSaving calibration scores...")
    probs_train = model.predict_proba(x)[:, 1]
    calibration_scores = np.sort(probs_train)

    # Export to ONNX
    print("Exporting to ONNX...")
    initial_types = [
        ("amount",      DoubleTensorType([None, 1])),
        ("city_pop",    DoubleTensorType([None, 1])),
        ("hour",        DoubleTensorType([None, 1])),
        ("day_of_week", DoubleTensorType([None, 1])),
        ("distance",    DoubleTensorType([None, 1])),
        ("age",         DoubleTensorType([None, 1])),
        ("merchant",    StringTensorType([None, 1])),
        ("category",    StringTensorType([None, 1])),
        ("state",       StringTensorType([None, 1])),
    ]
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_types,
        target_opset=12,
        options={id(model): {"zipmap": False}}
    )
    with open(ONNX_PATH, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Saved → {ONNX_PATH}")


if __name__ == "__main__":
    main()