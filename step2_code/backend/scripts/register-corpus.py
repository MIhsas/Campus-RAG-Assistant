"""Local corpus registration helper (T021).

Takes ONE local file (TXT/DOCX/PDF) plus required manifest metadata (JSON),
computes the file hash, copies the original file bytes into a NEW candidate
corpus package directory (original copy + manifest.json), then reuses the
existing validate + parse checks and prints a readable result with a startup
command.

Rules:
- only writes into the specified NEW output directory; never overwrites an
  existing library;
- missing required metadata is listed explicitly — titles, publish dates,
  scope or validity are NEVER guessed;
- does not download source_url and never modifies the input file.

Metadata JSON example:
{
  "document_id": "my-doc-001",
  "policy_group_id": "my-group",
  "title": "……",
  "source_url": "https://…",
  "source_site": "……",
  "version_label": "……",
  "published_at": null,
  "effective_from": null,
  "effective_to": null,
  "scope": {"campus": [], "student_type": [], "admission_years": []},
  "is_synthetic": true
}

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\register-corpus.py --input <file> --meta <meta.json> --out-dir <new-dir>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "document_id", "policy_group_id", "title", "source_url", "source_site",
    "version_label", "published_at", "effective_from", "effective_to",
    "scope", "is_synthetic",
]
SUPPORTED = {".txt", ".docx", ".pdf"}


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="本地语料登记辅助（TXT/DOCX/PDF，不猜测元数据）")
    parser.add_argument("--input", required=True, help="本地原文文件（不会被修改）")
    parser.add_argument("--meta", required=True, help="元数据 JSON（缺字段会明确列出）")
    parser.add_argument("--out-dir", required=True, help="新的候选语料包输出目录（不覆盖已有内容）")
    args = parser.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        print(f"输入文件不存在：{src}")
        return 2
    ext = src.suffix.lower()
    if ext not in SUPPORTED:
        print(f"不支持的文件格式：{ext}（支持 TXT/DOCX/PDF）")
        return 2

    try:
        meta_raw = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"元数据 JSON 无法读取：{type(e).__name__}")
        return 2
    if not isinstance(meta_raw, dict):
        print("元数据必须是 JSON 对象")
        return 2

    missing = [f for f in REQUIRED_FIELDS if f not in meta_raw]
    if missing:
        print("缺少必填元数据字段（请补全，系统不猜测学校政策信息）：")
        for f in missing:
            print(f"  - {f}")
        return 2
    scope = meta_raw.get("scope")
    if not isinstance(scope, dict) or any(k not in scope for k in ("campus", "student_type", "admission_years")):
        print("scope 必须包含 campus / student_type / admission_years 三个键")
        return 2
    # is_synthetic 只接受 JSON 布尔值；不做 bool() 强转（字符串"false"会误变为 True）
    if not isinstance(meta_raw.get("is_synthetic"), bool):
        print("is_synthetic 必须是 JSON 布尔值（true/false），不接受字符串、数字或 null")
        return 2

    out_dir = Path(args.out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"输出目录已存在且非空，拒绝覆盖：{out_dir}")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    dest = out_dir / src.name
    shutil.copyfile(src, dest)  # 原文逐字节复制；输入文件不被修改
    sha = hashlib.sha256(dest.read_bytes()).hexdigest()

    entry = {
        "document_id": meta_raw["document_id"],
        "policy_group_id": meta_raw["policy_group_id"],
        "title": meta_raw["title"],
        "source_url": meta_raw["source_url"],
        "source_site": meta_raw["source_site"],
        "local_path": src.name,
        "sha256": sha,
        "version_label": meta_raw["version_label"],
        "published_at": meta_raw["published_at"],
        "effective_from": meta_raw["effective_from"],
        "effective_to": meta_raw["effective_to"],
        "scope": {
            "campus": meta_raw["scope"]["campus"],
            "student_type": meta_raw["scope"]["student_type"],
            "admission_years": meta_raw["scope"]["admission_years"],
        },
        "is_synthetic": meta_raw["is_synthetic"],  # 严格布尔，原值保留
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"schema_version": "1.0", "documents": [entry]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 复用既有校验/解析检查
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.corpus.validate import validate_manifest

    result = validate_manifest(manifest_path, out_dir)
    parsed = parse_manifest(manifest_path, out_dir)

    lines = [
        f"候选语料包：{out_dir}",
        f"原文复制：{dest.name}（sha256={sha[:16]}…，输入文件未修改）",
        f"登记校验：{'通过' if result.get('valid') else '未通过'}",
        f"解析检查：{'通过' if parsed.get('valid') else '未通过'}（文档 {len(parsed.get('documents', []))}，错误 {len(parsed.get('errors', []))}）",
    ]
    for e in (result.get('errors') or []) + (parsed.get('errors') or []):
        lines.append(f"  - {e.get('code')}: {e.get('message')}")
    for d in parsed.get('documents', []):
        pages = len({b.get('locator', {}).get('page') for b in d.get('blocks', []) if b.get('locator', {}).get('type') == 'pdf_page'})
        lines.append(f"  - {d['document_id']}: {len(d['blocks'])} 块" + (f"，{pages} 页" if pages else ""))
    lines.append("启动命令（不加载任何合成模板/规则/mock 生成器；路径含空格可直接复制）：")
    lines.append(
        '  & .\\.venv\\Scripts\\python.exe scripts\\serve-corpus.py '
        f'--manifest "{manifest_path}" --corpus-root "{out_dir}"'
    )
    print("\n".join(lines))
    ok = result.get("valid") and parsed.get("valid")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
