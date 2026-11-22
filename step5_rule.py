import pandas as pd

COST = 0.1      # % per trade, rough allowance for spread and slippage
HOLD = "ret8"   # hold 8 weeks; change to "ret4" to test 4 weeks
MARKETS = ["euro", "yen", "pound", "gold", "crude"]  # 10-year left out (basis trade)

data = pd.read_csv("test_results.csv", parse_dates=["date"]).sort_values(["market", "date"])
data = data[data["market"].isin(MARKETS)]

zone_by_market = data.groupby("market")["zone"]
recent = pd.concat([zone_by_market.shift(k) for k in range(1, 5)], axis=1)
data["episode_start"] = (data["zone"] != "middle") & ~recent.eq(data["zone"], axis=0).any(axis=1)

trades = data[data["episode_start"]].dropna(subset=[HOLD]).copy()
trades["crowd"] = trades["zone"].map({"max long (>90)": 1, "max short (<10)": -1})
trades["ride"] = trades["crowd"] * trades[HOLD] - COST
trades["fade"] = -trades["crowd"] * trades[HOLD] - COST
trades["half"] = trades["date"].dt.year.map(lambda y: "2013-2020" if y <= 2020 else "2021-2026")

def report(t, label):
    print(f"{label:<10} trades {len(t):>3} | "
          f"ride: avg {t['ride'].mean():+.2f}%  win {(t['ride'] > 0).mean() * 100:.0f}% | "
          f"fade: avg {t['fade'].mean():+.2f}%  win {(t['fade'] > 0).mean() * 100:.0f}%")

report(trades, "All")
for half, t in trades.groupby("half"):
    report(t, half)
print()
for market, t in trades.groupby("market"):
    report(t, market)

trades.to_csv("trades.csv", index=False)