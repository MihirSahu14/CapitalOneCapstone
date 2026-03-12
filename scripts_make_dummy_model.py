from __future__ import annotations

import os

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = "data/raw/fraudTest.csv"
MODEL_PATH = "data/processed/model.joblib"

SOURCE_FEATURES = ["amt", "merchant", "city", "is_fraud"]
MODEL_FEATURES = ["amount", "merchant", "location"]


def build_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), ["amount"]),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["merchant", "location"]),
        ],
        remainder="drop",
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def load_training_frame(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=SOURCE_FEATURES)
    df = df.rename(columns={"amt": "amount", "city": "location"})
    df = df.dropna(subset=MODEL_FEATURES + ["is_fraud"])
    df["is_fraud"] = df["is_fraud"].astype(int)
    return df


def main() -> None:
    df = load_training_frame(DATA_PATH)
    x = df[MODEL_FEATURES]
    y = df["is_fraud"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = build_pipeline()
    model.fit(x_train, y_train)

    test_probs = model.predict_proba(x_test)[:, 1]
    test_pred = (test_probs >= 0.5).astype(int)
    print(f"Trained on {len(x_train):,} rows, tested on {len(x_test):,} rows")
    print(f"ROC AUC: {roc_auc_score(y_test, test_probs):.4f}")
    print(classification_report(y_test, test_pred))

    calibration_scores = sorted(model.predict_proba(x_train)[:, 1].tolist())
    artifact = {
        "model": model,
        "calibration_scores": calibration_scores,
    }

    os.makedirs("data/processed", exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    print(f"Wrote {MODEL_PATH}")


if __name__ == "__main__":
    main()
