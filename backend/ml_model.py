"""
Lendmark ML Model — Random Forest Loan Approval Predictor
Trains on loan_approval_dataset.csv and exposes a predict() function.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "loan_approval_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "rf_model.joblib")
META_PATH = os.path.join(BASE_DIR, "rf_model_meta.json")

FEATURE_COLS = [
    "no_of_dependents",
    "education",
    "self_employed",
    "income_annum",
    "loan_amount",
    "loan_term",
    "cibil_score",
    "residential_assets_value",
    "commercial_assets_value",
    "luxury_assets_value",
    "bank_asset_value",
]


def load_and_clean_data():
    """Load CSV, strip whitespace, encode categoricals."""
    df = pd.read_csv(CSV_PATH)
    # Strip whitespace from column names and string columns
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


def train_model():
    """Train a Random Forest on the full dataset, save model + metadata."""
    df = load_and_clean_data()

    # Encode categoricals
    le_edu = LabelEncoder()
    le_se = LabelEncoder()
    df["education"] = le_edu.fit_transform(df["education"])       # Graduate=0, Not Graduate=1
    df["self_employed"] = le_se.fit_transform(df["self_employed"]) # No=0, Yes=1

    # Target
    le_target = LabelEncoder()
    df["loan_status"] = le_target.fit_transform(df["loan_status"])  # Approved=0, Rejected=1

    X = df[FEATURE_COLS]
    y = df["loan_status"]

    # Train/test split for metrics
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # Evaluate
    y_pred = rf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le_target.classes_, output_dict=True)
    cm = confusion_matrix(y_test, y_pred).tolist()

    # Feature importances
    importances = dict(zip(FEATURE_COLS, rf.feature_importances_.tolist()))

    # Save model
    joblib.dump({
        "model": rf,
        "le_education": le_edu,
        "le_self_employed": le_se,
        "le_target": le_target,
    }, MODEL_PATH)

    # Save metadata (accuracy, feature importances, etc.)
    meta = {
        "accuracy": round(accuracy * 100, 2),
        "feature_importances": importances,
        "classification_report": {
            k: v for k, v in report.items()
            if k in le_target.classes_.tolist() + ["weighted avg"]
        },
        "confusion_matrix": cm,
        "n_estimators": 200,
        "n_samples_train": len(X_train),
        "n_samples_test": len(X_test),
        "classes": le_target.classes_.tolist(),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Model trained — Accuracy: {meta['accuracy']}%")
    print(f"   Training samples: {len(X_train)}, Test samples: {len(X_test)}")
    print(f"   Saved to: {MODEL_PATH}")
    print(f"   Feature importances: {json.dumps(importances, indent=2)}")

    return rf, meta


# ─────────────────────────────────────────────
# RUNTIME PREDICTION
# ─────────────────────────────────────────────
_loaded = None  # Lazy-loaded cache


def _get_model():
    """Load the trained model from disk (cached)."""
    global _loaded
    if _loaded is not None:
        return _loaded

    if not os.path.exists(MODEL_PATH):
        print("⚠️  No saved model found — training now...")
        train_model()

    _loaded = joblib.load(MODEL_PATH)
    return _loaded


def get_model_meta():
    """Return model metadata (accuracy, feature importances, etc.)."""
    if not os.path.exists(META_PATH):
        train_model()
    with open(META_PATH, "r") as f:
        return json.load(f)


def predict(input_data: dict) -> dict:
    """
    Run a single prediction.

    input_data keys:
        no_of_dependents, education, self_employed,
        income_annum, loan_amount, loan_term, cibil_score,
        residential_assets_value, commercial_assets_value,
        luxury_assets_value, bank_asset_value

    Returns dict with: status, confidence, probability_of_default,
                       risk_score, feature_importance
    """
    bundle = _get_model()
    model = bundle["model"]
    le_edu = bundle["le_education"]
    le_se = bundle["le_self_employed"]
    le_target = bundle["le_target"]

    # Build feature row
    edu_val = input_data.get("education", "Graduate")
    se_val = input_data.get("self_employed", "No")

    # Handle unseen labels gracefully
    try:
        edu_encoded = le_edu.transform([edu_val])[0]
    except ValueError:
        edu_encoded = 0  # default to Graduate
    try:
        se_encoded = le_se.transform([se_val])[0]
    except ValueError:
        se_encoded = 0  # default to No

    features = np.array([[
        int(input_data.get("no_of_dependents", 0)),
        edu_encoded,
        se_encoded,
        float(input_data.get("income_annum", 0)),
        float(input_data.get("loan_amount", 0)),
        int(input_data.get("loan_term", 12)),
        int(input_data.get("cibil_score", 650)),
        float(input_data.get("residential_assets_value", 0)),
        float(input_data.get("commercial_assets_value", 0)),
        float(input_data.get("luxury_assets_value", 0)),
        float(input_data.get("bank_asset_value", 0)),
    ]])

    # Predict
    proba = model.predict_proba(features)[0]
    pred_class_idx = np.argmax(proba)
    pred_label = le_target.inverse_transform([pred_class_idx])[0]

    # Map probabilities — find index for each class
    class_list = le_target.classes_.tolist()
    approved_idx = class_list.index("Approved") if "Approved" in class_list else 0
    rejected_idx = class_list.index("Rejected") if "Rejected" in class_list else 1

    approval_prob = float(proba[approved_idx])
    rejection_prob = float(proba[rejected_idx])

    confidence = float(max(proba)) * 100

    # Risk score: higher = riskier (based on rejection probability)
    risk_score = round(rejection_prob * 100, 1)

    # Feature importances for this prediction
    importances = model.feature_importances_
    feature_labels = [
        "Dependents", "Education", "Employment",
        "Annual Income", "Loan Amount", "Loan Term",
        "Credit Score (CIBIL)", "Residential Assets",
        "Commercial Assets", "Luxury Assets", "Bank Assets"
    ]
    fi = sorted(
        zip(feature_labels, importances.tolist()),
        key=lambda x: x[1], reverse=True
    )

    return {
        "status": pred_label,
        "confidence": round(confidence, 1),
        "probability_of_default": round(rejection_prob * 100, 1),
        "risk_score": risk_score,
        "feature_importance": [
            {"feature": f, "importance": round(v * 100, 1)}
            for f, v in fi[:6]
        ],
    }


# ─────────────────────────────────────────────
# CLI: train if run directly
# ─────────────────────────────────────────────
if __name__ == "__main__":
    train_model()
