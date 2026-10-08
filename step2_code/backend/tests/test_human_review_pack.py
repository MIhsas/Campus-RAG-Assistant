"""T036 focused checks for the offline human-review pack builder.

Only two meaningful business facts plus guard rails:
1. full completeness — 24 questions (20+4), 57 evidence, 13 steps, 20 citations,
   every span/quote matches a fresh parse;
2. export-path semantics are covered by scripts/check-review-pack.cjs (DOM/JS
   stub): one simulated opinion changes exactly one item, input SHAs persist.
Plus: refuse to overwrite a non-empty output dir; reject a corrupted citation
without writing a pack and without touching the originals; HTML stays offline
and defaults to 未复核. No model, retrieval or experiment is loaded here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
BUILDER = BACKEND / "scripts" / "build-human-review-pack.py"
MANIFEST = ROOT / "data/corpora/sicau-rag-pilot-v1.1/manifest.json"
QUESTIONS = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1/questions.json"
PROCEDURES = ROOT / "data/procedures/sicau-transfer-2026-v1/procedures.json"


def _run(out_dir: Path, procedures=PROCEDURES):
    return subprocess.run(
        [sys.executable, str(BUILDER),
         "--manifest", str(MANIFEST),
         "--corpus-root", str(MANIFEST.parent),
         "--questions", str(QUESTIONS),
         "--procedures", str(procedures),
         "--out-dir", str(out_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )


@pytest.fixture(scope="module")
def built_pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("pack") / "T036-test"
    r = _run(out)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


class TestCompleteness:
    def test_counts_and_spans(self, built_pack):
        pack = json.loads((built_pack / "pack.json").read_text(encoding="utf-8"))
        c = pack["pack_meta"]["counts"]
        assert c["questions"] == 24 and c["answerable"] == 20 and c["unanswerable"] == 4
        assert c["evidence"] == 57 and c["template_steps"] == 13 and c["template_citations"] == 20
        assert c["verified_refs"] == 77
        # every ref carries verbatim quote + full block + identity
        refs = [e for q in pack["questions"] for e in q["evidence"]]
        refs += [cit for t in pack["templates"] for s in t["steps"] for cit in s["citations"]]
        assert len(refs) == 77
        for r in refs:
            assert r["quote"] == r["block_text"][r["char_start"]:r["char_end"]]
            assert r["document_sha256"] and len(r["document_id"]) == 64  # 长 ID 不截断
            assert r["locator_display"] and r["block_text"]
        # inputs identity recorded
        assert pack["pack_meta"]["inputs"]["questions"]["sha256"].startswith("5fde70a3")
        assert pack["pack_meta"]["human_review_status"] == "unreviewed"

    def test_html_offline_and_defaults(self, built_pack):
        h = (built_pack / "review.html").read_text(encoding="utf-8")
        for bad in ("fetch(", "http://", "https://", "@import", "XMLHttpRequest"):
            assert bad not in h, bad
        assert "const PACK = {" in h
        assert "未复核" in h and "导出复核记录" in h


class TestGuardRails:
    def test_refuse_non_empty_dir(self, built_pack):
        r = _run(built_pack)  # same non-empty dir
        assert r.returncode == 1
        assert "拒绝覆盖" in r.stdout

    def test_reject_corrupt_citation_without_writing_pack(self, tmp_path):
        proc = json.loads(PROCEDURES.read_text(encoding="utf-8"))
        proc["procedures"][0]["steps"][0]["citations"][0]["quote"] = "（被篡改的引文）"
        bad = tmp_path / "bad-procedures.json"
        bad.write_text(json.dumps(proc, ensure_ascii=False), encoding="utf-8")
        out = tmp_path / "out"
        r = _run(out, procedures=bad)
        assert r.returncode == 1
        assert "CHECK FAILED" in r.stdout
        assert not out.exists(), "不得输出貌似完整的复核包"
        # originals untouched
        assert PROCEDURES.read_text(encoding="utf-8").count("被篡改的引文") == 0
