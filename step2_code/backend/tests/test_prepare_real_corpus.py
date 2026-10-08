"""T029-R1 lean regressions for prepare-real-corpus.py (business-level only).

Covers the review's causal chain without expanding the matrix:
- source_site derived from the SELECTED source_url host (dataset site may
  name the source-page site instead);
- VERIFY detects changed source bytes / changed selection evidence and
  exits non-zero WITHOUT overwriting the existing pack.
The exhaustive 4-scenario isolation is Astra's probe (T029-prepare-probe.py).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "prepare_real_corpus", BACKEND / "scripts" / "prepare-real-corpus.py"
)
prepare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare)


def _make_fixture(tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    src = dataset / "doc.txt"
    src.write_bytes(b"Original public policy text.\n")
    doc_id = prepare._sha256(src)
    row = {
        "doc_id": doc_id, "sha256": doc_id, "relative_path": "doc.txt",
        "title": "回归夹具",
        "sources": [{"url": "https://jiaowu.sicau.edu.cn/attach.txt",
                     "site": "rwy.sicau.edu.cn", "source_page": "https://rwy.sicau.edu.cn/page"}],
    }
    (dataset / "manifest.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    sel = {"docs": [{"doc_id": doc_id, "decision": "include", "reason": "r", "notes": "n1"}]}
    sp = tmp_path / "selection.json"
    sp.write_text(json.dumps(sel), encoding="utf-8")
    return dataset, sp, tmp_path / "pack", src, sel


def _run_build(dataset, sp, out) -> int:
    try:
        return prepare.build(dataset, sp, out)
    except SystemExit as exc:  # 脚本对输入漂移用 SystemExit 非零退出
        return exc.code if isinstance(exc.code, int) else 1


def test_source_site_from_selected_url_host(tmp_path):
    """source_site 必须等于已选 source_url 的主机；原 site 记录保留在 provenance。"""
    dataset, sp, out, _src, _sel = _make_fixture(tmp_path)
    assert prepare._site_from_url("https://jiaowu.sicau.edu.cn/attach.txt") == "jiaowu.sicau.edu.cn"
    assert _run_build(dataset, sp, out) == 0
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["documents"][0]["source_site"] == "jiaowu.sicau.edu.cn"
    prov = [json.loads(l) for l in (out / "provenance.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert prov[0]["all_sources"][0]["site"] == "rwy.sicau.edu.cn", "原来源页面站点须完整保留"
    assert prov[0]["selected_source_site_resolved"] == "jiaowu.sicau.edu.cn"


def test_verify_detects_input_change_without_overwrite(tmp_path):
    dataset, sp, out, src, _sel = _make_fixture(tmp_path)
    assert _run_build(dataset, sp, out) == 0
    before = {p.name: prepare._sha256(p) for p in out.glob("*") if p.is_file()}
    src.write_bytes(b"Changed policy text.\n")
    assert _run_build(dataset, sp, out) != 0, "输入字节变化必须非零退出"
    after = {p.name: prepare._sha256(p) for p in out.glob("*") if p.is_file()}
    assert before == after, "核验模式不得写入"


def test_verify_detects_selection_change_without_overwrite(tmp_path):
    dataset, sp, out, _src, sel = _make_fixture(tmp_path)
    assert _run_build(dataset, sp, out) == 0
    before = {p.name: prepare._sha256(p) for p in out.glob("*") if p.is_file()}
    sel["docs"][0]["notes"] = "n2"
    sp.write_text(json.dumps(sel), encoding="utf-8")
    assert _run_build(dataset, sp, out) != 0, "selection 边车变化必须非零退出"
    after = {p.name: prepare._sha256(p) for p in out.glob("*") if p.is_file()}
    assert before == after, "核验模式不得写入"