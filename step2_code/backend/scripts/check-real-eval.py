"""T030 small verification tool: contract / quotes / admission / freeze checks.

Reuses existing classes and functions (QuestionDataset, parse, filters) —
does NOT implement another evaluator. Checks:

1. contract   — questions.json validates against QuestionDataset;
2. quotes     — every evidence quote equals its parsed-block slice exactly
                (char_start/char_end), document_sha256/parser_version match
                the frozen manifest/pack;
3. admission  — every gold evidence of an answerable question passes that
                question's own conditions (product T011 filter rules);
4. fact rules — fact_id groups: answerable questions have ≥1 fact; each fact
                has ≥1 source; unanswerable questions carry `missing`;
5. freeze     — with --freeze <freeze.json>, verify recorded hashes still
                match (questions/manifest/pack files/implementation files).

Exit 0 only when all checks pass; each failure is printed as FAIL line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(pack: Path, questions_path: Path, freeze_path: Path | None = None) -> int:
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.evaluation.models import QuestionDataset
    from campus_assistant.retrieval.filters import compute_allowed_document_ids

    fails: list[str] = []

    # 1) contract
    try:
        ds = QuestionDataset.model_validate(json.loads(questions_path.read_text(encoding="utf-8")))
    except Exception as e:  # noqa: BLE001
        print("FAIL contract:", e)
        return 1

    # pack parse
    result = parse_manifest(pack / "manifest.json", pack)
    if not result.get("valid"):
        print("FAIL corpus:", result.get("errors"))
        return 1
    docs = result["documents"]
    by_id = {d["document_id"]: d for d in docs}
    blocks = {}
    for d in docs:
        for b in d.get("blocks") or []:
            blocks[(d["document_id"], b["block_id"])] = b

    for q in ds.questions:
        # 2/4) quotes + fact rules
        if q.answerable:
            if not q.evidence:
                fails.append(f"{q.question_id}: 可答题缺 evidence")
            fact_ids = {}
            for ev in q.evidence:
                fact_ids.setdefault(ev.fact_id, []).append(ev.evidence_id)
                if not ev.fact_id:
                    fails.append(f"{q.question_id}/{ev.evidence_id}: 缺 fact_id")
                doc = by_id.get(ev.document_id)
                if doc is None:
                    fails.append(f"{q.question_id}/{ev.evidence_id}: 文档不在语料 {ev.document_id}")
                    continue
                if ev.document_sha256 != (doc.get("metadata") or {}).get("sha256"):
                    fails.append(f"{q.question_id}/{ev.evidence_id}: sha256 不符")
                if ev.parser_version != doc.get("parser_version"):
                    fails.append(f"{q.question_id}/{ev.evidence_id}: parser_version 不符")
                b = blocks.get((ev.document_id, ev.block_id))
                if b is None:
                    fails.append(f"{q.question_id}/{ev.evidence_id}: 块不存在 {ev.block_id}")
                    continue
                slice_ = b["text"][ev.char_start:ev.char_end]
                if slice_ != ev.quote:
                    fails.append(f"{q.question_id}/{ev.evidence_id}: quote 与块切片不一致")
            if not fact_ids:
                fails.append(f"{q.question_id}: 无 fact 分组")
            # 3) admission
            allowed = compute_allowed_document_ids(docs, q.conditions or None)["allowed_document_ids"]
            for ev in q.evidence:
                if allowed is not None and ev.document_id not in allowed:
                    fails.append(f"{q.question_id}/{ev.evidence_id}: 未通过本题条件准入（{ev.document_id}）")
        else:
            if q.evidence:
                fails.append(f"{q.question_id}: 不足题不得有 evidence")
            if not q.missing:
                fails.append(f"{q.question_id}: 不足题缺 missing")

    # 5) freeze（T024-R1…T030-R1：按本项目实际冻结结构逐节核验；
    #    缺关键节/空清单/旧结构/哈希错误/缺文件一律非零退出，不修补输入）
    checked = 0
    if freeze_path is not None:
        try:
            fz = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print("FAIL freeze: 无法解析", e)
            return 1
        if not isinstance(fz, dict):
            print("FAIL freeze: 顶层必须是对象")
            return 1
        if "files" in fz:
            print("FAIL freeze: 不支持的冻结结构（旧式顶层 files 清单）")
            return 1

        project_root = BACKEND.parent.parent  # step2_code/backend -> 项目根

        def _freeze_section(section: str) -> dict:
            nonlocal checked
            if section not in fz:
                fails.append(f"freeze 缺关键节: {section}")
                return {}
            v = fz[section]
            if not isinstance(v, dict):
                fails.append(f"freeze 节结构不符: {section} 应为对象")
                return {}
            return v

        # ① dataset：题集哈希
        ds_sec = _freeze_section("dataset")
        qh = ds_sec.get("questions_sha256")
        if not isinstance(qh, str) or len(qh) != 64:
            fails.append("freeze.dataset.questions_sha256 缺失或非 64 位哈希")
        else:
            checked += 1
            if _sha256(questions_path) != qh:
                fails.append("freeze: 题集 questions_sha256 与实际文件不符")

        # ② corpus_pack：manifest + 语料文件
        cp_sec = _freeze_section("corpus_pack")
        mh = cp_sec.get("manifest_sha256")
        if not isinstance(mh, str) or len(mh) != 64:
            fails.append("freeze.corpus_pack.manifest_sha256 缺失或非法")
        else:
            checked += 1
            if _sha256(pack / "manifest.json") != mh:
                fails.append("freeze: manifest_sha256 与实际文件不符")
        files = cp_sec.get("files")
        if not isinstance(files, dict) or not files:
            fails.append("freeze.corpus_pack.files 缺失或为空清单")
        else:
            for name, h in files.items():
                checked += 1
                f = pack / name
                if not f.is_file():
                    fails.append(f"freeze: 语料文件缺失 {name}")
                elif _sha256(f) != h:
                    fails.append(f"freeze: 语料文件哈希不符 {name}")

        # ③ implementation_sha256：实现文件（基准=后端目录）
        impl = _freeze_section("implementation_sha256")
        if not impl:
            fails.append("freeze.implementation_sha256 为空清单")
        for rel, h in impl.items():
            checked += 1
            f = BACKEND / rel
            if not f.is_file():
                fails.append(f"freeze: 实现文件缺失 {rel}")
            elif _sha256(f) != h:
                fails.append(f"freeze: 实现文件哈希不符 {rel}")

        # ④ embedding_model：模型身份文件（基准=模型目录）
        emb = _freeze_section("embedding_model")
        ident = emb.get("identity_files_sha256")
        if not isinstance(ident, dict) or not ident:
            fails.append("freeze.embedding_model.identity_files_sha256 缺失或为空")
        else:
            model_dir = Path(emb.get("dir") or "")
            if not model_dir.is_absolute():
                model_dir = BACKEND / model_dir
            for name, h in ident.items():
                checked += 1
                f = model_dir / name
                if not f.is_file():
                    fails.append(f"freeze: 模型身份文件缺失 {name}")
                elif _sha256(f) != h:
                    fails.append(f"freeze: 模型身份文件哈希不符 {name}")

        # ⑤ annotation_files：标注说明文件（基准=项目根；必需节）
        ann = _freeze_section("annotation_files")
        if not ann:
            fails.append("freeze.annotation_files 缺失或为空清单")
        for rel, h in ann.items():
            checked += 1
            f = project_root / rel
            if not f.is_file():
                fails.append(f"freeze: 标注说明文件缺失 {rel}")
            elif _sha256(f) != h:
                fails.append(f"freeze: 标注说明文件哈希不符 {rel}")

        if checked == 0 and not fails:
            fails.append("freeze: 未核验到任何哈希项（拒绝零项通过）")

    if fails:
        for f in fails:
            print("FAIL:", f)
        print(f"CHECK FAILED: {len(fails)} 项")
        return 1
    n_ev = sum(len(q.evidence) for q in ds.questions)
    if freeze_path is not None:
        print(f"CHECK OK: {len(ds.questions)} 题 / {n_ev} 条证据（契约、引句、准入、事实分组）"
              f"；冻结哈希核对 {checked} 项（dataset/corpus/implementation/model/annotation）")
    else:
        print(f"CHECK OK: {len(ds.questions)} 题 / {n_ev} 条证据（契约、引句、准入、事实分组）")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="T030 题集/标注小校验")
    p.add_argument("--pack", required=True)
    p.add_argument("--questions", required=True)
    p.add_argument("--freeze", default=None)
    a = p.parse_args()
    return check(Path(a.pack), Path(a.questions), Path(a.freeze) if a.freeze else None)


if __name__ == "__main__":
    raise SystemExit(main())
