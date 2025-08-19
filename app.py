import os
import sys
import subprocess
import glob
import pandas as pd
import streamlit as st

st.set_page_config(page_title="4HorsemenDFS Optimizer", layout="wide")
st.title("4HorsemenDFS – Lineup Optimizer")

# --- Sidebar controls ---
st.sidebar.header("Settings")
proj_file = st.sidebar.file_uploader("Projections CSV", type=["csv"])
dk_file = st.sidebar.file_uploader("DraftKings Salaries CSV", type=["csv"])
alias_file = st.sidebar.file_uploader("Name Aliases CSV (optional)", type=["csv"])

salary_cap = st.sidebar.number_input("Salary cap", min_value=30000, max_value=70000, value=50000, step=500)
min_spend  = st.sidebar.number_input("Minimum spend", min_value=0, max_value=70000, value=49500, step=500)
n_lineups  = st.sidebar.number_input("# of lineups", min_value=1, max_value=150, value=20, step=1)
uniq_share = st.sidebar.slider("Uniqueness (max shared slots)", 5, 8, 7)
alpha_pct  = st.sidebar.slider("Randomness (projection noise %)", 0, 15, 4)
max_expo   = st.sidebar.slider("Max exposure per player (%)", 10, 80, 40)

run_btn = st.sidebar.button("Optimize")

# paths
OUTPUT_DIR = "outputs"
REPORTS_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def _persist_upload(uploaded, default_path):
    if uploaded is None:
        return None
    with open(default_path, "wb") as f:
        f.write(uploaded.read())
    return default_path

# Tabs
tab_data, tab_match, tab_opt, tab_lineups, tab_reports = st.tabs(["Data", "Matching", "Optimize", "Lineups", "Reports"])

with tab_data:
    st.subheader("Inputs")
    c1, c2 = st.columns(2)
    alias_path = None

    if proj_file:
        proj_path = _persist_upload(proj_file, "projections.csv")
        df_proj = pd.read_csv(proj_path)
        c1.metric("Projection rows", len(df_proj))
        c1.dataframe(df_proj.head(50))
    else:
        st.info("Upload your Projections CSV to preview.")

    if dk_file:
        dk_path = _persist_upload(dk_file, "data/DKSalaries.csv")
        df_dk = pd.read_csv(dk_path)
        c2.metric("DK Salary rows", len(df_dk))
        c2.dataframe(df_dk.head(50))
    else:
        st.info("Upload your DraftKings Salaries CSV to preview.")

    if alias_file:
        alias_path = _persist_upload(alias_file, "data/name_aliases.csv")
        df_alias = pd.read_csv(alias_path)
        st.caption("Alias overrides (optional)")
        st.dataframe(df_alias)
    elif os.path.exists("data/name_aliases.csv"):
        alias_path = "data/name_aliases.csv"

with tab_match:
    st.subheader("Match Report")
    unmatched = os.path.join(REPORTS_DIR, "unmatched_players.csv")
    ambiguous = os.path.join(REPORTS_DIR, "ambiguous_matches.csv")

    if os.path.exists(unmatched):
        df_unmatched = pd.read_csv(unmatched)
        st.write("Unmatched players")
        st.dataframe(df_unmatched.head(200))
        st.download_button("Download unmatched_players.csv", df_unmatched.to_csv(index=False), "unmatched_players.csv")
    else:
        st.info("Run optimizer to generate unmatched report.")

    if os.path.exists(ambiguous):
        df_amb = pd.read_csv(ambiguous)
        st.write("Ambiguous matches")
        st.dataframe(df_amb.head(200))
        st.download_button("Download ambiguous_matches.csv", df_amb.to_csv(index=False), "ambiguous_matches.csv")

with tab_opt:
    st.subheader("Build Lineups")

    if run_btn:
        if not proj_file or not dk_file:
            st.error("Please upload both Projections and DK Salaries.")
        else:
            cmd = [
                sys.executable, "scripts/optimize_lineups_v2.py",
                "--projections", "projections.csv",
                "--salaries", "data/DKSalaries.csv",
                "--output", os.path.join(OUTPUT_DIR, "optimal_lineup_v2.csv"),
                "--salary-cap", str(salary_cap),
                "--min-salary", str(min_spend),
                "--num-lineups", str(n_lineups),
                "--uniq-shared", str(uniq_share),
                "--alpha", str(alpha_pct / 100.0),
                "--max-exposure", str(max_expo / 100.0),
            ]
            if alias_path:
                cmd += ["--aliases", alias_path]

            st.code(" ".join(cmd), language="bash")

            # Force UTF-8 in child process and decode safely on Windows
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            try:
                with st.spinner("Solving..."):
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                        shell=False,
                    )
                st.text_area("Console log", value=(proc.stdout or "") + "\n" + (proc.stderr or ""), height=400)
                if proc.returncode != 0:
                    st.error(f"Optimizer exited with code {proc.returncode}")
            except Exception as e:
                st.error(f"Error calling optimizer: {e}")

    # Show most recent optimal lineup if present
    opt_csv = os.path.join(OUTPUT_DIR, "optimal_lineup_v2.csv")
    if os.path.exists(opt_csv):
        st.success("Latest optimal lineup")
        df_opt = pd.read_csv(opt_csv)
        st.dataframe(df_opt)
        st.download_button("Download optimal_lineup_v2.csv", df_opt.to_csv(index=False), "optimal_lineup_v2.csv")

with tab_lineups:
    st.subheader("Generated Lineups")
    lineup_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "lineup_*.csv")))
    if lineup_files:
        pick = st.selectbox("Select lineup file", lineup_files)
        df_l = pd.read_csv(pick)
        st.dataframe(df_l)
        st.download_button("Download this lineup", df_l.to_csv(index=False), os.path.basename(pick))
    else:
        st.info("No multi-lineup files found. Increase # of lineups and re-run.")

with tab_reports:
    st.subheader("Exposure & Stacks")
    pexp = os.path.join(REPORTS_DIR, "player_exposure.csv")
    texp = os.path.join(REPORTS_DIR, "team_exposure.csv")
    stacks = os.path.join(REPORTS_DIR, "stacks.csv")

    if os.path.exists(pexp):
        st.write("Player Exposure")
        st.dataframe(pd.read_csv(pexp))
    if os.path.exists(texp):
        st.write("Team Exposure")
        st.dataframe(pd.read_csv(texp))
    if os.path.exists(stacks):
        st.write("Stacks")
        st.dataframe(pd.read_csv(stacks))

st.caption("Tip: keep reports/unmatched_players.csv small by maintaining data/name_aliases.csv")
