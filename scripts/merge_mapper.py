"""Download the Tinker LoRA and merge it into Qwen3.5-4B one shard at a time.

The merged Hugging Face folder is the input for the GGUF conversion. This
does not load the whole model at once.

    .\\.venv\\Scripts\\python.exe scripts\\merge_mapper.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKPOINT = "tinker://dc5187e2-b9cb-5b09-be4e-ec338c6d4ae8:train:0/sampler_weights/slothfill-mapper"
ADAPTER_DIR = ROOT / "data" / "tinker_adapter"
MERGED_DIR = ROOT / "data" / "merged_mapper"
LOCAL_BASE = ROOT / "data" / "qwen35_base"
SHARD_SIZES = {
    "model.safetensors-00001-of-00002.safetensors": 5_329_398_688,
    "model.safetensors-00002-of-00002.safetensors": 3_990_429_408,
}


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    _load_dotenv()
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not set.")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from tinker_cookbook import weights

    if not (ADAPTER_DIR / "adapter_model.safetensors").exists():
        print("downloading adapter", flush=True)
        weights.download(tinker_path=CHECKPOINT, output_dir=str(ADAPTER_DIR))
    else:
        print("adapter already downloaded", flush=True)
    if MERGED_DIR.exists():
        raise SystemExit(f"{MERGED_DIR} already exists. Not merging over it.")
    ready = (LOCAL_BASE / "config.json").is_file() and all(
        (LOCAL_BASE / name).is_file() and (LOCAL_BASE / name).stat().st_size == size
        for name, size in SHARD_SIZES.items()
    )
    if not ready:
        raise SystemExit(
            "Base weights are not complete in data/qwen35_base. "
            "Run scripts/download_qwen_base.py first."
        )
    os.environ["HF_HUB_OFFLINE"] = "1"
    print(f"merging local weights in {LOCAL_BASE} one shard at a time", flush=True)
    weights.build_hf_model(
        base_model=str(LOCAL_BASE),
        adapter_path=str(ADAPTER_DIR),
        output_path=str(MERGED_DIR),
        merge_strategy="shard",
        trust_remote_code=True,
    )
    print(f"merged model at {MERGED_DIR}", flush=True)


if __name__ == "__main__":
    main()
