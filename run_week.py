# run_week.py
import argparse, subprocess, sys, os, shlex

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    print(f"\n$ {cmd}")
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        sys.exit(proc.returncode)

def main():
    p = argparse.ArgumentParser("DFS weekly pipeline")
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--dk_salaries", required=True, help="DraftKings salaries CSV")
    p.add_argument("--lineups", type=int, default=50)
    p.add_argument("--salary_cap", type=int, default=50000)
    p.add_argument("--uniques", type=int, default=2)
    p.add_argument("--randomness", type=float, default=0.07)
    p.add_argument("--stack_qb_receiver", type=int, default=1)
    p.add_argument("--bringback", type=int, choices=[0,1], default=1)
    p.add_argument("--no_opp_dst", action="store_true")
    p.add_argument("--max_exposure", default="", help="e.g. \"Ja'Marr Chase=0.4; Joe Burrow=0.35\"")
    p.add_argument("--out", default="lineups_week.csv")
    p.add_argument("--retrain", action="store_true", help="Retrain QB/RB/WR/TE models first")
    args = p.parse_args()

    os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)

    # 1) (Optional) retrain
    if args.retrain:
        print("\n=== Retraining models (QB/RB/WR/TE) ===")
        run(f'{PY} scripts{os.sep}train_models.py')

    # 2) Build projections (uses models + nfl_data_py + DST fallback)
    print("\n=== Building projections ===")
    proj_csv = os.path.join(HERE, "projections.csv")
    cmd_proj = (
        f'{PY} scripts{os.sep}make_projections.py '
        f'--season {args.season} --week {args.week} '
        f'--out "{proj_csv}"'
    )
    run(cmd_proj)

    # 3) Run optimizer
    print("\n=== Optimizing lineups ===")
    parts = [
        f'{PY} scripts{os.sep}optimize_lineups.py',
        f'--projections "{proj_csv}"',
        f'--out "{args.out}"',
        f'--num_lineups {args.lineups}',
        f'--salary_cap {args.salary_cap}',
        f'--uniques {args.uniques}',
        f'--randomness {args.randomness}',
        f'--stack_qb_receiver {args.stack_qb_receiver}',
        f'--bringback {args.bringback}',
    ]
    if args.no_opp_dst:
        parts.append("--no_opp_dst")
    if args.max_exposure.strip():
        parts.append(f'--max_exposure "{args.max_exposure}"')

    run(" ".join(parts))

    print("\n✅ Pipeline complete.")
    print(f"• Projections: {proj_csv}")
    print(f"• Lineups:     {args.out}")
    print("• Reports:     ./reports/ (validation, exposures, stacks)")

if __name__ == "__main__":
    main()
