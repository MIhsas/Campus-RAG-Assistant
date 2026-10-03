"""Download the local ASR model into the project cache (T020).

Model installation/download is separate from service runtime: the ASR
service only loads from a configured local directory and never starts an
automatic download. This helper downloads one public model snapshot
(FunASR Paraformer zh) into .cache/asr-models/ via ModelScope — local file
fetch only; no inference, no audio upload, no proxy changes.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\download-asr-model.py [--model-id iic/...] [--out-dir .cache/asr-models/paraformer-zh]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_MODEL_ID = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"


def main() -> int:
    parser = argparse.ArgumentParser(description="下载本地 ASR 模型（仅文件下载，无推理）")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--out-dir", default=".cache/asr-models/paraformer-zh")
    args = parser.parse_args()

    from modelscope.hub.snapshot_download import snapshot_download

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(args.model_id, local_dir=str(out))

    # 记录文件清单与哈希（供 provenance 记录；不包含任何密钥）
    files = []
    for f in sorted(Path(path).rglob("*")):
        if f.is_file():
            files.append({
                "name": str(f.relative_to(path)),
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                "size": f.stat().st_size,
            })
    record = {"model_id": args.model_id, "source": "ModelScope 公开模型快照", "local_dir": str(path), "files": files}
    (out / "PROVENANCE.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model_id": args.model_id, "local_dir": str(path), "files": len(files),
                      "total_bytes": sum(f["size"] for f in files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
