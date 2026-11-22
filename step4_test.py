import pandas as pd
import yfinance as yf

# The price that moves the same way as the hedge funds' bet
TICKERS = {"gold": "GC=F", "crude": "CL=F", "euro": "EURUSD=X",
           "pound": "GBPUSD=X", "yen": "JPY=X", "us10y": "ZN=F"}

history = pd.read_csv("history.csv", parse_dates=["date"]).dropna(subset=["gauge"])

prices = yf.download(list(TICKERS.values()), start="2010-01-01",
                     auto_adjust=True, progress=False)["Close"]
prices["JPY=X"] = 1 / prices["JPY=X"]  # flip USD/JPY so "up" means the yen got stronger

results = []
for market, ticker in TICKERS.items():
    s = prices[ticker].dropna()
    t = history[history["market"] == market].copy()

    entry_day = pd.DatetimeIndex(t["date"] + pd.Timedelta(days=3))  # report comes out Friday
    t["entry"] = s.asof(entry_day).values
    for weeks in (4, 8):
        exit_day = entry_day + pd.Timedelta(weeks=weeks)
        ret = (s.asof(exit_day).values / t["entry"] - 1) * 100
        ret[exit_day > s.index[-1]] = float("nan")  # that future hasn't happened yet
        t[f"ret{weeks}"] = ret
    results.append(t)

data = pd.concat(results)

def zone(g):
    if g < 10:
        return "max short (<10)"
    if g > 90:
        return "max long (>90)"
    return "middle"

data["zone"] = data["gauge"].apply(zone)

up = lambda r: (r.dropna() > 0).mean() * 100
summary = data.groupby(["market", "zone"]).agg(
    weeks=("ret4", "count"),
    avg_4w=("ret4", "mean"),
    up_4w=("ret4", up),
    avg_8w=("ret8", "mean"),
    up_8w=("ret8", up),
).round(1)

pd.set_option("display.width", 120)
print(summary)
data.to_csv("test_results.csv", index=False)