from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = ["amount", "merchant", "location", "timestamp"]
LABEL = "is_fraud"


def build_pipeline() -> Pipeline:
    numeric_cols = ["amount", "timestamp"]
    categorical_cols = ["merchant", "location"]

    preprocess = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def main(data_path: str, out_path: str) -> None:
    df = pd.read_csv(data_path)
    missing = [c for c in FEATURES + [LABEL] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    x = df[FEATURES]
    y = df[LABEL]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    model = build_pipeline()
    model.fit(x_train, y_train)

    test_probs = model.predict_proba(x_test)[:, 1]
    test_pred = (test_probs >= 0.5).astype(int)
    print(f"ROC AUC: {roc_auc_score(y_test, test_probs):.4f}")
    print(classification_report(y_test, test_pred))

    calibration_scores = sorted(model.predict_proba(x_train)[:, 1].tolist())
    artifact = {"model": model, "calibration_scores": calibration_scores}
    joblib.dump(artifact, out_path)
    print(f"Saved model artifact to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to csv dataset")
    parser.add_argument("--out", required=True, help="Path to save model artifact")
    args = parser.parse_args()
    main(args.data, args.out)
