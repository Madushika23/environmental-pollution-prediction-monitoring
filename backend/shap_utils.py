
"""
shap_utils.py

Provides prediction-explanation utilities using SHAP
(SHapley Additive exPlanations).

The module helps explain individual model predictions by
showing how input features contribute to the prediction.

These explanations complement overall feature importance
by focusing on the contribution of features to a specific
prediction.
"""


import numpy as np
import shap


def explain_instance(model, X, predicted_class_index=None):
    """
    model: fitted XGBoost model (regressor or classifier)
    X: pandas DataFrame, exactly one row, columns in the model's feature order
    predicted_class_index: the class the model actually predicted (0, 1, 2...)
                            for classifiers. Leave as None for regression.

    Returns a list of {"feature": ..., "contribution": ...} sorted by
    absolute size, descending. Positive = pushed the result toward what
    the model actually predicted. Negative = pushed against it.
    """
    explainer = shap.TreeExplainer(model)
    raw = explainer.shap_values(X)
    arr = np.array(raw)

    if arr.ndim == 3:
        # Multiclass classifier: shape is (1, n_features, n_classes)
        idx = predicted_class_index if predicted_class_index is not None else 0
        values = arr[0, :, idx]
    else:
        # Regression, or binary classifier -- shap_values() gives the
        # contribution toward class 1 by convention, regardless of which
        # class was actually predicted, so flip the sign when class 0 won.
        values = arr[0]
        if predicted_class_index == 0:
            values = -values

    contributions = [
        {"feature": f, "contribution": round(float(v), 4)}
        for f, v in zip(X.columns.tolist(), values)
    ]
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions
