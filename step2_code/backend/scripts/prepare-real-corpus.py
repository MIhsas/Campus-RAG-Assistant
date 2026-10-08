"""T029: build a product-readable corpus pack from the real dataset (read-only input).

Maps the dataset's manifest.jsonl entries (explicit selection list) to the
product manifest.json contract (corpus.models.Document):

- copies selected ORIGINAL FILES byte-identically into the pack (sha256 kept);
- document_id = dataset doc_id (64-hex = file sha256, satisfies product ID rules);
- source_site is derived from the SELECTED source_url host (dataset "site"
  sometimes names the source-page site, not the attachment host — the original
  site records are preserved verbatim in provenance);
- keeps original relative_path / all sources / selection reason in sidecars;
- unknown metadata is preserved as unknown (null / empty arrays) — never guessed;
- refuses to silently overwrite an existing pack: re-runs run in VERIFY mode,
  which must detect ANY input/sidecar drift (source bytes, selection evidence,
  provenance) and exit non-zero WITHOUT writing.

The dataset root is READ-ONLY (including its verification.json — this script
never writes there). No parsing framework is introduced here; parsing/validation
is done by the existing campus_assistant.corpus pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))

import re as _re

ID_RE = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_dataset(dataset_root: Path):
    rows = {}
    manifest_path = dataset_root / "manifest.jsonl"
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["doc_id"]] = r
    return rows, _sha256(manifest_path)


def _site_from_url(url: str) -> str:
    """Product source_site = host of the SELECTED source_url.

    The dataset's sources[].site may name the source-page site instead of
    the attachment host; the original records stay in provenance.
    """
    try:
        host = urlparse(url).hostname
    except ValueError:
        return ""
    return host or ""


def _map_entry(row: dict, sel: dict) -> dict:
    """Map one dataset row + selection overrides to a product manifest entry."""
    sources = row.get("sources") or []
    idx = sel.get("source_url_index", 0)
    src = sources[idx] if sources else {}
    ext = row["relative_path"].rsplit(".", 1)[-1]
    doc_id = row["doc_id"]
    if not ID_RE.match(doc_id):
        raise SystemExit(f"doc_id 不符合产品 ID 规则: {doc_id}")
    group = sel.get("policy_group_id") or f"sicau-{doc_id[:12]}"
    if not ID_RE.match(group):
        raise SystemExit(f"policy_group_id 不符合产品 ID 规则: {group}")
    return {
        "document_id": doc_id,
        "policy_group_id": group,
        "title": row["title"],
        "source_url": src.get("url") or "",
        "source_site": _site_from_url(src.get("url") or ""),
        "local_path": f"{doc_id}.{ext}",
        "sha256": row["sha256"],
        "version_label": sel.get("version_label") or "未标注",
        "published_at": sel.get("published_at"),
        "effective_from": sel.get("effective_from"),
        "effective_to": sel.get("effective_to"),
        "scope": sel.get("scope") or {"campus": [], "student_type": [], "admission_years": []},
        "is_synthetic": False,
    }


def _build_expected(dataset_root: Path, selection_path: Path):
    """Derive (manifest, provenance) from CURRENT inputs (no writes)."""
    rows, manifest_sha = _load_dataset(dataset_root)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    docs = [d for d in selection["docs"] if d.get("decision") == "include"]
    if not docs:
        raise SystemExit("selection 中没有 include 条目")
    manifest = {"schema_version": "1.0", "documents": []}
    provenance = []
    input_hashes = {}
    for sel in docs:
        doc_id = sel["doc_id"]
        row = rows.get(doc_id)
        if row is None:
            raise SystemExit(f"doc_id 不在数据集 manifest 中: {doc_id}")
        src_file = dataset_root / row["relative_path"]
        if not src_file.is_file():
            raise SystemExit(f"原文件缺失（数据集不完整）: {row['relative_path']}")
        input_hashes[doc_id] = _sha256(src_file)
        manifest["documents"].append(_map_entry(row, sel))
        sources = row.get("sources") or []
        provenance.append({
            "document_id": doc_id,
            "original_relative_path": row["relative_path"],
            "original_sha256": row["sha256"],
            "title": row["title"],
            "material_type": row.get("material_type"),
            "topic": row.get("topic"),
            "processing_required": row.get("processing_required"),
            "inspection_status": row.get("inspection_status"),
            "all_sources": row.get("sources"),
            "source_sites": row.get("source_sites"),
            "source_url_index": sel.get("source_url_index", 0),
            "selected_source_url": (sources[sel.get("source_url_index", 0)] or {}).get("url") if sources else None,
            "selected_source_site_resolved": _site_from_url((sources[sel.get("source_url_index", 0)] or {}).get("url") or "") if sources else None,
            "year_hints": row.get("year_hints"),
            "related_versions": row.get("related_versions"),
            "selection_reason": sel.get("reason"),
            "selection_notes": sel.get("notes"),
            "mapping_limits": sel.get("mapping_limits"),
            "dataset_manifest_sha256": manifest_sha,
        })
    return manifest, provenance, selection, input_hashes


def _structured_diff(saved_text: str, derived_obj: Any, label: str) -> list[str]:
    try:
        saved = json.loads(saved_text)
    except ValueError:
        return [f"{label} 无法解析（非合法 JSON）"]
    if saved != derived_obj:
        return [f"{label} 与当前推导结果不一致（结构化比较）"]
    return []


def verify(out_dir: Path, manifest: dict, provenance: list, selection: dict,
           input_hashes: dict[str, str]) -> int:
    """核验模式：不写入。任何输入/边车漂移明确报出并非零退出。"""
    diffs: list[str] = []

    # 1) 输入原文件 SHA（只查选定文件，不重哈希全库）
    for doc_id, digest in input_hashes.items():
        entry = next((e for e in manifest["documents"] if e["document_id"] == doc_id), None)
        if entry is None:
            diffs.append(f"推导 manifest 缺文档: {doc_id}")
            continue
        if digest != entry["sha256"]:
            diffs.append(
                f"输入原文件 SHA 与数据集声明不一致: {doc_id}（文件 {digest[:16]}… ≠ 声明 {entry['sha256'][:16]}…）")

    # 2) 产品 manifest（结构化）
    mp = out_dir / "manifest.json"
    if not mp.is_file():
        diffs.append("缺 manifest.json")
    else:
        diffs.extend(_structured_diff(mp.read_text(encoding="utf-8"), manifest, "manifest.json"))

    # 3) 已保存 selection 副本（结构化）
    sp = out_dir / "selection.json"
    if not sp.is_file():
        diffs.append("缺 selection.json")
    else:
        diffs.extend(_structured_diff(sp.read_text(encoding="utf-8"), selection, "selection.json"))

    # 4) 已保存 provenance（逐条结构化）
    pp = out_dir / "provenance.jsonl"
    if not pp.is_file():
        diffs.append("缺 provenance.jsonl")
    else:
        saved_rows = [json.loads(l) for l in pp.read_text(encoding="utf-8").splitlines() if l.strip()]
        if saved_rows != provenance:
            diffs.append("provenance.jsonl 与当前推导结果不一致（逐条结构化比较）")

    # 5) 输出原文件存在 + 字节哈希
    for e in manifest["documents"]:
        f = out_dir / e["local_path"]
        if not f.is_file():
            diffs.append(f"缺文件: {e['local_path']}")
        elif _sha256(f) != e["sha256"]:
            diffs.append(f"输出文件哈希不符: {e['local_path']}")

    # 6) 产品校验器（有效性）
    if mp.is_file():
        try:
            from campus_assistant.corpus.validate import validate_manifest

            result = validate_manifest(mp, out_dir)
            if not result.get("valid", False):
                diffs.append(f"产品校验器判定无效: {result.get('errors')}")
        except Exception as e:  # noqa: BLE001
            diffs.append(f"产品校验器异常: {type(e).__name__}")

    if diffs:
        for d in diffs:
            print("DIFF:", d)
        print(f"VERIFY FAILED: {len(diffs)} 处不一致（不覆盖已有输出）")
        return 1
    print(f"VERIFY OK: {len(manifest['documents'])} 份输入/输出/边车一致（未写入）")
    return 0


def build(dataset_root: Path, selection_path: Path, out_dir: Path) -> int:
    from campus_assistant.corpus.validate import validate_manifest

    manifest, provenance, selection, input_hashes = _build_expected(dataset_root, selection_path)

    # 输入哈希预检（构建模式同样拒绝被改动的输入，不写入）
    bad_inputs = [
        did for did, digest in input_hashes.items()
        if digest != next(e["sha256"] for e in manifest["documents"] if e["document_id"] == did)
    ]
    if bad_inputs:
        for did in bad_inputs:
            print("DIFF: 输入原文件 SHA 与数据集声明不一致:", did)
        raise SystemExit("输入原文件已被改动，拒绝构建（非零退出）")

    if (out_dir / "manifest.json").is_file():
        return verify(out_dir, manifest, provenance, selection, input_hashes)

    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"输出目录已存在且非空，拒绝覆盖: {out_dir}（如需核验请用同一命令重跑）")
    out_dir.mkdir(parents=True, exist_ok=True)
    for e in manifest["documents"]:
        ext = e["local_path"].rsplit(".", 1)[-1]
        row_src = dataset_root / next(
            p["original_relative_path"] for p in provenance if p["document_id"] == e["document_id"])
        dst = out_dir / e["local_path"]
        shutil.copyfile(row_src, dst)
        if _sha256(dst) != e["sha256"]:
            raise SystemExit(f"拷贝后哈希不一致: {e['document_id']}")
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "provenance.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in provenance) + "\n", encoding="utf-8")
    (out_dir / "selection.json").write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        result = validate_manifest(out_dir / "manifest.json", out_dir)
        ok = result.get("valid", False)
        errs = result.get("errors", [])
    except Exception as e:  # noqa: BLE001
        ok, errs = False, [{"message": f"validate 异常: {type(e).__name__}"}]
    print(f"manifest.json: {len(manifest['documents'])} 份；产品校验器: {'valid' if ok else 'INVALID'}")
    for e in errs[:10]:
        print("  ERR:", e)
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="真实数据集→产品语料包（只读输入，显式选择清单）")
    p.add_argument("--dataset-root", required=True)
    p.add_argument("--selection", required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()
    return build(Path(a.dataset_root), Path(a.selection), Path(a.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
