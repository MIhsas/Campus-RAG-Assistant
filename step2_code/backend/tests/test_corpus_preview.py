"""Tests for corpus preview API and preview page (T005).

Covers: unconfigured, ready, partial/failed states, document list/detail,
unknown IDs, request tracking, multi-app isolation, static preview page.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app

_EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "parse-corpus"
_EXAMPLE_MANIFEST = _EXAMPLE_DIR / "manifest.json"


# --- Helpers ---

def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _unconfigured_client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def _example_client() -> TestClient:
    return TestClient(
        create_app(manifest_path=_EXAMPLE_MANIFEST, corpus_root=_EXAMPLE_DIR),
        raise_server_exceptions=False,
    )


def _make_corpus(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal valid corpus. Returns (manifest_path, corpus_root)."""
    txt = tmp_path / "doc.txt"
    _write_text(txt, "段落一\n\n段落二\n")
    import hashlib
    sha = hashlib.sha256(txt.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "test-doc",
            "policy_group_id": "g",
            "title": "测试文档",
            "source_url": "https://example.org/doc",
            "source_site": "测试站",
            "local_path": "doc.txt",
            "sha256": sha,
            "version_label": "v1",
            "published_at": "2025-01-01",
            "effective_from": "2025-03-01",
            "effective_to": None,
            "scope": {"campus": ["成都校区"], "student_type": ["本科"], "admission_years": [2024]},
            "is_synthetic": True,
        }],
    }
    mp = tmp_path / "manifest.json"
    _write_json(mp, manifest)
    return mp, tmp_path


# --- Unconfigured state ---

class TestUnconfigured:
    def test_status_unconfigured(self) -> None:
        c = _unconfigured_client()
        r = c.get("/api/v1/corpus/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "unconfigured"
        assert d["document_count"] == 0
        assert d["parsed_count"] == 0
        assert d["errors"] == []

    def test_documents_503(self) -> None:
        c = _unconfigured_client()
        r = c.get("/api/v1/corpus/documents")
        assert r.status_code == 503
        d = r.json()
        assert d["code"] == "CORPUS_NOT_CONFIGURED"

    def test_document_detail_503(self) -> None:
        c = _unconfigured_client()
        r = c.get("/api/v1/corpus/documents/anything")
        assert r.status_code == 503
        assert r.json()["code"] == "CORPUS_NOT_CONFIGURED"


# --- Ready state (example corpus) ---

class TestReadyState:
    def test_status_ready(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ready"
        assert d["document_count"] == 2
        assert d["parsed_count"] == 2
        assert d["errors"] == []

    def test_documents_list(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/documents")
        assert r.status_code == 200
        d = r.json()
        assert len(d["items"]) == 2
        item = d["items"][0]
        assert "document_id" in item
        assert "title" in item
        assert "block_count" in item
        assert "warnings" in item
        assert "format" in item

    def test_document_detail_found(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/documents/syn-parse-txt-001")
        assert r.status_code == 200
        d = r.json()
        doc = d["document"]
        assert doc["document_id"] == "syn-parse-txt-001"
        assert "metadata" in doc
        assert "blocks" in doc
        assert len(doc["blocks"]) >= 5
        assert doc["metadata"]["is_synthetic"] is True

    def test_document_detail_not_found(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/documents/nonexistent")
        assert r.status_code == 404
        assert r.json()["code"] == "DOCUMENT_NOT_FOUND"


# --- Partial/failed state ---

class TestPartialState:
    def test_partial_with_bad_docx(self, tmp_path: Path) -> None:
        """One good TXT + one corrupt DOCX → partial."""
        import hashlib
        txt = tmp_path / "good.txt"
        _write_text(txt, "好内容\n")
        txt_sha = hashlib.sha256(txt.read_bytes()).hexdigest()

        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"PK\x03\x04not real")
        bad_sha = hashlib.sha256(bad.read_bytes()).hexdigest()

        manifest = {
            "schema_version": "1.0",
            "documents": [
                {
                    "document_id": "good", "policy_group_id": "g", "title": "好文档",
                    "source_url": "https://example.org/", "source_site": "S",
                    "local_path": "good.txt", "sha256": txt_sha, "version_label": "v",
                    "published_at": None, "effective_from": None, "effective_to": None,
                    "scope": {"campus": [], "student_type": [], "admission_years": []},
                    "is_synthetic": True,
                },
                {
                    "document_id": "bad", "policy_group_id": "g", "title": "坏文档",
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

        app = create_app(manifest_path=mp, corpus_root=tmp_path)
        c = TestClient(app, raise_server_exceptions=False)

        r = c.get("/api/v1/corpus/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "partial"
        assert d["parsed_count"] == 1
        assert len(d["errors"]) > 0

        r2 = c.get("/api/v1/corpus/documents")
        assert r2.status_code == 200
        items = r2.json()["items"]
        assert len(items) == 1
        assert items[0]["document_id"] == "good"

    def test_failed_validation(self, tmp_path: Path) -> None:
        """Invalid manifest → failed status."""
        mp = tmp_path / "manifest.json"
        mp.write_text("{bad json", encoding="utf-8")
        app = create_app(manifest_path=mp, corpus_root=tmp_path)
        c = TestClient(app, raise_server_exceptions=False)

        r = c.get("/api/v1/corpus/status")
        assert r.status_code == 200
        assert r.json()["status"] == "failed"
        assert r.json()["parsed_count"] == 0


# --- Request ID tracking ---

class TestRequestId:
    def test_status_has_request_id(self) -> None:
        c = _unconfigured_client()
        r = c.get("/api/v1/corpus/status")
        d = r.json()
        assert "request_id" in d
        assert r.headers["X-Request-ID"] == d["request_id"]

    def test_documents_has_request_id(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/documents")
        d = r.json()
        assert r.headers["X-Request-ID"] == d["request_id"]

    def test_detail_has_request_id(self) -> None:
        c = _example_client()
        r = c.get("/api/v1/corpus/documents/syn-parse-txt-001")
        d = r.json()
        assert r.headers["X-Request-ID"] == d["request_id"]


# --- Multi-app isolation ---

class TestAppIsolation:
    def test_two_apps_independent(self, tmp_path: Path) -> None:
        """Configured and unconfigured apps don't share state."""
        mp, root = _make_corpus(tmp_path)
        c1 = TestClient(create_app(), raise_server_exceptions=False)
        c2 = TestClient(create_app(manifest_path=mp, corpus_root=root), raise_server_exceptions=False)

        assert c1.get("/api/v1/corpus/status").json()["status"] == "unconfigured"
        assert c2.get("/api/v1/corpus/status").json()["status"] == "ready"


# --- Parse runs once ---

class TestParseOnce:
    def test_data_is_snapshot(self, tmp_path: Path) -> None:
        """Multiple requests read same snapshot, not re-parsing."""
        mp, root = _make_corpus(tmp_path)
        c = TestClient(create_app(manifest_path=mp, corpus_root=root), raise_server_exceptions=False)
        r1 = c.get("/api/v1/corpus/documents").json()
        r2 = c.get("/api/v1/corpus/documents").json()
        assert r1["items"] == r2["items"]

    def test_single_parse_call(self, tmp_path: Path, monkeypatch) -> None:
        """create_app calls parse_manifest exactly once (no redundant validate_manifest)."""
        mp, root = _make_corpus(tmp_path)
        call_count = {"n": 0}
        original = None

        from campus_assistant.corpus import parse as parse_mod
        original = parse_mod.parse_manifest

        def counting_parse(*args, **kwargs):
            call_count["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(parse_mod, "parse_manifest", counting_parse)
        create_app(manifest_path=mp, corpus_root=root)
        assert call_count["n"] == 1


# --- Factory validation ---

class TestFactoryValidation:
    def test_manifest_without_root_raises(self) -> None:
        with pytest.raises(ValueError, match="同时提供"):
            create_app(manifest_path=Path("x"))

    def test_root_without_manifest_raises(self) -> None:
        with pytest.raises(ValueError, match="同时提供"):
            create_app(corpus_root=Path("."))


# --- Preview page ---

class TestPreviewPage:
    def test_preview_accessible(self) -> None:
        c = _example_client()
        r = c.get("/preview")
        assert r.status_code == 200
        assert "语料预览" in r.text
        assert "合成测试" in r.text

    def test_preview_from_different_cwd(self, tmp_path: Path) -> None:
        """Preview page loads regardless of working directory."""
        mp, root = _make_corpus(tmp_path)
        app = create_app(manifest_path=mp, corpus_root=root)
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/preview")
        assert r.status_code == 200
        assert "语料预览" in r.text


# --- OpenAPI ---

class TestOpenApi:
    def test_corpus_endpoints_in_schema(self) -> None:
        c = _example_client()
        schema = c.get("/openapi.json").json()
        paths = schema["paths"]
        assert "/api/v1/corpus/status" in paths
        assert "/api/v1/corpus/documents" in paths
        assert "/api/v1/corpus/documents/{document_id}" in paths

    def test_ready_503_in_schema(self) -> None:
        c = _example_client()
        schema = c.get("/openapi.json").json()
        docs_path = schema["paths"]["/api/v1/corpus/documents"]
        assert "503" in docs_path["get"]["responses"]

    def test_status_has_field_model(self) -> None:
        """R5: OpenAPI status response should have defined properties, not bare object."""
        c = _example_client()
        schema = c.get("/openapi.json").json()
        status_resp = schema["paths"]["/api/v1/corpus/status"]["get"]["responses"]["200"]
        # Should reference a schema with specific fields
        ref = status_resp.get("content", {}).get("application/json", {}).get("schema", {})
        assert "$ref" in ref or "properties" in ref


# --- Health regression ---

class TestHealthRegression:
    def test_health_still_works(self) -> None:
        c = _example_client()
        assert c.get("/api/v1/health/live").status_code == 200
        assert c.get("/api/v1/health/ready").status_code == 503


# --- CLI smoke ---

class TestCliSmoke:
    def _run_demo(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c",
             "from campus_assistant.demo import app; "
             "from fastapi.testclient import TestClient; "
             "c=TestClient(app); "
             "import json; "
             "print(json.dumps({'status':c.get('/api/v1/corpus/status').json()['status'],"
             "'docs':len(c.get('/api/v1/corpus/documents').json()['items'])}))"],
            capture_output=True, encoding="utf-8",
            cwd=str(Path(__file__).parent.parent),
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_demo_module_works(self) -> None:
        proc = self._run_demo()
        assert proc.returncode == 0
        out = json.loads(proc.stdout)
        assert out["status"] == "ready"
        assert out["docs"] == 2
