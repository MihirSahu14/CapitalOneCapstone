from __future__ import annotations

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TRAIN_PATH = "archive/fraudTrain.csv"
TEST_PATH  = "archive/fraudTest.csv"
MODEL_PATH = "data/processed/model.joblib"

SOURCE_FEATURES = [
    "amt", "merchant", "category", "city", "state",
    "city_pop", "lat", "long", "merch_lat", "merch_long",
    "trans_date_trans_time", "dob", "is_fraud",
]

NUMERIC_FEATURES     = ["amount", "city_pop", "hour", "day_of_week", "distance"]
CATEGORICAL_FEATURES = ["merchant", "category", "state"]
MODEL_FEATURES       = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def haversine_distance(lat1, lon1, lat2, lon2):
    """Compute distance in km between two lat/lon points."""
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
    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


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

    x_train, x_val, y_train, y_val = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training on {len(x_train):,} rows...")
    model = build_pipeline()
    model.fit(x_train, y_train)

    evaluate("Validation Set", model, x_val, y_val)

    print("\nLoading held-out test data...")
    test_df = load_frame(TEST_PATH)
    evaluate("Held-out Test Set", model, test_df[MODEL_FEATURES], test_df["is_fraud"])

    print("\nSaving model artifact...")
    calibration_scores = sorted(model.predict_proba(x_train)[:, 1].tolist())
    artifact = {"model": model, "calibration_scores": calibration_scores}
    os.makedirs("data/processed", exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    print(f"Wrote {MODEL_PATH}")


if __name__ == "__main__":
    main()