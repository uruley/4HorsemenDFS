import pandas as pd

dk = pd.read_csv("data/DKSalaries.csv")
df = pd.DataFrame({
    "name": dk["Name"].astype(str).str.strip(),
    "pos": dk["Position"].astype(str).str.upper().str.strip()
                     .str.split("/").str[0].replace({"DEF":"DST","D/ST":"DST","D":"DST"}),
    "proj_points": pd.to_numeric(dk["AvgPointsPerGame"], errors="coerce"),
    "team": dk["TeamAbbrev"].astype(str).str.upper().str.strip(),
    "opp": "UNK",
})
df = df[df["proj_points"].notna()].copy()
df.to_csv("projections.csv", index=False)
print("wrote projections.csv with", len(df), "rows")
print(df["pos"].value_counts().to_string())
