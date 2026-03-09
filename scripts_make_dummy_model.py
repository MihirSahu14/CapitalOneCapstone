import os
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

# Numeric pipeline: scale amount
num_pipe = Pipeline([
    ("scaler", StandardScaler()),
])

pre = ColumnTransformer(
    transformers=[
        ("num", num_pipe, ["amount"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["merchant", "location"]),
    ],
    remainder="drop",
)

pipe = Pipeline([
    ("pre", pre),
    ("clf", LogisticRegression(max_iter=500)),
])

# Synthetic training data
df = pd.DataFrame([
    {"amount": 5.0,   "merchant": "Starbucks", "location": "Madison", "is_fraud": 0},
    {"amount": 12.0,  "merchant": "Target",    "location": "Madison", "is_fraud": 0},
    {"amount": 43.21, "merchant": "Walmart",   "location": "Chicago", "is_fraud": 0},
    {"amount": 250.0, "merchant": "Apple",     "location": "Chicago", "is_fraud": 1},
    {"amount": 800.0, "merchant": "BestBuy",   "location": "Chicago", "is_fraud": 1},
])

X = df[["amount", "merchant", "location"]]
y = df["is_fraud"].astype(int)

pipe.fit(X, y)

artifact = {
    "model": pipe,
    "calibration_scores": np.linspace(0, 1, 1001).tolist(),
}

os.makedirs("data/processed", exist_ok=True)
joblib.dump(artifact, "data/processed/model.joblib")
print("Wrote data/processed/model.joblib")