import pandas as pd

# Convert DK export to required schema
dk = pd.read_csv("data/DKSalaries.csv")
df = pd.DataFrame({
    "name": dk["Name"].astype(str).str.strip(),
    "pos": dk["Position"].astype(str).str.upper().str.strip().str.split("/").str[0].replace({"DEF":"DST","D/ST":"DST","D":"DST"}),
    "proj_points": pd.to_numeric(dk["AvgPointsPerGame"], errors="coerce"),
    "team": dk["TeamAbbrev"].astype(str).str.upper().str.strip(),
    "opp": "UNK",
})

# Clean up and filter
df = df[df["proj_points"].notna()]
df = df[df["proj_points"] > 0]  # Only keep players with positive projections

# Save to projections.csv
df.to_csv("projections.csv", index=False)

print(f"Converted {len(df)} players to projections.csv")
print(f"Position breakdown:")
print(df["pos"].value_counts().sort_index())
print(f"\nProjection range: {df['proj_points'].min():.1f} - {df['proj_points'].max():.1f}")
print(f"Teams: {len(df['team'].unique())}")
