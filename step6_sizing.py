import pandas as pd
import yfinance as yf

ACCOUNT_GBP = 10_000   # your OANDA practice balance
RISK = 0.01            # a typical 8-week move should make or lose 1% of the account

TICKERS = {"gold": "GC=F", "crude": "CL=F", "euro": "EURUSD=X",
           "pound": "GBPUSD=X", "yen": "JPY=X"}

prices = yf.download(list(TICKERS.values()), period="3y", auto_adjust=True, progress=False)["Close"]
weekly = prices.resample("W-FRI").last()
gbpusd = prices["GBPUSD=X"].dropna().iloc[-1]

print(f"Account £{ACCOUNT_GBP:,}: about £{ACCOUNT_GBP * RISK:,.0f} per typical 8-week move\n")
print(f"{'Market':<7}{'Typical 8-wk move':>19}{'Position (£)':>14}   OANDA units")

for market, ticker in TICKERS.items():
    move = weekly[ticker].pct_change(8, fill_method=None).std()  # typical 8-week % move
    size_gbp = ACCOUNT_GBP * RISK / move
    size_usd = size_gbp * gbpusd
    price = prices[ticker].dropna().iloc[-1]

    if market == "euro":
        units = f"{size_usd / price:,.0f} EUR/USD (euros)"
    elif market == "pound":
        units = f"{size_gbp:,.0f} GBP/USD (pounds)"
    elif market == "yen":
        units = f"{size_usd:,.0f} USD/JPY (dollars)"
    elif market == "gold":
        units = f"{size_usd / price:,.1f} XAU/USD (ounces)"
    else:
        units = f"{size_usd / price:,.0f} WTI (barrels)"

    print(f"{market:<7}{move * 100:>18.1f}%{size_gbp:>14,.0f}   {units}")