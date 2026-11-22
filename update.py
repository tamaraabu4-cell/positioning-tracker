"""Weekly update: CFTC positioning -> crowding gauges -> Rule v1 signals -> positioning.json

Runs every Saturday on GitHub Actions (and on Tuesdays, to catch reports delayed by US holidays).
"""
import json
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf

DISAGG = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"  # gold, oil
TFF = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"     # currencies, bonds
MANAGED_MONEY = ("m_money_positions_long_all", "m_money_positions_short_all")
LEVERAGED_FUNDS = ("lev_money_positions_long", "lev_money_positions_short")

# name: (report, contract code, hedge-fund columns, price ticker, OANDA instrument, traded by Rule v1)
MARKETS = {
    "gold":  (DISAGG, "088691", MANAGED_MONEY,   "GC=F",     "XAU/USD", True),
    "crude": (DISAGG, "067651", MANAGED_MONEY,   "CL=F",     "WTI",     True),
    "euro":  (TFF,    "099741", LEVERAGED_FUNDS, "EURUSD=X", "EUR/USD", True),
    "yen":   (TFF,    "097741", LEVERAGED_FUNDS, "JPY=X",    "USD/JPY", True),
    "pound": (TFF,    "096742", LEVERAGED_FUNDS, "GBPUSD=X", "GBP/USD", True),
    "us10y": (TFF,    "043602", LEVERAGED_FUNDS, "ZN=F",     None,      False),  # basis trade: shown, not traded
}

START = "2010-01-01"
WINDOW = 156        # 3 years of weekly reports for the gauge
HOLD_WEEKS = 8      # Rule v1 holding period
ACCOUNT_GBP = 10_000
RISK = 0.01         # a typical 8-week move should make or lose 1% of the account


def fetch_positions():
    """Every week since 2010, hedge-fund long / short / net for each market."""
    tables = []
    for name, (url, code, (long_col, short_col), *_rest) in MARKETS.items():
        params = {
            "cftc_contract_market_code": code,
            "$where": f"report_date_as_yyyy_mm_dd >= '{START}'",
            "$order": "report_date_as_yyyy_mm_dd",
            "$limit": 5000,
        }
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            raise RuntimeError(f"No CFTC data came back for {name}")

        df = pd.DataFrame(rows)
        tables.append(pd.DataFrame({
            "date": pd.to_datetime(df["report_date_as_yyyy_mm_dd"]),
            "market": name,
            "long": pd.to_numeric(df[long_col]),
            "short": pd.to_numeric(df[short_col]),
        }))

    history = pd.concat(tables, ignore_index=True)
    history["net"] = history["long"] - history["short"]
    return history.sort_values(["market", "date"]).reset_index(drop=True)


def add_gauge(history):
    """Crowding gauge (0-100 vs the last 3 years), weekly change, zone and episode starts."""
    net = history.groupby("market")["net"]
    low = net.transform(lambda s: s.rolling(WINDOW).min())
    high = net.transform(lambda s: s.rolling(WINDOW).max())
    history["gauge"] = ((history["net"] - low) / (high - low) * 100).round()
    history["change"] = net.diff()

    history["zone"] = "middle"
    history.loc[history["gauge"] > 90, "zone"] = "max long"
    history.loc[history["gauge"] < 10, "zone"] = "max short"

    # New episode = entering an extreme zone not seen in the previous 4 weeks
    zones = history.groupby("market")["zone"]
    recent = pd.concat([zones.shift(k) for k in range(1, 5)], axis=1)
    history["episode_start"] = (history["zone"] != "middle") & ~recent.eq(history["zone"], axis=0).any(axis=1)
    return history


def get_prices():
    """Daily closes for the last 3 years. Returns None if Yahoo fails, so the CFTC part still saves."""
    tickers = [m[3] for m in MARKETS.values()]
    try:
        prices = yf.download(tickers, period="3y", auto_adjust=True, progress=False)["Close"]
        if prices.empty:
            raise RuntimeError("empty price download")
        return prices
    except Exception as error:
        print(f"WARNING: prices unavailable ({error}) - saving positioning without P&L and sizes")
        return None


def open_signals(history, prices):
    """Rule v1 trades still inside their 8-week hold, with running P&L if prices are available."""
    latest = history["date"].max()
    starts = history[history["episode_start"] & (history["date"] > latest - pd.Timedelta(weeks=HOLD_WEEKS))]

    signals = []
    for _, r in starts.iterrows():
        _, _, _, ticker, instrument, traded = MARKETS[r["market"]]
        if not traded:
            continue

        side = 1 if r["zone"] == "max long" else -1
        entry_day = r["date"] + pd.Timedelta(days=3)  # report comes out on Friday
        # USD/JPY is the dollar priced in yen, so the order side flips for yen
        order_side = side * (-1 if r["market"] == "yen" else 1)

        signal = {
            "market": r["market"],
            "crowd": r["zone"],
            "side": "BUY" if side == 1 else "SELL",
            "oanda_order": f"{'BUY' if order_side == 1 else 'SELL'} {instrument}",
            "signal_report": r["date"].date().isoformat(),
            "entry_date": entry_day.date().isoformat(),
            "exit_date": (entry_day + pd.Timedelta(weeks=HOLD_WEEKS)).date().isoformat(),
            "new_this_week": bool(r["date"] == latest),
            "entry_price": None,
            "latest_price": None,
            "pnl_pct": None,
        }

        if prices is not None:
            s = prices[ticker].dropna()
            entry, now = s.asof(entry_day), s.iloc[-1]
            move = (entry / now - 1) if r["market"] == "yen" else (now / entry - 1)  # yen: up = yen stronger
            signal.update({
                "entry_price": round(float(entry), 5),
                "latest_price": round(float(now), 5),
                "pnl_pct": round(float(side * move * 100), 2),
            })

        signals.append(signal)
    return signals


def position_sizes(prices):
    """Size so a typical 8-week move makes or loses RISK of the account in every market."""
    if prices is None:
        return {}
    weekly = prices.resample("W-FRI").last()
    gbpusd = prices["GBPUSD=X"].dropna().iloc[-1]

    sizes = {}
    for name, (_, _, _, ticker, instrument, traded) in MARKETS.items():
        if not traded:
            continue
        move = weekly[ticker].pct_change(HOLD_WEEKS, fill_method=None).std()
        size_gbp = ACCOUNT_GBP * RISK / move
        size_usd = size_gbp * gbpusd
        price = prices[ticker].dropna().iloc[-1]
        units = {
            "euro": size_usd / price,   # euros
            "pound": size_gbp,          # pounds
            "yen": size_usd,            # dollars (USD/JPY)
            "gold": size_usd / price,   # ounces
            "crude": size_usd / price,  # barrels
        }[name]
        sizes[name] = {
            "instrument": instrument,
            "typical_8w_move_pct": round(float(move * 100), 1),
            "size_gbp": round(float(size_gbp)),
            "oanda_units": round(float(units), 1),
        }
    return sizes


def main():
    history = add_gauge(fetch_positions())
    prices = get_prices()
    latest = history["date"].max()

    markets = []
    for _, r in history[history["date"] == latest].iterrows():
        markets.append({
            "market": r["market"],
            "long": int(r["long"]),
            "short": int(r["short"]),
            "net": int(r["net"]),
            "change": int(r["change"]),
            "gauge": int(r["gauge"]),
            "zone": r["zone"],
            "traded": MARKETS[r["market"]][5],
        })

    # Last 3 years of net position and gauge, for the project page charts
    charts = {}
    for name, t in history[history["date"] > latest - pd.Timedelta(weeks=WINDOW)].groupby("market"):
        charts[name] = {
            "dates": t["date"].dt.strftime("%Y-%m-%d").tolist(),
            "net": t["net"].astype(int).tolist(),
            "gauge": t["gauge"].astype(int).tolist(),
        }

    output = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "report_date": latest.date().isoformat(),
        "rule": "Rule v1: ride the crowd at extremes (gauge >90 or <10), hold 8 weeks",
        "markets": markets,
        "open_signals": open_signals(history, prices),
        "sizes": position_sizes(prices),
        "history": charts,
    }

    with open("positioning.json", "w") as f:
        json.dump(output, f, indent=2)

    saved = history[["date", "market", "long", "short", "net", "gauge", "change"]].copy()
    saved["date"] = saved["date"].dt.date
    saved.to_csv("history.csv", index=False)

    # Summary for the Actions log
    print(f"Report date {output['report_date']}")
    for m in markets:
        print(f"  {m['market']:<6} net {m['net']:>12,}  change {m['change']:>10,}  gauge {m['gauge']:>3}  {m['zone']}")
    for s in output["open_signals"]:
        flag = "NEW " if s["new_this_week"] else ""
        pnl = f"{s['pnl_pct']:+.2f}%" if s["pnl_pct"] is not None else "n/a"
        print(f"  {flag}signal: {s['market']} {s['side']} ({s['oanda_order']}), exit {s['exit_date']}, P&L {pnl}")


if __name__ == "__main__":
    main()