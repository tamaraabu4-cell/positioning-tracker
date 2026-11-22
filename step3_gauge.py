import pandas as pd

WINDOW = 156  # 3 years of weekly reports

history = pd.read_csv("history.csv", parse_dates=["date"])
history = history.sort_values(["market", "date"])

net = history.groupby("market")["net"]
low = net.transform(lambda s: s.rolling(WINDOW).min())
high = net.transform(lambda s: s.rolling(WINDOW).max())

history["gauge"] = ((history["net"] - low) / (high - low) * 100).round()
history["change"] = net.diff()

history.to_csv("history.csv", index=False)

latest = history.groupby("market").tail(1)
print(f"{'Market':<8}{'Net':>12}{'Weekly change':>15}{'Gauge':>8}")
for _, r in latest.iterrows():
    print(f"{r['market']:<8}{int(r['net']):>12,}{int(r['change']):>15,}{int(r['gauge']):>8}")