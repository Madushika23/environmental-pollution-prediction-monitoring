"""
soil.py
Soil fertility prediction route.

Loads the trained XGBoost model (models/soil_model.pkl). Predicts
Less Fertile / Fertile / Highly Fertile from 12 soil chemistry values:
N, P, K, pH, EC, OC, S, Zn, Fe, Cu, Mn, B.
"""

import os
import joblib
import pandas as pd
from flask import Blueprint, request, jsonify
from database import save_reading, get_history
from shap_utils import explain_instance

soil_bp = Blueprint("soil", __name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
)
model = joblib.load(os.path.join(MODELS_DIR, "soil_model.pkl"))

FEATURE_ORDER = ["N", "P", "K", "pH", "EC", "OC", "S", "Zn", "Fe", "Cu", "Mn", "B"]
LABEL_MAP = {0: "Less Fertile", 1: "Fertile", 2: "Highly Fertile"}


@soil_bp.route("/api/soil/predict", methods=["POST"])
def predict_soil():
    data = request.get_json(force=True)
    source = data.get("source", "manual")

    raw = {k: float(data.get(k, 0)) for k in FEATURE_ORDER}
    X = pd.DataFrame([raw], columns=FEATURE_ORDER)

    pred_encoded = int(model.predict(X)[0])
    category = LABEL_MAP[pred_encoded]

    prediction = {"category": category}
    save_reading("soil", source, raw, prediction)

    return jsonify({"inputs": raw, "prediction": prediction, "source": source})


@soil_bp.route("/api/soil/explain", methods=["POST"])
def explain_soil():
    data = request.get_json(force=True)
    raw = {k: float(data.get(k, 0)) for k in FEATURE_ORDER}
    X = pd.DataFrame([raw], columns=FEATURE_ORDER)

    try:
        pred_encoded = int(model.predict(X)[0])
        contributions = explain_instance(model, X, predicted_class_index=pred_encoded)
        return jsonify({"contributions": contributions})
    except Exception as e:
        return jsonify({"error": f"Could not compute explanation: {e}"}), 500


@soil_bp.route("/api/soil/history", methods=["GET"])
def soil_history():
    return jsonify(get_history(domain="soil"))


@soil_bp.route("/api/soil/feature-importance")
def soil_feature_importance():
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_ORDER, importances), key=lambda x: x[1], reverse=True)
    return jsonify([{"feature": f, "importance": round(float(i), 4)} for f, i in ranked])