"""Score base Qwen and the LoRA on the held-out labels, both sampled on Tinker.

Temperature is 0 and each row gets one sample, so the accuracy number is the
model's single best guess. Gemma is scored afterwards on this computer, with
the same prompt and temperature 0. That latency is local CPU time and is
stored separately from the Tinker sample.

    .\\.venv\\Scripts\\python.exe scripts\\eval_mapper.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slothfill.extract import ParseError, _json_object  # noqa: E402
from slothfill.mapper_set import SYSTEM, build_splits  # noqa: E402

BASE_MODEL = "Qwen/Qwen3.5-4B"
GEMMA_MODEL = "gemma4:e2b-it-qat"


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


def _choice(text: str) -> tuple[str, str] | None:
    try:
        parsed = _json_object(text)
    except ParseError:
        return None
    if not isinstance(parsed, dict):
        return None
    return str(parsed.get("profile_key") if parsed.get("profile_key") is not None else ""), str(
        parsed.get("transform") or ""
    )


def _summarize(rows: list[dict], field: str) -> dict:
    valid = [row for row in rows if row[field] is not None]
    exact = [row for row in valid if row[field]["exact"]]
    return {
        "n": len(rows),
        "json_valid": round(len(valid) / len(rows), 4) if rows else 0,
        "exact": round(len(exact) / len(rows), 4) if rows else 0,
    }


async def _sample_one(client, renderer, params, row) -> str:
    prompt = renderer.build_generation_prompt(row.messages()[:-1])
    result = await client.sample_async(prompt=prompt, num_samples=1, sampling_params=params)
    response, _ok = renderer.parse_response(result.sequences[0].tokens)
    from tinker_cookbook.renderers import get_text_content

    return get_text_content(response)


async def _sample_split(client, renderer, params, rows: list, name: str) -> list[str]:
    semaphore = asyncio.Semaphore(6)

    async def wrapped(index: int, row) -> str:
        async with semaphore:
            try:
                text = await _sample_one(client, renderer, params, row)
            except Exception as exc:
                text = ""
                print(f"{name} {index} failed: {type(exc).__name__}", flush=True)
            if index % 15 == 0:
                print(f"{name} {index}/{len(rows)}", flush=True)
            return text

    return list(await asyncio.gather(*(wrapped(index, row) for index, row in enumerate(rows))))


def _gemma_one(row) -> tuple[str, float]:
    payload = {
        "model": GEMMA_MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": row.user_text()},
        ],
        "options": {"temperature": 0, "top_p": 0.95, "top_k": 64},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode("utf-8"))
    elapsed = time.perf_counter() - started
    message = body.get("message") or {}
    return str(message.get("content") or ""), elapsed


def _record(row, base_text: str, lora_text: str) -> dict:
    expected = (row.profile_key, row.transform)
    base_choice = _choice(base_text)
    lora_choice = _choice(lora_text)
    return {
        "label": row.label,
        "expected_key": row.profile_key,
        "expected_transform": row.transform,
        "base_text": base_text[:240],
        "lora_text": lora_text[:240],
        "base": None
        if base_choice is None
        else {"key": base_choice[0], "transform": base_choice[1], "exact": base_choice == expected},
        "lora": None
        if lora_choice is None
        else {"key": lora_choice[0], "transform": lora_choice[1], "exact": lora_choice == expected},
    }


async def _tinker_eval(heldout: list) -> list[dict]:
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    checkpoint = json.loads((ROOT / "data" / "tinker_train.json").read_text(encoding="utf-8"))["checkpoint"]
    service = tinker.ServiceClient(display_name="slothfill-mapper-eval")
    tokenizer = get_tokenizer(BASE_MODEL)
    renderer = get_renderer("qwen3_5_disable_thinking", tokenizer)
    params = tinker.SamplingParams(max_tokens=80, temperature=0, seed=0, stop=renderer.get_stop_sequences())
    base_client = await service.create_sampling_client_async(base_model=BASE_MODEL)
    lora_client = await service.create_sampling_client_async(model_path=checkpoint)
    print(f"checkpoint {checkpoint}", flush=True)
    base_texts = await _sample_split(base_client, renderer, params, heldout, "base")
    lora_texts = await _sample_split(lora_client, renderer, params, heldout, "lora")
    return [_record(row, base, lora) for row, base, lora in zip(heldout, base_texts, lora_texts)]


def _add_gemma(rows: list[dict], heldout: list) -> list[float]:
    times: list[float] = []
    for index, (record, row) in enumerate(zip(rows, heldout)):
        try:
            text, elapsed = _gemma_one(row)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            text, elapsed = "", 0
            print(f"gemma {index} failed", flush=True)
        choice = _choice(text)
        expected = (row.profile_key, row.transform)
        record["gemma"] = (
            None
            if choice is None
            else {"key": choice[0], "transform": choice[1], "exact": choice == expected, "seconds": round(elapsed, 2)}
        )
        times.append(elapsed)
        if index % 15 == 0:
            print(f"gemma {index}/{len(heldout)} {elapsed:.1f}s", flush=True)
    return times


def main() -> None:
    _load_dotenv()
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not set.")
    _train, heldout = build_splits()
    rows = asyncio.run(_tinker_eval(heldout))
    report = {
        "temperature": 0,
        "heldout": len(heldout),
        "base_qwen": _summarize(rows, "base"),
        "lora": _summarize(rows, "lora"),
    }
    out = ROOT / "data" / "tinker_eval.json"
    out.write_text(json.dumps({"report": report, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    times = _add_gemma(rows, heldout)
    report["gemma_local"] = _summarize(rows, "gemma")
    scored = [item for item in times if item > 0]
    report["gemma_local"]["median_seconds"] = round(sorted(scored)[len(scored) // 2], 2) if scored else None
    out.write_text(json.dumps({"report": report, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
