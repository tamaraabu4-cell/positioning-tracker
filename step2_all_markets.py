import requests
import pandas as pd

DISAGG = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"  # gold, oil
TFF = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"     # currencies, bonds

# name: (report, contract code, hedge-fund long column, hedge-fund short column)
MARKETS = {
    "gold":  (DISAGG, "088691", "m_money_positions_long_all", "m_money_positions_short_all"),
    "crude": (DISAGG, "067651", "m_money_positions_long_all", "m_money_positions_short_all"),
    "euro":  (TFF, "099741", "lev_money_positions_long", "lev_money_positions_short"),
    "yen":   (TFF, "097741", "lev_money_positions_long", "lev_money_positions_short"),
    "pound": (TFF, "096742", "lev_money_positions_long", "lev_money_positions_short"),
    "us10y": (TFF, "043602", "lev_money_positions_long", "lev_money_positions_short"),
}

START = "2010-01-01"
all_tables = []

for name, (url, code, long_col, short_col) in MARKETS.items():
    params = {
        "cftc_contract_market_code": code,
        "$where": f"report_date_as_yyyy_mm_dd >= '{START}'",
        "$order": "report_date_as_yyyy_mm_dd",
        "$limit": 5000,
    }
    rows = requests.get(url, params=params, timeout=60).json()

    if isinstance(rows, dict) or not rows:
        print(f"{name}: nothing usable came back -> {rows}")
        continue
    if long_col not in rows[0]:
        print(f"{name}: column names differ. Options: {[k for k in rows[0] if 'lev' in k or 'm_money' in k]}")
        continue

    df = pd.DataFrame(rows)
    table = pd.DataFrame({
        "date": pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.date,
        "market": name,
        "long": pd.to_numeric(df[long_col]),
        "short": pd.to_numeric(df[short_col]),
    })
    table["net"] = table["long"] - table["short"]
    all_tables.append(table)

    print(f"{name:<6} {rows[0]['market_and_exchange_names']}")
    print(f"       {len(table)} weeks, {table['date'].iloc[0]} to {table['date'].iloc[-1]}, latest net {table['net'].iloc[-1]:,}")

if all_tables:
    history = pd.concat(all_tables)
    history.to_csv("history.csv", index=False)
    print(f"\nSaved {len(history)} rows to history.csv")