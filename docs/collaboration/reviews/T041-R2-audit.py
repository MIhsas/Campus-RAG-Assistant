"""Focused revision-2 document/preservation audit; no metric or model rerun."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "docs/collaboration/submissions/T041"
DEL = ROOT / "docs/delivery"
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(kind, label, ok):
    checks.append({"kind": kind, "label": label, "pass": bool(ok)})
current = read(SUB / "changed-files.json")
old = read(SUB / "rev1/changed-files.json")
for section in ("delivery_modified", "delivery_unchanged", "submissions"):
    for item in current[section]:
        if "sha256" in item:
            check("current hash", item["path"], sha(ROOT / item["path"]) == item["sha256"])
for section in ("delivery_updated", "delivery_new"):
    for item in old[section]:
        check("prior delivery archive", item["path"], sha(DEL / "archive-t041-rev1" / Path(item["path"]).name) == item["sha256"])
for item in old["submissions"]:
    if "sha256" in item:
        check("prior submission archive", item["path"], sha(SUB / "rev1" / Path(item["path"]).name) == item["sha256"])
links = []
names = [Path(item["path"]).name for section in ("delivery_modified", "delivery_unchanged") for item in current[section]]
texts = {name: (DEL / name).read_text(encoding="utf-8") for name in names}
for name, text in texts.items():
    for target in re.findall(r'\]\(([^\n)]+)\)', text):
        if re.match(r'^[a-zA-Z]+:', target) or target.startswith('#'):
            continue
        dest = target.split('#')[0].strip('<>')
        links.append({"file": name, "target": target, "pass": (DEL / dest).exists()})
check("links", "30 existing relative links", len(links) == 30 and all(link['pass'] for link in links))
for name in ("system-design.md", "human-review-pending.md", "generation-casebook.md"):
    check("unchanged delivery", name, sha(DEL / name) == sha(DEL / "archive-t041-rev1" / name))
check("preserved original verification", "t041-verify original bytes", sha(SUB / "t041-verify.json") == sha(SUB / "rev1/t041-verify.json"))
index = texts["experiment-index.md"]
defense = texts["defense-script.md"]
matrix = texts["evidence-matrix.md"]
check("reviewed prose", "current human status distinguished", "gold 为**模型辅助标注、人工未复核**" not in index and "用户逐项意见" in index and "T039 新改项与 T040 新答案待定向复核" in index and "用户逐项意见已收到" in defense and "gold 人工未复核" not in defense)
source = (ROOT / "docs/collaboration/reviews/T038-browser/verification.md").read_text(encoding="utf-8")
check("reviewed prose", "T038 scope retained, current/new scope limited", "T038—T041 均无浏览器实操" not in matrix and "T038-browser/verification.md" in matrix and "T041 本轮无新浏览器实操" in matrix and "T040 无真实浏览器生成闭环证据" in matrix and "本记录为手动真实页面操作" in source)
result = {"checks": checks, "count": len(checks), "links": links, "pass": all(c['pass'] for c in checks), "boundary": "Focused file and prose checks plus Astra source reading; previous numeric/case/token/time/help validation is carried forward, not rerun."}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({"checks": len(checks), "links": len(links), "pass": result['pass'], "failed": [c for c in checks if not c['pass']]}))
raise SystemExit(0 if result['pass'] else 1)
