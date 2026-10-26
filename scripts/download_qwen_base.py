"""Download Qwen/Qwen3.5-4B locally, then merge the LoRA on this machine.

One connection to Hugging Face stays near 70 KB/s. Eight connections together
reach about 1 MB/s, so the shards are fetched in pieces and resumed if a
piece stalls. The merge runs only after both files match the published sizes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "qwen35_base"
PARTS = DEST / "parts"
CACHE = Path(
    r"C:\Users\sbera\.cache\huggingface\hub\models--Qwen--Qwen3.5-4B"
    r"\snapshots\851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
)
CURL = Path(r"C:\Windows\System32\curl.exe")
REPO = "https://huggingface.co/Qwen/Qwen3.5-4B/resolve/main"
CONNECTIONS = 8
SHARDS = (
    ("model.safetensors-00001-of-00002.safetensors", 5_329_398_688),
    ("model.safetensors-00002-of-00002.safetensors", 3_990_429_408),
)
TOTAL = sum(size for _, size in SHARDS)

_state = {"done": 0}
_lock = threading.Lock()


def _ranges(total: int, pieces: int) -> list[tuple[int, int]]:
    chunk = (total + pieces - 1) // pieces
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < total:
        end = min(total - 1, start + chunk - 1)
        ranges.append((start, end))
        start = end + 1
    return ranges


def _bytes_done() -> int:
    with _lock:
        done = _state["done"]
    part_bytes = 0
    if PARTS.exists():
        part_bytes = sum(path.stat().st_size for path in PARTS.glob("*.part"))
    return done + part_bytes


def _heartbeat(stop: threading.Event) -> None:
    last = _bytes_done()
    last_at = time.monotonic()
    while not stop.wait(20):
        now = time.monotonic()
        current = _bytes_done()
        speed = (current - last) / max(now - last_at, 0.1)
        print(
            f"progress {current / 1_048_576:.1f} MB of {TOTAL / 1_048_576:.1f} MB"
            f" at {speed / 1_048_576:.2f} MB/s",
            flush=True,
        )
        last, last_at = current, now


def _fetch_part(url: str, start: int, end: int, dest: Path) -> None:
    expected = end - start + 1
    stalls = 0
    attempt = dest.with_suffix(dest.suffix + ".tmp")
    while True:
        have = dest.stat().st_size if dest.exists() else 0
        if have > expected:
            dest.unlink()
            have = 0
        if have == expected:
            if attempt.exists():
                attempt.unlink()
            return
        if attempt.exists():
            attempt.unlink()
        command = [
            str(CURL),
            "-L",
            "--fail",
            "--speed-limit",
            "2000",
            "--speed-time",
            "40",
            "-r",
            f"{start + have}-{end}",
            "-s",
            url,
        ]
        with attempt.open("wb") as handle:
            subprocess.call(command, stdout=handle)
        got = attempt.stat().st_size if attempt.exists() else 0
        if got and have + got <= expected:
            with dest.open("ab") as handle, attempt.open("rb") as source:
                shutil.copyfileobj(source, handle, length=8 * 1024 * 1024)
            attempt.unlink()
            stalls = 0
            continue
        if attempt.exists():
            attempt.unlink()
        stalls += 1
        if stalls >= 8:
            raise SystemExit(f"No progress on {dest.name} after {stalls} tries.")
        time.sleep(min(30, 2 * stalls))


def _download_shard(name: str, size: int) -> None:
    final = DEST / name
    if final.is_file() and final.stat().st_size == size:
        for part in PARTS.glob(f"{name}.*.part"):
            part.unlink()
        print(f"{name} already complete", flush=True)
        with _lock:
            _state["done"] += size
        return
    if final.exists():
        final.unlink()
    ranges = _ranges(size, CONNECTIONS)
    print(f"downloading {name} in {len(ranges)} pieces", flush=True)
    url = f"{REPO}/{name}"
    for index, (start, end) in enumerate(ranges):
        part = PARTS / f"{name}.{index:02d}.part"
        if part.exists() and part.stat().st_size > (end - start + 1):
            print(f"dropping oversized {part.name}", flush=True)
            part.unlink()
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
        futures = [
            pool.submit(_fetch_part, url, start, end, PARTS / f"{name}.{index:02d}.part")
            for index, (start, end) in enumerate(ranges)
        ]
        for future in futures:
            future.result()
    print(f"joining {name}", flush=True)
    with final.open("wb") as handle:
        for index in range(len(ranges)):
            part = PARTS / f"{name}.{index:02d}.part"
            with part.open("rb") as source:
                shutil.copyfileobj(source, handle, length=8 * 1024 * 1024)
    if final.stat().st_size != size:
        raise SystemExit(f"{name} is {final.stat().st_size} bytes, expected {size}.")
    with _lock:
        _state["done"] += size
    for index in range(len(ranges)):
        (PARTS / f"{name}.{index:02d}.part").unlink()
    print(f"{name} complete", flush=True)


def _copy_config() -> None:
    if not (CACHE / "config.json").is_file():
        raise SystemExit(f"Missing cached config at {CACHE}")
    for path in CACHE.iterdir():
        if not path.is_file() or path.name.startswith("model.safetensors"):
            continue
        target = DEST / path.name
        if target.exists() and target.stat().st_size == path.stat().st_size:
            continue
        shutil.copyfile(path, target)
    index = CACHE / "model.safetensors.index.json"
    target = DEST / index.name
    if not target.exists() or target.stat().st_size != index.stat().st_size:
        shutil.copyfile(index, target)


def main() -> None:
    if not CURL.is_file():
        raise SystemExit(f"curl is missing at {CURL}")
    DEST.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    _copy_config()
    stop = threading.Event()
    beat = threading.Thread(target=_heartbeat, args=(stop,), daemon=True)
    beat.start()
    try:
        for name, size in SHARDS:
            _download_shard(name, size)
    finally:
        stop.set()
    partial = DEST / "model.safetensors-00001-of-00002.safetensors.partial"
    if partial.exists():
        partial.unlink()
    print("download complete, merging on this PC", flush=True)
    code = subprocess.call([sys.executable, str(ROOT / "scripts" / "merge_mapper.py")])
    raise SystemExit(code)


if __name__ == "__main__":
    main()
