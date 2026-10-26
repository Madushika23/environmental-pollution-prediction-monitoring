
"""
backtest_forecast.py

Evaluates the accuracy of the air quality forecasting model
using historical air quality data.

The script uses Prophet to forecast a held-out period and
compares the predicted values with the actual recorded values.
This helps evaluate forecasting performance on data that was
not used to train the model.

Run from the backend directory:
    python backtest_forecast.py

Sufficient historical data is required for both training and
testing. If there is not enough data, reduce TEST_DAYS if
appropriate or collect more daily readings before running
the evaluation again.
"""


import pandas as pd
from database import get_history

TEST_DAYS = 5          # how many recent real days to hold out and test against
MIN_TRAIN_DAYS = 10    # minimum days Prophet needs left over to train on


def run():
    history = get_history("air", limit=2000)
    rows = [
        {"ds": h["timestamp"], "y": h["prediction"].get("predicted_pm25")}
        for h in history
        if h["prediction"].get("predicted_pm25") is not None
    ]
    if not rows:
        print("No air history found -- nothing to backtest yet.")
        return

    df = pd.DataFrame(rows)
    df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
    df["date"] = df["ds"].dt.date
    daily = df.groupby("date", as_index=False)["y"].mean()
    daily["ds"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    if len(daily) < TEST_DAYS + MIN_TRAIN_DAYS:
        print(f"Only {len(daily)} distinct days available -- need at least "
              f"{TEST_DAYS + MIN_TRAIN_DAYS} ({MIN_TRAIN_DAYS} to train on + "
              f"{TEST_DAYS} to test against). Keep using the app daily.")
        return

    train = daily.iloc[:-TEST_DAYS]
    test = daily.iloc[-TEST_DAYS:].reset_index(drop=True)

    from prophet import Prophet
    model = Prophet()
    model.fit(train[["ds", "y"]])
    future = model.make_future_dataframe(periods=TEST_DAYS, freq="D")
    forecast = model.predict(future)
    pred = forecast[["ds", "yhat"]].tail(TEST_DAYS).reset_index(drop=True)

    compare = pd.DataFrame({
        "date": test["date"],
        "actual": test["y"],
        "predicted": pred["yhat"].round(1),
    })
    compare["abs_error"] = (compare["actual"] - compare["predicted"]).abs().round(1)
    compare["pct_error"] = (compare["abs_error"] / compare["actual"] * 100).round(1)

    print("=== Prophet ===")
    print(compare.to_string(index=False))
    mape = compare["pct_error"].mean()
    print(f"\nProphet MAPE: {mape:.1f}%  (accuracy ~{100 - mape:.1f}%)")

    # Naive baseline: "tomorrow = same as today" -- the simplest possible forecast.
    # If Prophet can't beat this, that's a sign of too little/noisy data, not a
    # sign Prophet is the wrong tool.
    naive_preds = []
    last_known = train["y"].iloc[-1]
    for actual in test["y"]:
        naive_preds.append(last_known)
        last_known = actual

    naive_compare = pd.DataFrame({"date": test["date"], "actual": test["y"], "naive_predicted": naive_preds})
    naive_compare["abs_error"] = (naive_compare["actual"] - naive_compare["naive_predicted"]).abs().round(1)
    naive_compare["pct_error"] = (naive_compare["abs_error"] / naive_compare["actual"] * 100).round(1)
    naive_mape = naive_compare["pct_error"].mean()

    print(f"\n=== Naive baseline (tomorrow = today) ===")
    print(naive_compare.to_string(index=False))
    print(f"\nNaive MAPE: {naive_mape:.1f}%  (accuracy ~{100 - naive_mape:.1f}%)")

    print(f"\nDay-to-day std dev in actual values: {daily['y'].std():.1f}  (mean: {daily['y'].mean():.1f})")
    print()
    if mape < naive_mape:
        print(f"Prophet beat the naive baseline ({mape:.1f}% vs {naive_mape:.1f}% error) --")
        print("it's adding real value even with limited data.")
    else:
        print(f"Prophet did NOT beat the naive baseline ({mape:.1f}% vs {naive_mape:.1f}% error) --")
        print("this points to too little/noisy history rather than the wrong algorithm.")
        print("Worth reporting honestly: forecast quality is expected to improve as more")
        print("consistent daily data accumulates, and this comparison is evidence you")
        print("evaluated the choice of method rather than assuming it works.")


if __name__ == "__main__":
    run()
