
"""
water.py

Defines API routes for water quality prediction and live
monitoring.

The module loads the trained XGBoost model from
models/water_model.pkl and the associated label encoder
from models/water_label_encoder.pkl.

The model predicts whether water is classified as Safe
or Unsafe using temperature, conductivity, and pH.

The original dataset's labeling rule also considers dissolved
oxygen (DO), biochemical oxygen demand (BOD), and fecal
coliform. These measurements are not included in the current
sensor inputs because they require additional testing.

Available routes:

- /api/water/predict:
  Generates a prediction from supplied input values and
  saves the reading.

- /api/water/live-peek:
  Processes an incoming IoT sensor reading, updates the
  latest-reading cache, and saves the reading to the database.

- /api/water/live-latest:
  Returns the latest cached reading for the water monitoring
  interface.
"""


import os
import joblib
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify
from database import save_reading, get_history
from shap_utils import explain_instance

water_bp = Blueprint("water", __name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
)
model = joblib.load(os.path.join(MODELS_DIR, "water_model.pkl"))
label_encoder = joblib.load(os.path.join(MODELS_DIR, "water_label_encoder.pkl"))

FEATURE_ORDER = ["Temp", "Conductivity", "pH"]

_latest_live_reading = {"inputs": None, "prediction": None, "timestamp": None}


@water_bp.route("/api/water/predict", methods=["POST"])
def predict_water():
    data = request.get_json(force=True)
    source = data.get("source", "manual")

    temperature = float(data.get("temperature", 0))
    conductivity = float(data.get("conductivity", 0))
    ph = float(data.get("ph", 0))

    row = {"Temp": temperature, "Conductivity": conductivity, "pH": ph}
    X = pd.DataFrame([row], columns=FEATURE_ORDER)

    pred_encoded = model.predict(X)[0]
    category = label_encoder.inverse_transform([pred_encoded])[0]

    inputs = {"temperature": temperature, "conductivity": conductivity, "ph": ph}
    prediction = {"category": category}

    save_reading("water", source, inputs, prediction)

    return jsonify({"inputs": inputs, "prediction": prediction, "source": source})


@water_bp.route("/api/water/live-peek", methods=["POST"])
def live_peek_water():
    data = request.get_json(force=True)
    temperature = float(data.get("temperature", 0))
    conductivity = float(data.get("conductivity", 0))
    ph = float(data.get("ph", 0))

    row = {"Temp": temperature, "Conductivity": conductivity, "pH": ph}
    X = pd.DataFrame([row], columns=FEATURE_ORDER)

    pred_encoded = model.predict(X)[0]
    category = label_encoder.inverse_transform([pred_encoded])[0]

    inputs = {"temperature": temperature, "conductivity": conductivity, "ph": ph}
    prediction = {"category": category}

    _latest_live_reading["inputs"] = inputs
    _latest_live_reading["prediction"] = prediction
    _latest_live_reading["timestamp"] = datetime.now().isoformat()

    # Save every IoT reading straight to the database (no more 15-min wait).
    save_reading("water", "iot", inputs, prediction)

    return jsonify({"inputs": inputs, "prediction": prediction, "source": "iot"})


@water_bp.route("/api/water/live-latest", methods=["GET"])
def live_latest_water():
    if _latest_live_reading["inputs"] is None:
        return jsonify({"available": False})
    return jsonify({
        "available": True,
        "inputs": _latest_live_reading["inputs"],
        "prediction": _latest_live_reading["prediction"],
        "timestamp": _latest_live_reading["timestamp"],
    })


@water_bp.route("/api/water/explain", methods=["POST"])
def explain_water():
    data = request.get_json(force=True)
    temperature = float(data.get("temperature", 0))
    conductivity = float(data.get("conductivity", 0))
    ph = float(data.get("ph", 0))

    row = {"Temp": temperature, "Conductivity": conductivity, "pH": ph}
    X = pd.DataFrame([row], columns=FEATURE_ORDER)

    try:
        pred_encoded = int(model.predict(X)[0])
        contributions = explain_instance(model, X, predicted_class_index=pred_encoded)
        return jsonify({"contributions": contributions})
    except Exception as e:
        return jsonify({"error": f"Could not compute explanation: {e}"}), 500


@water_bp.route("/api/water/history", methods=["GET"])
def water_history():
    return jsonify(get_history(domain="water"))


@water_bp.route("/api/water/feature-importance")
def water_feature_importance():
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_ORDER, importances), key=lambda x: x[1], reverse=True)
    return jsonify([{"feature": f, "importance": round(float(i), 4)} for f, i in ranked])
