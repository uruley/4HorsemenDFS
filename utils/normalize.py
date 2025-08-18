import re, unicodedata
from typing import Optional

DST_WORDS = {"dst","def","defense","d/st","d-st"}

TEAM_ALIAS = {
    "JAX":"JAC","WSH":"WAS","LA":"LAR","ARZ":"ARI","SD":"LAC","STL":"LAR",
    "TAM":"TB","GNB":"GB","SFO":"SF"
}

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def player_match_key(name: str) -> str:
    n = strip_accents(str(name))
    n = re.sub(r"[^A-Za-z0-9 ]", "", n).lower()
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

def canon_team(team: Optional[str]) -> Optional[str]:
    if team is None: return None
    t = str(team).strip().upper()
    return TEAM_ALIAS.get(t, t)

def is_dst(name: str) -> bool:
    n = re.sub(r"[^A-Za-z ]","", str(name)).lower().split()
    return any(w in DST_WORDS for w in n)
