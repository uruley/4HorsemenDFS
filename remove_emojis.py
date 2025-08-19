import re
import pathlib

# Remove emojis from the file
p = pathlib.Path("scripts/optimize_lineups_v2.py")
txt = p.read_text(encoding="utf-8", errors="ignore")

# Remove common emoji blocks (misc symbols, dingbats, emoticons, transport, supplemental symbols)
txt = re.sub(r'[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]', '', txt)

p.write_text(txt, encoding="utf-8")
print("Emojis removed from scripts/optimize_lineups_v2.py")
