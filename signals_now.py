import pandas as pd
import yfinance as yf

TICKERS = {"gold": "GC=F", "crude": "CL=F", "euro": "EURUSD=X",
           "pound": "GBPUSD=X", "yen": "JPY=X"}

data = pd.read_csv("test_results.csv", parse_dates=["date"]).sort_values(["market", "date"])
data = data[data["market"] != "us10y"]

zone_by_market = data.groupby("market")["zone"]
recent = pd.concat([zone_by_market.shift(k) for k in range(1, 5)], axis=1)
data["episode_start"] = (data["zone"] != "middle") & ~recent.eq(data["zone"], axis=0).any(axis=1)

cutoff = data["date"].max() - pd.Timedelta(weeks=8)
live = data[data["episode_start"] & (data["date"] > cutoff)]

if live.empty:
    print("No signals in the last 8 weeks")

for _, r in live.iterrows():
    side = 1 if r["zone"].startswith("max long") else -1
    entry_day = r["date"] + pd.Timedelta(days=3)  # Friday release
    exit_day = entry_day + pd.Timedelta(weeks=8)

    prices = yf.Ticker(TICKERS[r["market"]]).history(start=entry_day - pd.Timedelta(days=7))["Close"]
    prices.index = prices.index.tz_localize(None)
    entry, now = prices.asof(entry_day), prices.iloc[-1]

    move = (entry / now - 1) if r["market"] == "yen" else (now / entry - 1)  # yen flipped: up = yen stronger
    pnl = side * move * 100

    print(f"{r['market']:<6} {'BUY' if side == 1 else 'SELL'}  "
          f"entry {entry:.4f} on {entry_day.date()}  now {now:.4f}  "
          f"P&L {pnl:+.2f}%  exit around {exit_day.date()}")