#!/usr/bin/env python3
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import re
import pandas as pd
from difflib import SequenceMatcher, get_close_matches
from typing import Dict, Tuple, Optional

# ---- helpers --------------------------------------------------------------

SUFFIXES = (' jr', ' sr', ' ii', ' iii', ' iv', ' v')
DST_ALIASES = {
    'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills',
    'CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns',
    'DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers',
    'HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs',
    'LV':'Las Vegas Raiders','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','MIA':'Miami Dolphins',
    'MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants',
    'NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks',
    'SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders',
}

NICK_BUNDLES = {
    # "initial bundles" (no dot or with dot)
    'DJ': None, 'AJ': None, 'TJ': None, 'CJ': None, 'JJ': None, 'RJ': None, 'MJ': None,
    # common nicknames mapping to formal first names:
    'CeeDee': ['Cedarian'], 'Tee': ['Tamaurice'], 'Deebo': ['Tyshun'],
}

def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s\.-]", "", s)  # keep letters/digits/space/dot/hyphen
    s = re.sub(r"\s+", " ", s)
    return s

def _strip_suffix(first_last: str) -> str:
    s = _norm(first_last)
    for suf in SUFFIXES:
        if s.endswith(suf):
            return s[: -len(suf)].strip()
    return s

def split_first_last(name: str) -> Tuple[str, str]:
    s = _strip_suffix(name)
    # Handle dotted/initial pattern: A.Rodgers / A. Rodgers / A-Rodgers
    m = re.match(r'^\s*([A-Za-z])\s*[\.\-\s]\s*([A-Za-z][A-Za-z\-\']+(?:\s+[A-Za-z\-\']+)*)\s*$', s)
    if m:
        return m.group(1), m.group(2).strip()

    # If there's exactly one dot and no space (classic A.Rodgers), handle it
    if '.' in s and ' ' not in s:
        parts = s.split('.', 1)
        if len(parts[0]) == 1 and parts[1]:
            return parts[0], parts[1].strip()

    # Fallback: standard "First Last ..." split
    parts = s.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

def is_initial_bundle(tok: str) -> bool:
    t = tok.replace('.', '').upper()
    return t in NICK_BUNDLES

def canonical_dst_key(team_abbrev: Optional[str], full_name: Optional[str]) -> str:
    # Normalize all DST-like variants to "DST:<ABBREV>"
    if team_abbrev and team_abbrev in DST_ALIASES:
        return f"DST:{team_abbrev}"
    if full_name:
        nm = _norm(full_name)
        # try reverse map
        for abbr, full in DST_ALIASES.items():
            if _norm(full) == nm or _norm(f"{full} dst") == nm or _norm(f"{abbr} dst") == nm:
                return f"DST:{abbr}"
    # fallback (rare)
    return f"DST:{(team_abbrev or full_name or 'UNK').upper()}"

# ---- main matcher ---------------------------------------------------------

class AdvancedNameMatcherV2:
    def __init__(self, debug=False, alias_csv: Optional[str] = "data/name_aliases.csv"):
        self.debug = debug
        self.alias_map = self._load_aliases(alias_csv)

    def _load_aliases(self, path: Optional[str]) -> Dict[Tuple[str,str], str]:
        out = {}
        if not path:
            return out
        try:
            df = pd.read_csv(path)
            for _, r in df.iterrows():
                p_name = _norm(str(r['proj_name']))
                p_pos  = _norm(str(r.get('proj_pos', '')))
                dk     = str(r['dk_name']).strip()
                out[(p_name, p_pos)] = dk
            return out
        except Exception:
            return out

    def _build_indices(self, dk_df: pd.DataFrame):
        # Ensure normalized helper cols
        df = dk_df.copy()
        if 'pos' not in df: df['pos'] = df['Position'].str.upper()
        if 'name' not in df: df['name'] = df['Name']
        if 'team' not in df and 'TeamAbbrev' in df: df['team'] = df['TeamAbbrev']

        df['n_name'] = df['name'].apply(_strip_suffix)
        df['first'], df['last'] = zip(*df['n_name'].map(split_first_last))
        df['pos'] = df['pos'].str.upper().str.strip()
        df['team'] = df.get('team', pd.Series(['']*len(df))).str.upper().str.strip()

        # Indexes
        by_full = {}         # (pos, n_name) -> row
        by_pos_last = {}     # (pos, last) -> [rows]
        by_pos_last_team = {}# (pos, last, team) -> row
        by_initial_last = {} # (pos, first_initial, last) -> row

        for _, row in df.iterrows():
            pos  = row['pos']
            team = row['team']
            n_name = row['n_name']
            first = row['first']
            last  = row['last'] if row['last'] else n_name  # handle single-name oddities

            by_full[(pos, n_name)] = row

            by_pos_last.setdefault((pos, last), []).append(row)

            by_pos_last_team[(pos, last, team)] = row

            if first:
                by_initial_last[(pos, first[0], last)] = row

        return df, by_full, by_pos_last, by_pos_last_team, by_initial_last

    def _try_alias(self, proj_name: str, proj_pos: str) -> Optional[str]:
        key1 = (_norm(proj_name), _norm(proj_pos))
        key2 = (_norm(proj_name), '')  # position-agnostic
        return self.alias_map.get(key1) or self.alias_map.get(key2)

    def _match_person(self, proj_row, by_full, by_pos_last, by_pos_last_team, by_initial_last):
        p_name = str(proj_row['name'])
        p_pos  = str(proj_row['pos']).upper().strip()
        p_team = str(proj_row.get('team', '')).upper().strip()

        # alias override
        alias = self._try_alias(p_name, p_pos)
        if alias:
            key = (p_pos, _strip_suffix(alias))
            hit = by_full.get(key)
            if hit is not None:
                return hit, 'alias'

        n_name = _strip_suffix(p_name)
        first, last = split_first_last(n_name)

        # 1) Exact normalized full name at pos
        hit = by_full.get((p_pos, n_name))
        if hit is not None:
            return hit, 'exact'

        # 2) Team-aware last-name match if team present and unique
        if p_team and last:
            hit = by_pos_last_team.get((p_pos, last, p_team))
            if hit is not None:
                return hit, 'last+team'

        # 3) Initials like "A.Rodgers" / "A Rodgers" / "ARodgers"
        #    Also handle DJ/AJ/TJ bundles as "initial bundles"
        if first and last:
            # (a) classic first-initial + last
            hit = by_initial_last.get((p_pos, first[0], last))
            if hit is not None:
                return hit, 'initial+last'

            # (b) "DJ/AJ/…" first token
            if is_initial_bundle(first):
                # try first-letter of expanded possibilities = already covered by (a)
                # fall back to last-name unique at pos
                pass

        # 4) Unique last-name at position
        cand = by_pos_last.get((p_pos, last), [])
        if len(cand) == 1:
            return cand[0], 'last-unique'

        # 5) If multiple candidates share last name, try gently with difflib
        if len(cand) > 1:
            # choose the best name match by SequenceMatcher ratio
            ratios = [(SequenceMatcher(None, n_name, _strip_suffix(r['name'])).ratio(), r) for r in cand]
            ratios.sort(key=lambda x: x[0], reverse=True)
            if ratios and ratios[0][0] >= 0.92:
                return ratios[0][1], 'fuzzy-same-last'

        # 6) Final-resort fuzzy (tight cutoff) within same position
        # (kept small to avoid false positives)
        pos_names = [r['name'] for rows in by_pos_last.values() for r in rows if r['pos'] == p_pos]
        close = get_close_matches(p_name, pos_names, n=1, cutoff=0.93)
        if close:
            # find row by normalized name
            nn = _strip_suffix(close[0])
            hit = by_full.get((p_pos, nn))
            if hit is not None:
                return hit, 'fuzzy-tight'

        return None, None

    def _match_dst(self, proj_row, dk_df):
        # Canonicalize by team
        p_team = str(proj_row.get('team', '')).upper().strip()
        p_name = str(proj_row['name'])
        # Try to infer team from name if team missing
        if not p_team:
            nm = _norm(p_name)
            for abbr, full in DST_ALIASES.items():
                if _norm(full) in nm or abbr.lower() in nm or 'dst' in nm:
                    p_team = abbr
                    break

        key = canonical_dst_key(p_team, proj_row.get('name'))
        abbr = key.split(":")[1]
        hit = dk_df[(dk_df['pos'] == 'DST') & (dk_df['team'] == abbr)]
        if len(hit) == 1:
            return hit.iloc[0], 'dst-team'
        return None, None

    def merge(self, projections_df: pd.DataFrame, salaries_df: pd.DataFrame, debug=False):
        # Standardize inputs
        proj = projections_df.copy()
        if 'pos' in proj: proj['pos'] = proj['pos'].str.upper().str.strip()
        if 'team' in proj: proj['team'] = proj['team'].str.upper().str.strip()
        
        # Normalize dotted-initials in projection names: "A.Rodgers" -> "A Rodgers"
        proj['name'] = proj['name'].astype(str).str.replace(r'^\s*([A-Za-z])\.\s*', r'\1 ', regex=True)

        dk = salaries_df.copy()
        if 'Position' in dk: dk['pos'] = dk['Position'].str.upper().str.strip()
        if 'Name' in dk:     dk['name'] = dk['Name']
        if 'Salary' in dk:   dk['salary'] = dk['Salary']
        if 'TeamAbbrev' in dk: dk['team'] = dk['TeamAbbrev'].str.upper().str.strip()
        dk['pos'] = dk['pos'].replace({'DEF':'DST','D':'DST','D/ST':'DST'})

        # Build indices
        dk_idx_df, by_full, by_pos_last, by_pos_last_team, by_initial_last = self._build_indices(dk)

        matches = []
        unmatched = []
        ambiguous = []

        for _, pr in proj.iterrows():
            p_pos = str(pr['pos']).upper().strip()

            if p_pos == 'DST':
                hit, how = self._match_dst(pr, dk_idx_df)
            else:
                hit, how = self._match_person(pr, by_full, by_pos_last, by_pos_last_team, by_initial_last)

            if hit is not None:
                matches.append({
                    'name': pr['name'],
                    'dk_name': hit['name'],
                    'pos': p_pos,
                    'team': hit.get('team', pr.get('team', '')),
                    'opp': hit.get('opp', pr.get('opp', 'UNK')),
                    'salary': hit['salary'],
                    'proj_points': pr['proj_points'],
                    'match_how': how
                })
            else:
                # Track ambiguous last-name clusters for inspection
                if p_pos != 'DST':
                    n_name = _strip_suffix(str(pr['name']))
                    _, last = split_first_last(n_name)
                    cands = by_pos_last.get((p_pos, last), [])
                    if len(cands) > 1:
                        ambiguous.append({
                            'proj_name': pr['name'],
                            'pos': p_pos,
                            'team': pr.get('team',''),
                            'last': last,
                            'candidates': "; ".join(sorted(set(c['name'] for c in cands)))
                        })
                unmatched.append({'proj_name': pr['name'], 'pos': p_pos, 'team': pr.get('team','')})

        out = pd.DataFrame(matches)
        # Basic sanity filters
        if not out.empty:
            out = out[out['salary'].notna() & (out['salary'] > 0)]
            out = out[out['proj_points'].notna() & (out['proj_points'] >= 0)]
            out['value'] = out['proj_points'] / (out['salary'] / 1000.0)

        # Dump reports
        if unmatched:
            pd.DataFrame(unmatched).to_csv("reports/unmatched_players.csv", index=False)
        if ambiguous:
            pd.DataFrame(ambiguous).to_csv("reports/ambiguous_matches.csv", index=False)

        # Console summary
        total = len(proj)
        matched = len(out)
        rate = (matched / total * 100.0) if total else 0.0
        print(f"\n=== MATCH SUMMARY (V2) ===")
        print(f"Matched: {matched}/{total} ({rate:.1f}%)")
        if debug and not out.empty:
            print(out.groupby('pos')['name'].count())

        # readiness check (conservative)
        min_required = {'QB': 2, 'RB': 6, 'WR': 9, 'TE': 3, 'DST': 2}
        can_build = all((out[out['pos']==p].shape[0] >= need) for p, need in min_required.items())
        if can_build: print("Sufficient depth to build lineups.")
        else: print("Limited depth in one or more positions; check reports/ files.")

        return out
