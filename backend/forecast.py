"""
forecast.py
Prophet-based forecasting, reading straight from the domain's own table.
Simplified to daily-only, short-horizon (tomorrow + day after) forecasting.

Multiple readings can land on the same calendar day (e.g. from testing
the app several times in one sitting, or at different times of day).
Prophet expects one y-value per date, so before fitting we collapse
history down to one reading per day -- using the AVERAGE of that day's
readings, not just the latest one. Air pollution genuinely varies by
time of day (traffic, temperature inversions, etc.), so averaging
removes that time-of-day noise instead of letting whichever moment
happened to be tested last stand in for the whole day. All available
distinct days are used (no upper cap) -- only a minimum is enforced
before attempting a forecast.
"""

import pandas as pd
from database import get_history
from routes.air import classify_pm25

MIN_POINTS_FOR_FORECAST = 10   # minimum distinct days needed before forecasting

DOMAIN_VALUE_FIELD = {
    "water": "conductivity",
    "soil": "N",
}


def get_forecast(domain, periods=2):
    """Always daily granularity. periods=2 -> tomorrow + day after tomorrow."""
    history = get_history(domain, limit=2000)

    if domain == "air":
        rows = [
            {"ds": h["timestamp"], "y": h["prediction"].get("predicted_pm25")}
            for h in history
            if h["prediction"].get("predicted_pm25") is not None
        ]
    else:
        field = DOMAIN_VALUE_FIELD.get(domain)
        rows = [
            {"ds": h["timestamp"], "y": h["inputs"].get(field)}
            for h in history
            if h["inputs"].get(field) is not None
        ]

    if not rows:
        return {
            "ready": False,
            "message": f"No {domain} history yet. Keep using the app daily to build up data.",
        }

    df = pd.DataFrame(rows)
    df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
    df["date"] = df["ds"].dt.date

    # one reading per calendar day -- average of that day's readings, so a
    # single snapshot (morning vs. night) doesn't stand in for the whole day
    daily = df.groupby("date", as_index=False)["y"].mean()
    daily["ds"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    if len(daily) < MIN_POINTS_FOR_FORECAST:
        return {
            "ready": False,
            "message": (
                f"Not enough {domain} history yet ({len(daily)} distinct days, "
                f"need {MIN_POINTS_FOR_FORECAST}+ different days). "
                f"Keep using the app daily to build up data."
            ),
        }

    from prophet import Prophet

    model = Prophet()
    model.fit(daily[["ds", "y"]])
    future = model.make_future_dataframe(periods=periods, freq="D")
    forecast = model.predict(future)

    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

    forecast_list = []
    for _, row in result.iterrows():
        entry = {
            "date": str(row["ds"])[:10],
            "predicted_value": round(row["yhat"], 1),
            "range_low": round(max(row["yhat_lower"], 0), 1),   # pollution can't be negative
            "range_high": round(row["yhat_upper"], 1),
        }
        if domain == "air":
            aqi, category = classify_pm25(row["yhat"])
            entry["aqi_sl"] = aqi
            entry["category"] = category
        forecast_list.append(entry)

    return {"ready": True, "forecast": forecast_list}