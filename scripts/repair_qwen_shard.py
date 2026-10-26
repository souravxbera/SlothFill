"""Replace one byte range of a Qwen shard and leave the rest untouched.

The first parallel download kept piece 02 at the right length with the wrong
bytes. Quantize then found NaNs in the three tensors that sit in that piece.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CURL = Path(r"C:\Windows\System32\curl.exe")
URL = (
    "https://huggingface.co/Qwen/Qwen3.5-4B/resolve/main/"
    "model.safetensors-00001-of-00002.safetensors"
)
SHARD = Path(
    r"s:\Desktop\Desktop\SlothFill\data\qwen35_base"
    r"\model.safetensors-00001-of-00002.safetensors"
)
PARTS = SHARD.parent / "parts" / "repair"
START = 1_332_349_672
END = 1_998_524_507
PIECES = 8


def _ranges(start: int, end: int, pieces: int) -> list[tuple[int, int]]:
    total = end - start + 1
    chunk = (total + pieces - 1) // pieces
    ranges: list[tuple[int, int]] = []
    cursor = start
    while cursor <= end:
        stop = min(end, cursor + chunk - 1)
        ranges.append((cursor, stop))
        cursor = stop + 1
    return ranges


def _fetch(start: int, end: int, dest: Path) -> None:
    expected = end - start + 1
    stalls = 0
    attempt = dest.with_suffix(".tmp")
    while True:
        have = dest.stat().st_size if dest.exists() else 0
        if have > expected:
            dest.unlink()
            have = 0
        if have == expected:
            return
        if attempt.exists():
            attempt.unlink()
        command = [
            str(CURL),
            "-L",
            "--fail",
            "--connect-timeout",
            "20",
            "--speed-limit",
            "2000",
            "--speed-time",
            "30",
            "-r",
            f"{start + have}-{end}",
            "-o",
            str(attempt),
            "-s",
            URL,
        ]
        subprocess.call(command)
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


def main() -> None:
    if PARTS.exists():
        shutil.rmtree(PARTS)
    PARTS.mkdir(parents=True, exist_ok=True)
    ranges = _ranges(START, END, PIECES)
    expected = END - START + 1
    print(f"repairing {expected} bytes in {len(ranges)} pieces", flush=True)
    stop = threading.Event()

    def beat() -> None:
        while not stop.wait(20):
            have = sum(path.stat().st_size for path in PARTS.iterdir() if path.is_file())
            print(f"repair {have / 1_048_576:.1f} MB of {expected / 1_048_576:.1f} MB", flush=True)

    threading.Thread(target=beat, daemon=True).start()
    with ThreadPoolExecutor(max_workers=PIECES) as pool:
        futures = [
            pool.submit(_fetch, start, end, PARTS / f"{index:02d}.part")
            for index, (start, end) in enumerate(ranges)
        ]
        for future in futures:
            future.result()
    stop.set()
    piece = PARTS / "piece.bin"
    with piece.open("wb") as handle:
        for index in range(len(ranges)):
            with (PARTS / f"{index:02d}.part").open("rb") as source:
                shutil.copyfileobj(source, handle, length=8 * 1024 * 1024)
    expected = END - START + 1
    if piece.stat().st_size != expected:
        raise SystemExit(f"piece is {piece.stat().st_size} bytes, expected {expected}.")
    with SHARD.open("r+b") as shard, piece.open("rb") as source:
        shard.seek(START)
        shutil.copyfileobj(source, shard, length=8 * 1024 * 1024)
    print("spliced", flush=True)


if __name__ == "__main__":
    main()
