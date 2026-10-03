"""Tests for BM25 retrieval CLI (T007).

Subprocess tests: success, no hit, partial failure, param error, UTF-8.
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


def _make_corpus(tmp_path: Path, docs: list[tuple[str, str]]) -> Path:
    """Create a corpus with given (filename, content) pairs. Returns manifest path."""
    manifest_docs = []
    for fname, content in docs:
        fpath = tmp_path / fname
        _write_text(fpath, content)
        sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        manifest_docs.append({
            "document_id": fname.replace(".txt", ""),
            "policy_group_id": "g",
            "title": fname,
            "source_url": "https://example.org/",
            "source_site": "测试站",
            "local_path": fname,
            "sha256": sha,
            "version_label": "v1",
            "published_at": None,
            "effective_from": None,
            "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        })
    manifest = {"schema_version": "1.0", "documents": manifest_docs}
    mp = tmp_path / "manifest.json"
    _write_json(mp, manifest)
    return mp


def _run_cli(tmp_path: Path, mp: Path, extra_args=None) -> subprocess.CompletedProcess:
    args = [
        sys.executable, "-m", "campus_assistant.retrieval.search",
        "--manifest", str(mp), "--corpus-root", str(tmp_path),
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args, capture_output=True, cwd=str(tmp_path),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestSuccess:
    def test_finds_match(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请材料\n\n成绩复核要求\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "缓考申请", "--max-chars", "500", "--top-k", "5"])
        assert proc.returncode == 0
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is True
        assert len(out["hits"]) >= 1
        assert any("缓考" in h["matched_terms"][0]["term"] for h in out["hits"])

    def test_output_fields(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "缓考"])
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["schema_version"] == "1.0"
        assert out["retriever_version"] == "1.0"
        assert out["tokenizer_version"] == "cjk_bigram_ascii_v1"
        assert "query_tokens" in out
        assert "parameters" in out
        assert "indexed_chunk_count" in out


class TestNoHit:
    def test_no_match_returns_empty(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "不存在的词"])
        assert proc.returncode == 0
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is True
        assert out["hits"] == []


class TestPartialFailure:
    def test_bad_docx_preserved_hits(self, tmp_path: Path) -> None:
        """One good TXT + one corrupt DOCX → valid=false, but good doc hits preserved."""
        txt = tmp_path / "good.txt"
        _write_text(txt, "缓考申请\n")
        txt_sha = hashlib.sha256(txt.read_bytes()).hexdigest()
        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"PK\x03\x04not real")
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()
        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good", "policy_group_id": "g", "title": "好",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad", "policy_group_id": "g", "title": "坏",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "bad.docx", "sha256": bad_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
            ],
        }
        mp = tmp_path / "manifest.json"
        _write_json(mp, manifest)
        proc = _run_cli(tmp_path, mp, ["--query", "缓考"])
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is False
        assert len(out["hits"]) >= 1  # good doc hits preserved


class TestParamError:
    def test_top_k_zero(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "test", "--top-k", "0"])
        assert proc.returncode == 2
        assert proc.stdout == b"" or proc.stdout.strip() == b""

    def test_max_chars_negative(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "test", "--max-chars", "-1"])
        assert proc.returncode == 2

    def test_usage_error(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.retrieval.search"],
            capture_output=True,
        )
        assert proc.returncode == 2


class TestUtf8Output:
    def test_utf8_without_env_var(self, tmp_path: Path) -> None:
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n")])
        proc = subprocess.run(
            [sys.executable, "-m", "campus_assistant.retrieval.search",
             "--manifest", str(mp), "--corpus-root", str(tmp_path),
             "--query", "缓考"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={},
        )
        assert proc.returncode == 0
        text = proc.stdout.decode("utf-8")
        out = json.loads(text)
        assert out["valid"] is True


class TestIndexedChunkCount:
    def test_mixed_valid_and_punctuation(self, tmp_path: Path) -> None:
        """Valid text + punctuation-only line → indexed < total."""
        mp = _make_corpus(tmp_path, [("doc.txt", "缓考申请\n\n!!!\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "缓考", "--max-chars", "500"])
        assert proc.returncode == 0
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["chunk_count"] == 2
        assert out["indexed_chunk_count"] == 1
        assert len(out["hits"]) == 1

    def test_all_punctuation(self, tmp_path: Path) -> None:
        """All punctuation → valid=true, indexed=0, hits=[], exit 0."""
        mp = _make_corpus(tmp_path, [("doc.txt", "!!!\n\n???\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "缓考", "--max-chars", "500"])
        assert proc.returncode == 0
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is True
        assert out["chunk_count"] == 2
        assert out["indexed_chunk_count"] == 0
        assert out["hits"] == []

    def test_no_chunks_empty_doc(self, tmp_path: Path) -> None:
        """Empty document → parse EMPTY_DOCUMENT error, valid=false, exit 1."""
        mp = _make_corpus(tmp_path, [("doc.txt", "")])
        proc = _run_cli(tmp_path, mp, ["--query", "test", "--max-chars", "500"])
        assert proc.returncode == 1
        out = json.loads(proc.stdout.decode("utf-8"))
        assert out["valid"] is False
        assert out["chunk_count"] == 0
        assert out["indexed_chunk_count"] == 0
        assert out["hits"] == []


class TestChunkManifestCalledOnce:
    def test_single_call(self, tmp_path: Path, monkeypatch) -> None:
        """chunk_manifest should be called exactly once per search invocation."""
        from campus_assistant.corpus import chunk as chunk_mod
        from campus_assistant.retrieval.search import _run_search
        call_count = {"n": 0}
        original = chunk_mod.chunk_manifest

        def counting(*args, **kwargs):
            call_count["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(chunk_mod, "chunk_manifest", counting)
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        _run_search(mp, tmp_path, query="test")
        assert call_count["n"] == 1

    def test_invalid_param_cli_exits_2(self, tmp_path: Path) -> None:
        """Invalid max_chars should exit 2 via argparse before _run_search."""
        mp = _make_corpus(tmp_path, [("doc.txt", "test\n")])
        proc = _run_cli(tmp_path, mp, ["--query", "test", "--max-chars", "0"])
        assert proc.returncode == 2
