# Positioning Tracker

Every week, the US futures regulator (the CFTC) publishes how big traders are positioned in the futures market: who is betting prices go up, and who is betting they go down.

This repo turns that report into a **crowding gauge** for six markets in FX, gold, oil and bonds, tests whether extreme crowding predicts what prices do next, and runs one simple rule that I paper trade. It updates itself every week.

> Paper trading only. Nothing here is investment advice.

## The idea in one picture

Think of a tug-of-war. When nearly everyone is already pulling the same way, there is nobody left to join that side, and if the rope slips they all let go at once. Traders call that a *crowded trade*.

The question this project asks: **when hedge funds are at an extreme, is the crowd usually right, or about to be wrong?**

## Markets

| Market | CFTC contract | Who counts as "hedge funds" | Traded by Rule v1 |
|---|---|---|---|
| Gold | Gold, COMEX | Managed Money | Yes |
| Crude oil | Crude oil, light sweet, NYMEX | Managed Money | Yes |
| Euro | Euro FX, CME | Leveraged Funds | Yes |
| Yen | Japanese yen, CME | Leveraged Funds | Yes |
| Pound | British pound, CME | Leveraged Funds | Yes |
| US 10-year | 10-year Treasury note, CBOT | Leveraged Funds | No (see below) |

The CFTC uses two reports. Gold and oil come from the *Disaggregated* report, where hedge funds are called Managed Money. Currencies and bonds come from *Traders in Financial Futures*, where they are called Leveraged Funds.

**Why the 10-year isn't traded:** hedge funds hold a huge short in Treasury futures, but most of it is one half of the *basis trade* (buy the actual bonds, sell the futures, collect the small price gap). It looks like a giant bet that bonds will fall, but it isn't a view on bond prices at all. It's shown on the tracker as a basis trade monitor, not used as a signal.

## The crowding gauge

Raw positions can't be compared across markets: 100,000 contracts of gold and 100,000 of yen are very different bets. So each market is compared only with its own past three years:

$$
\text{gauge} = \frac{\text{net now} - \text{lowest net (3 yrs)}}{\text{highest net (3 yrs)} - \text{lowest net (3 yrs)}} \times 100
$$

- **100** means hedge funds are the most bullish they've been in three years.
- **0** means the most bearish.
- **Above 90 or below 10** counts as an extreme.

Net position = contracts betting up minus contracts betting down. Traders call this measure the *COT index*.

## What the data says (2013–2026)

The gauge needs three years of history, so the tests start in 2013. Each test asks: after the report came out (Friday, not the Tuesday the positions are dated), what did the price do over the next 4 and 8 weeks?

**1. Single-market patterns mostly didn't survive.** Looking at every week, some results looked impressive (gold rose in the 4 weeks after a max-long reading 71% of the time, against 51% normally). But when each extreme was counted once per episode and history was split into two halves (2013–2020 and 2021–2026), most of those patterns pointed the other way in one half. With 24 comparisons, a few will always look good by chance.

**2. So I tested one rule, the same for every market.** "Ride the crowd": when a market enters an extreme, trade in the crowd's direction. Costs of 0.1% per trade included.

| Hold | All trades | 2013–2020 | 2021–2026 |
|---|---|---|---|
| **8 weeks** | +0.18% per trade, wins 55% (85) | **+0.13%**, 57% (47) | **+0.23%**, 53% (38) |
| 4 weeks | +0.20%, 55% (86) | **−0.07%**, 55% (47) | +0.52%, 54% (39) |

Fading the crowd (the opposite trade) lost money in both halves.

Only the 8-week version made money in **both** halves. The 4-week version looks just as good overall, but all of that comes from 2021–2026, which is exactly the trap the two-halves check is there to catch.

**By market (8-week hold, riding the crowd):**

| Market | Trades | Avg per trade | Win rate |
|---|---|---|---|
| Gold | 18 | +2.01% | 67% |
| Euro | 19 | +1.06% | 58% |
| Yen | 19 | +0.24% | 63% |
| Pound | 13 | −1.12% | 38% |
| Crude | 16 | −1.96% | 44% |

**My honest reading:** the edge is small. A single 8-week move in these markets is often several percent, so +0.18% per trade over 85 trades is well within what luck alone could produce. That's good enough to paper trade as a test, not to claim a proven edge. Paper trading from here on is the real out-of-sample test.

Crude worked the other way: when funds were very bearish, oil tended to rally (a short squeeze). That fits a sensible story, but it was found by looking at the results, so it stays a watch item rather than a rule.

## Rule v1

- **Signal:** euro, yen, pound, gold or crude starts a new extreme episode (gauge above 90 or below 10, and not in that zone at any point in the previous 4 weeks).
- **Direction:** same side as the crowd.
- **Entry:** when the report comes out (Friday evening UK), in practice at the Sunday open.
- **Exit:** after 8 weeks.
- **Size:** each trade is sized so a typical 8-week move in that market makes or loses about 1% of the account. Crude moves about six times as much as the pound, so its position is much smaller.
- **No stop-loss in v1**, because the backtest didn't use one. The small size is the risk control.

Signals are rare: about six a year across all five markets. Most weeks the positioning read is context, not a trade.

## Trade log

| # | Market | Side | Signal (report date) | Entry | Entry price | Exit around | Status |
|---|---|---|---|---|---|---|---|
| 1 | Euro | Sell EUR/USD | 13 Oct 2026 (gauge 0) | 16 Oct 2026 | 1.1213 | 11 Dec 2026 | Open, +2.17% on 22 Nov |

Signal #1 was found five weeks after it started, so it is logged exactly as the rule would have traded it.

## How it runs

Every Saturday morning, GitHub Actions runs `update.py`, which:

1. Pulls every week since 2010 for all six markets from the CFTC.
2. Works out the gauges and the weekly change.
3. Finds Rule v1 trades that are still open, with their running profit or loss.
4. Works out position sizes for each market.
5. Saves everything to `positioning.json` and `history.csv`, and commits them back to this repo.

It also runs on Tuesdays, to pick up reports delayed by US holidays. If Yahoo's prices fail, the positioning data is still saved, and profit/loss and sizes are left empty for that week.

## Files

| File | What it is |
|---|---|
| `update.py` | The weekly job (everything below in one file) |
| `.github/workflows/weekly-update.yml` | The Saturday and Tuesday schedule |
| `positioning.json` | This week's readings, open signals, sizes and 3 years of chart data |
| `history.csv` | Every week since 2010: long, short, net, gauge, change |
| `step1_gold.py` … `step6_sizing.py` | The research trail, one step at a time |
| `signals_now.py` | Prints Rule v1 trades that are still open |
| `test_results.csv`, `trades.csv` | Backtest outputs |

## Run it yourself

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python update.py
```

No API key needed.

## Limitations

- **Small sample.** Extremes come in clusters, so there are only a handful of separate episodes per market.
- **Futures prices roll.** Gold, crude and 10-year prices come from rolling futures contracts, which add small artificial jumps on roll dates.
- **Report lag.** Positions are dated Tuesday but published Friday; the tests only use prices from after publication.
- **Costs are rough.** 0.1% per trade covers spread and slippage, but not the daily financing charged on positions held for 8 weeks.
- **Prices from Yahoo Finance** via `yfinance`, which is free but unofficial.

## Data sources

- [CFTC Commitments of Traders, Public Reporting Environment](https://publicreporting.cftc.gov) (Disaggregated and Traders in Financial Futures, futures only)
- Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance)