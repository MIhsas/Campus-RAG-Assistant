"""T042 build-focused tests for build-targeted-review-pack.py.

Only the pack-building business chain: 8 cards with domain-separated IDs,
quotes verified at build time, q10's three paragraphs (incl. P3 inference)
unchanged vs T040 original, all new opinions default 未复核, source files
untouched. No product/experiment/model tests.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
SCRIPT = BACKEND / "scripts" / "build-targeted-review-pack.py"

INPUTS = {
    "manifest": ROOT / "data/corpora/sicau-rag-pilot-v1.2/manifest.json",
    "questions": ROOT / "data/evaluations/sicau-rag-pilot-eval-v2/questions.json",
    "supplement": ROOT / "docs/collaboration/submissions/T039/review-supplement.md",
    "live-answers": ROOT / "docs/collaboration/submissions/T040/live-answers-full.json",
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _run_build(out_dir: Path) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, str(SCRIPT),
        "--manifest", str(INPUTS["manifest"]),
        "--corpus-root", str(ROOT / "data/corpora/sicau-rag-pilot-v1.2"),
        "--questions", str(INPUTS["questions"]),
        "--supplement", str(INPUTS["supplement"]),
        "--live-answers", str(INPUTS["live-answers"]),
        "--casebook", str(ROOT / "docs/delivery/generation-casebook.md"),
        "--user-record", str(ROOT / "data/reviews/T036-user-review-20261008/human-review-record.json"),
        "--out-dir", str(out_dir),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("t042") / "T042-v1"
    before = {k: _sha(v) for k, v in INPUTS.items()}
    proc = _run_build(out_dir)
    after = {k: _sha(v) for k, v in INPUTS.items()}
    assert proc.returncode == 0, proc.stdout + proc.stderr
    pack = json.loads((out_dir / "pack.json").read_text(encoding="utf-8"))
    return pack, out_dir, before, after


def test_eight_cards_domain_ids(built):
    pack, _, _, _ = built
    ids = [c["card_id"] for c in pack["cards"]]
    assert ids == ["revision:q08", "revision:q10", "revision:u03", "revision:u04",
                   "answer:q08", "answer:q10", "answer:u03", "answer:u04"]
    assert len(set(ids)) == 8  # 分域 ID 不冲突
    rev = {c["question_id"] for c in pack["cards"] if c["object_type"] == "revision"}
    ans = {c["question_id"] for c in pack["cards"] if c["object_type"] == "answer"}
    assert rev == ans == {"q08", "q10", "u03", "u04"}


def test_q10_paragraphs_and_p3_unchanged(built):
    pack, _, _, _ = built
    live = json.loads(INPUTS["live-answers"].read_text(encoding="utf-8"))
    card = next(c for c in pack["cards"] if c["card_id"] == "answer:q10")
    orig = live["questions"]["q10"]["answer_paragraphs_full"]
    assert [p["text"] for p in card["answer_paragraphs"]] == [p["text"] for p in orig]
    assert len(card["answer_paragraphs"]) == 3
    p3 = card["answer_paragraphs"][2]["text"]
    assert "不纳入上述组成比例" in p3 and "两级制" in p3
    assert any("推断" in n for n in card["special_notes"])  # P3 推断突出


def test_q08_gold_not_mixed_into_sent_evidence(built):
    pack, _, _, _ = built
    rev08 = next(c for c in pack["cards"] if c["card_id"] == "revision:q08")
    ans08 = next(c for c in pack["cards"] if c["card_id"] == "answer:q08")
    gold_quotes = [e["quote"] for e in rev08["gold_evidence"]]
    sent_texts = [e["quote"] for e in ans08["sent_evidence"]]
    assert gold_quotes and sent_texts
    for gq in gold_quotes:
        assert not any(gq in t or t in gq for t in sent_texts), "gold 不得混入实发 E"


def test_u04_candidates_labelled_not_basis(built):
    pack, _, _, _ = built
    rev04 = next(c for c in pack["cards"] if c["card_id"] == "revision:u04")
    assert rev04["candidates"], "u04 应含未核实候选"
    for cand in rev04["candidates"]:
        assert "未核实" in cand["candidate_label"] and "非本次模型依据" in cand["candidate_label"]
    ans04 = next(c for c in pack["cards"] if c["card_id"] == "answer:u04")
    assert all(not e["document_id"].startswith("83eb") for e in ans04["sent_evidence"])


def test_all_unreviewed_and_inputs_identity(built):
    pack, _, before, after = built
    assert pack["pack_meta"]["human_review_status"] == "unreviewed"
    assert pack["pack_meta"]["counts"] == {"cards": 8, "revision_cards": 4, "answer_cards": 4,
                                          "verified_refs": pack["pack_meta"]["counts"]["verified_refs"]}
    assert pack["pack_meta"]["counts"]["verified_refs"] == 40
    assert pack["pack_meta"]["inputs"]["questions"]["sha256"] == before["questions"]
    assert pack["pack_meta"]["inputs"]["live_answers_full"]["sha256"] == before["live-answers"]
    assert before == after, "构建不得改动任何源输入"


def test_outputs_and_nonempty_refusal(built):
    pack, out_dir, _, _ = built
    assert (out_dir / "review.html").exists() and (out_dir / "README.md").exists()
    html = (out_dir / "review.html").read_text(encoding="utf-8")
    assert "/*__PACK_DATA__*/" not in html  # 数据已嵌入
    proc2 = _run_build(out_dir)
    assert proc2.returncode == 1 and "拒绝覆盖" in proc2.stdout
