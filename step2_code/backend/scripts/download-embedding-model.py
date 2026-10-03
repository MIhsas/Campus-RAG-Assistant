"""Download BAAI/bge-small-zh-v1.5 embedding model.

Usage:
    python scripts/download-embedding-model.py [--output-dir models]

Downloads config, tokenizer, and model weights to the specified directory.
Only downloads one weight format (safetensors) — pytorch_model.bin is
skipped. Existing local weights are not re-downloaded or deleted.
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Download BGE embedding model")
    parser.add_argument("--output-dir", default="models", help="Output directory")
    parser.add_argument("--model-name", default="BAAI/bge-small-zh-v1.5",
                       help="Hugging Face model name")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {args.model_name} to {output_dir}...")

    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=args.model_name,
        local_dir=str(output_dir),
        local_dir_use_symlinks=False,
        # Only one weight format going forward; do not remove any
        # previously downloaded weights.
        ignore_patterns=["*.bin", "tf_model.h5*", "flax_model.msgpack"],
    )
    print(f"Model downloaded to {output_dir}")

if __name__ == "__main__":
    main()
