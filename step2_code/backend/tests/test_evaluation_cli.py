"""CLI tests for evaluation runner (T009).

Real subprocess tests: success, bad dataset, corpus error, param validation,
call counting, determinism.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_corpus(tmp_path: Path, docs: list[tuple[str, str]]) -> tuple[Path, Path]:
    """Create a corpus with given (filename, content) pairs. Returns (manifest_path, corpus_root)."""
    manifest_docs = []
    for fname, content in docs:
        fpath = tmp_path / fname
        _write_text(fpath, content)
        sha = _hash_file(fpath)
        manifest_docs.append({
            "document_id": fname.replace(".txt", ""),
            "policy_group_id": "g", "title": fname,
            "source_url": "https://example.org/", "source_site": "测试站",
            "local_path": fname, "sha256": sha, "version_label": "v1",
            "published_at": None, "effective_from": None, "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        })
    manifest = {"schema_version": "1.0", "documents": manifest_docs}
    mp = tmp_path / "manifest.json"
    _write_json(mp, manifest)
    return mp, tmp_path


def _make_questions(tmp_path: Path, doc_id: str, doc_sha: str,
                    block_id: str, text: str, answerable: bool = True) -> Path:
    """Create a minimal questions.json."""
    q = {
        "schema_version": "1.0",
        "dataset_id": "test-ds",
        "dataset_version": "1.0",
        "split": "dev",
        "is_synthetic": True,
        "questions": [{
            "question_id": "q01",
            "query": text[:20],
            "answerable": answerable,
            "evidence": [{
                "evidence_id": "e01",
                "document_id": doc_id,
                "document_sha256": doc_sha,
                "parser_version": "1.0",
                "block_id": block_id,
                "char_start": 0,
                "char_end": min(10, len(text)),
                "quote": text[:10],
            }] if answerable else [],
        }],
    }
    qp = tmp_path / "questions.json"
    _write_json(qp, q)
    return qp


def _run_cli(tmp_path: Path, mp: Path, qp: Path, extra_args=None) -> subprocess.CompletedProcess:
    args = [
        sys.executable, "-m", "campus_assistant.evaluation.run",
        "--manifest", str(mp), "--corpus-root", str(tmp_path),
        "--questions", str(qp),
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args, capture_output=True, cwd=str(tmp_path),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestSuccess:
    def test_valid_dataset(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "缓考申请材料\n\n成绩复核要求\n")])
        # Need to get actual block IDs — use parse_manifest
        from campus_assistant.corpus.parse import parse_manifest
        pr = parse_manifest(mp, root)
        doc = pr["documents"][0]
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"], answerable=True)
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 0
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is True
        assert out["question_count"] == 1
        assert out["answerable_count"] == 1
        assert out["evaluator_version"] == "1.0"
        assert "summary" in out
        assert "per_question" in out

    def test_output_fields(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        from campus_assistant.corpus.parse import parse_manifest
        pr = parse_manifest(mp, root)
        doc = pr["documents"][0]
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"], answerable=True)
        proc = _run_cli(root, mp, qp)
        out = json.loads(proc.stdout.decode("utf-8"))
        assert "manifest_sha256" in out
        assert "questions_sha256" in out
        assert "corpus_documents" in out
        assert out["parameters"]["max_chars"] == 500
        assert out["parameters"]["k1"] == 1.5


class TestDeterminism:
    def test_same_input_same_output(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test content\n")])
        from campus_assistant.corpus.parse import parse_manifest
        pr = parse_manifest(mp, root)
        doc = pr["documents"][0]
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"])
        r1 = json.loads(_run_cli(root, mp, qp).stdout.decode("utf-8"))
        r2 = json.loads(_run_cli(root, mp, qp).stdout.decode("utf-8"))
        # T027：timing_seconds 为分段耗时记录，天然非确定性且不作性能结论——
        # 确定性比较排除该字段，其余输出必须逐字节一致。
        r1.pop("timing_seconds", None)
        r2.pop("timing_seconds", None)
        assert r1 == r2


class TestBadDataset:
    def test_missing_file(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        proc = _run_cli(root, mp, tmp_path / "nope.json")
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is False
        assert any(e["code"] == "DATASET_READ_ERROR" for e in out["errors"])

    def test_invalid_json(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        qp = tmp_path / "bad.json"
        qp.write_text("{bad json", encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])

    def test_schema_error(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        qp = tmp_path / "bad.json"
        _write_json(qp, {"schema_version": "2.0", "dataset_id": "x", "dataset_version": "1",
                         "split": "dev", "is_synthetic": True, "questions": []})
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])


class TestCorpusError:
    def test_invalid_manifest(self, tmp_path: Path) -> None:
        mp = tmp_path / "bad_manifest.json"
        _write_json(mp, {"schema_version": "1.0", "documents": []})
        qp = tmp_path / "q.json"
        _write_json(qp, {"schema_version": "1.0", "dataset_id": "x", "dataset_version": "1",
                         "split": "dev", "is_synthetic": True, "questions": [
                             {"question_id": "q1", "query": "test", "answerable": False, "evidence": []}
                         ]})
        proc = _run_cli(tmp_path, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "CORPUS_ERROR" for e in out["errors"])


class TestEvidenceReferenceError:
    def test_bad_document_id(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        qp = _make_questions(tmp_path, "nonexistent", "a" * 64, "b1", "test", answerable=True)
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "EVIDENCE_REFERENCE_ERROR" for e in out["errors"])

    def test_bad_hash(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        from campus_assistant.corpus.parse import parse_manifest
        pr = parse_manifest(mp, root)
        doc = pr["documents"][0]
        qp = _make_questions(tmp_path, doc["document_id"], "b" * 64, "b1", "test", answerable=True)
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "EVIDENCE_REFERENCE_ERROR" for e in out["errors"])


class TestParamValidation:
    def test_top_k_zero(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        qp = tmp_path / "q.json"
        _write_json(qp, {"schema_version": "1.0", "dataset_id": "x", "dataset_version": "1",
                         "split": "dev", "is_synthetic": True, "questions": [
                             {"question_id": "q1", "query": "test", "answerable": False, "evidence": []}
                         ]})
        proc = _run_cli(root, mp, qp, ["--top-k", "0"])
        assert proc.returncode == 2

    def test_top_k_over_20(self, tmp_path: Path) -> None:
        mp, root = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        qp = tmp_path / "q.json"
        _write_json(qp, {"schema_version": "1.0", "dataset_id": "x", "dataset_version": "1",
                         "split": "dev", "is_synthetic": True, "questions": [
                             {"question_id": "q1", "query": "test", "answerable": False, "evidence": []}
                         ]})
        proc = _run_cli(root, mp, qp, ["--top-k", "21"])
        assert proc.returncode == 2

    def test_usage_error(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.evaluation.run"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 2


class TestEvidenceValidation:
    """R1: Verify all evidence fields are checked against actual corpus."""

    def _make_corpus_and_block(self, tmp_path):
        mp, root = _make_corpus(tmp_path, [("doc.txt", "第一段内容\n\n第二段内容\n")])
        from campus_assistant.corpus.parse import parse_manifest
        pr = parse_manifest(mp, root)
        doc = pr["documents"][0]
        return mp, root, doc

    def test_bad_block_id(self, tmp_path: Path) -> None:
        mp, root, doc = self._make_corpus_and_block(tmp_path)
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], "nonexistent_block",
                             doc["blocks"][0]["text"], answerable=True)
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is False
        assert any(e["code"] == "EVIDENCE_REFERENCE_ERROR" and "block_id" in e["field"] for e in out["errors"])

    def test_bad_parser_version(self, tmp_path: Path) -> None:
        mp, root, doc = self._make_corpus_and_block(tmp_path)
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"], answerable=True)
        # Modify parser_version in questions file
        import json as _json
        qdata = _json.loads(qp.read_text(encoding="utf-8"))
        qdata["questions"][0]["evidence"][0]["parser_version"] = "999"
        qp.write_text(_json.dumps(qdata, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any("parser_version" in e["field"] for e in out["errors"])

    def test_char_end_exceeds_block_length(self, tmp_path: Path) -> None:
        mp, root, doc = self._make_corpus_and_block(tmp_path)
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"], answerable=True)
        # Set char_end beyond block length
        import json as _json
        qdata = _json.loads(qp.read_text(encoding="utf-8"))
        qdata["questions"][0]["evidence"][0]["char_end"] = 9999
        qp.write_text(_json.dumps(qdata, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any("char" in e["field"] for e in out["errors"])

    def test_quote_mismatch(self, tmp_path: Path) -> None:
        mp, root, doc = self._make_corpus_and_block(tmp_path)
        block = doc["blocks"][0]
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], block["block_id"],
                             block["text"], answerable=True)
        # Change quote to something wrong
        import json as _json
        qdata = _json.loads(qp.read_text(encoding="utf-8"))
        qdata["questions"][0]["evidence"][0]["quote"] = "完全不同的文本"
        qp.write_text(_json.dumps(qdata, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any("quote" in e["field"] for e in out["errors"])

    def test_bad_evidence_no_search(self, tmp_path: Path, monkeypatch) -> None:
        """R1: Bad evidence should fail before BM25Index.search is called."""
        from campus_assistant.retrieval import bm25 as bm25_mod
        search_called = {"n": 0}
        orig_search = bm25_mod.BM25Index.search

        def counting_search(*a, **kw):
            search_called["n"] += 1
            return orig_search(*a, **kw)

        monkeypatch.setattr(bm25_mod.BM25Index, "search", counting_search)

        mp, root, doc = self._make_corpus_and_block(tmp_path)
        qp = _make_questions(tmp_path, doc["document_id"],
                             doc["metadata"]["sha256"], "bad_block_id",
                             "text", answerable=True)
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        assert search_called["n"] == 0


class TestNonObjectJson:
    """R4: Non-dict JSON top-level must produce DATASET_SCHEMA_ERROR."""

    def _make_corpus_for_json(self, tmp_path):
        return _make_corpus(tmp_path, [("doc.txt", "test\n")])

    def test_top_level_array(self, tmp_path: Path) -> None:
        mp, root = self._make_corpus_for_json(tmp_path)
        qp = tmp_path / "bad.json"
        qp.write_text("[]", encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is False
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])

    def test_top_level_null(self, tmp_path: Path) -> None:
        mp, root = self._make_corpus_for_json(tmp_path)
        qp = tmp_path / "bad.json"
        qp.write_text("null", encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])

    def test_top_level_number(self, tmp_path: Path) -> None:
        mp, root = self._make_corpus_for_json(tmp_path)
        qp = tmp_path / "bad.json"
        qp.write_text("42", encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])

    def test_top_level_string(self, tmp_path: Path) -> None:
        mp, root = self._make_corpus_for_json(tmp_path)
        qp = tmp_path / "bad.json"
        qp.write_text('"hello"', encoding="utf-8")
        proc = _run_cli(root, mp, qp)
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert any(e["code"] == "DATASET_SCHEMA_ERROR" for e in out["errors"])


class TestInitCounts:
    def test_multi_question_init(self, tmp_path: Path, monkeypatch) -> None:
        """parse_manifest, chunk_documents, BM25Index each called once for multi-question eval."""
        from campus_assistant.corpus import parse as parse_mod
        from campus_assistant.corpus import chunk as chunk_mod
        from campus_assistant.retrieval import bm25 as bm25_mod

        counts = {"parse": 0, "chunk": 0, "index": 0}
        orig_parse = parse_mod.parse_manifest
        orig_chunk = chunk_mod.chunk_documents
        orig_init = bm25_mod.BM25Index.__init__

        def c_parse(*a, **kw):
            counts["parse"] += 1
            return orig_parse(*a, **kw)
        def c_chunk(*a, **kw):
            counts["chunk"] += 1
            return orig_chunk(*a, **kw)
        def c_init(self_inner, *a, **kw):
            counts["index"] += 1
            return orig_init(self_inner, *a, **kw)

        monkeypatch.setattr(parse_mod, "parse_manifest", c_parse)
        monkeypatch.setattr(chunk_mod, "chunk_documents", c_chunk)
        monkeypatch.setattr(bm25_mod.BM25Index, "__init__", c_init)

        mp, root = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n\n成绩复核\n")])
        from campus_assistant.corpus.parse import parse_manifest as real_parse
        pr = real_parse(mp, root)
        doc = pr["documents"][0]
        blocks = doc["blocks"]
        # Build a 2-question dataset
        qdata = {
            "schema_version": "1.0",
            "dataset_id": "test-ds",
            "dataset_version": "1.0",
            "split": "dev",
            "is_synthetic": True,
            "questions": [
                {
                    "question_id": "q1",
                    "query": "缓考",
                    "answerable": True,
                    "evidence": [{
                        "evidence_id": "e1",
                        "document_id": doc["document_id"],
                        "document_sha256": doc["metadata"]["sha256"],
                        "parser_version": "1.0",
                        "block_id": blocks[0]["block_id"],
                        "char_start": 0,
                        "char_end": min(4, len(blocks[0]["text"])),
                        "quote": blocks[0]["text"][:4],
                    }],
                },
                {
                    "question_id": "q2",
                    "query": "成绩",
                    "answerable": True,
                    "evidence": [{
                        "evidence_id": "e2",
                        "document_id": doc["document_id"],
                        "document_sha256": doc["metadata"]["sha256"],
                        "parser_version": "1.0",
                        "block_id": blocks[1]["block_id"],
                        "char_start": 0,
                        "char_end": min(4, len(blocks[1]["text"])),
                        "quote": blocks[1]["text"][:4],
                    }],
                },
            ],
        }
        qp = tmp_path / "questions.json"
        _write_json(qp, qdata)
        counts["parse"] = 0
        from campus_assistant.evaluation.run import _run_eval
        _run_eval(mp, root, qp, top_k=5)
        assert counts == {"parse": 1, "chunk": 1, "index": 1}
