import requests

URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"  # Disaggregated report, futures only
GOLD = "088691"  # COMEX gold contract code

params = {
    "cftc_contract_market_code": GOLD,
    "$order": "report_date_as_yyyy_mm_dd DESC",
    "$limit": 10,
}

rows = requests.get(URL, params=params, timeout=30).json()

if isinstance(rows, dict) or not rows:
    print("Nothing usable came back:", rows)
else:
    print(rows[0]["market_and_exchange_names"])
    print(f"{'Week':<12}{'Long':>10}{'Short':>10}{'Net':>10}")
    for r in reversed(rows):
        long_ = int(r["m_money_positions_long_all"])
        short = int(r["m_money_positions_short_all"])
        print(f"{r['report_date_as_yyyy_mm_dd'][:10]:<12}{long_:>10,}{short:>10,}{long_ - short:>10,}")