import pandas as pd

data = pd.read_csv("test_results.csv", parse_dates=["date"])
data = data.sort_values(["market", "date"])

# A new episode starts when a market enters an extreme zone
# it hasn't been in at any point in the previous 4 weeks
zone_by_market = data.groupby("market")["zone"]
recent = pd.concat([zone_by_market.shift(k) for k in range(1, 5)], axis=1)
data["episode_start"] = (data["zone"] != "middle") & ~recent.eq(data["zone"], axis=0).any(axis=1)

data["half"] = data["date"].dt.year.map(lambda y: "2013-2020" if y <= 2020 else "2021-2026")

rows = []
for (market, half), part in data.groupby(["market", "half"]):
    normal = part[part["zone"] == "middle"]
    for zone in ["max long (>90)", "max short (<10)"]:
        starts = part[(part["zone"] == zone) & part["episode_start"]]
        row = {"market": market, "zone": zone, "half": half, "episodes": len(starts)}
        for w in (4, 8):
            r = starts[f"ret{w}"].dropna()
            base = normal[f"ret{w}"].dropna()
            row[f"edge_{w}w"] = round(r.mean() - base.mean(), 1) if len(r) else None
        r8 = starts["ret8"].dropna()
        row["up_8w"] = round((r8 > 0).mean() * 100) if len(r8) else None
        row["normal_up_8w"] = round((normal["ret8"].dropna() > 0).mean() * 100)
        rows.append(row)

table = pd.DataFrame(rows).set_index(["market", "zone", "half"])
pd.set_option("display.width", 120)
pd.set_option("display.max_columns", None)
print(table)

print("\nSame direction in both halves (8-week edge):")
for (market, zone), g in table.groupby(level=["market", "zone"]):
    e = g["edge_8w"].tolist()
    if len(e) == 2 and e[0] * e[1] > 0:
        print(f"  {market:<6} {zone:<16} {e[0]:+.1f} then {e[1]:+.1f}")