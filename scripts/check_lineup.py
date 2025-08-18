import sys, pandas as pd

VALID_SLOTS = {"QB","RB","WR","TE","FLEX","DST"}
CAP = 50000

def fail(msg):
    print(f"VALIDATION FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

def main(path="lineups.csv"):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        fail(f"Could not read {path}: {e}")

    required_cols = {"slot","name","salary","proj_points"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        fail(f"Missing columns: {sorted(missing)}")

    if len(df) != 9:
        fail(f"Expected 9 rows, got {len(df)}")

    if not df["slot"].isin(VALID_SLOTS).all():
        bad = df.loc[~df["slot"].isin(VALID_SLOTS), "slot"].unique().tolist()
        fail(f"Invalid slot(s): {bad}")

    # Counts by slot (FLEX checked separately)
    counts = df["slot"].value_counts().to_dict()
    need = {"QB":1, "RB":2, "WR":3, "TE":1, "DST":1}
    for k,v in need.items():
        if counts.get(k,0) != v:
            fail(f"Need {v} {k}, found {counts.get(k,0)}")

    # FLEX rules
    if counts.get("FLEX",0) != 1:
        fail(f"Need 1 FLEX, found {counts.get('FLEX',0)}")
    flex_rows = df[df["slot"]=="FLEX"]
    if flex_rows.empty:
        fail("FLEX row missing")
    # Optional: ensure FLEX is not QB/DST by verifying the player's position column if present
    if "pos" in df.columns:
        pos_ok = flex_rows["pos"].isin(["RB","WR","TE"]).all()
        if not pos_ok:
            fail("FLEX must be RB/WR/TE")

    # Salary cap
    total_salary = int(df["salary"].sum())
    if total_salary > CAP:
        fail(f"Salary cap exceeded: {total_salary} > {CAP}")

    total_proj = float(df["proj_points"].sum())
    out = df.copy().sort_values(["slot","salary"], ascending=[True, False])
    print(f"OK ✅ 9 players | Salary: {total_salary} | Proj: {round(total_proj,2)}")
    print(out.to_string(index=False))

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "lineups.csv"
    main(path)
