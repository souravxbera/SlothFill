"""Train the field-mapper LoRA on Tinker, then score it against base Qwen.

The base model is Qwen/Qwen3.5-4B, the 64K variant. The 256K id costs more
and is not used. Prices checked on 24 Oct 2026:

- train $0.737 per million tokens
- sample $1.005 per million output tokens
- prefill $0.33 per million prompt tokens

This script refuses to start a run whose estimate is above $2, and it never
starts one without TINKER_API_KEY. A dry run prints the estimate and stops.

    .\\.venv\\Scripts\\python.exe scripts\\train_mapper.py
    .\\.venv\\Scripts\\python.exe scripts\\train_mapper.py --train
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slothfill.mapper_set import SYSTEM, build_splits  # noqa: E402

BASE_MODEL = "Qwen/Qwen3.5-4B"
RANK = 16
LEARNING_RATE = 2e-4
BATCH_SIZE = 32
EPOCHS = 1
TRAIN_USD_PER_MILLION = 0.737
SAMPLE_USD_PER_MILLION = 1.005
PREFILL_USD_PER_MILLION = 0.33
SPEND_CAP_USD = 2.0
CHARS_PER_TOKEN = 3.5


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


def _tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def estimate(train: list, heldout: list) -> dict:
    train_tokens = sum(_tokens(SYSTEM) + _tokens(row.user_text()) + _tokens(row.answer()) for row in train)
    train_tokens *= EPOCHS
    prompt_tokens = sum(_tokens(SYSTEM) + _tokens(row.user_text()) for row in heldout)
    # Base Qwen and the LoRA each see the held-out prompts. Answers are short JSON.
    sample_tokens = len(heldout) * 2 * 40
    prefill_tokens = prompt_tokens * 2
    train_usd = train_tokens / 1_000_000 * TRAIN_USD_PER_MILLION
    sample_usd = sample_tokens / 1_000_000 * SAMPLE_USD_PER_MILLION
    prefill_usd = prefill_tokens / 1_000_000 * PREFILL_USD_PER_MILLION
    return {
        "model": BASE_MODEL,
        "rank": RANK,
        "train_rows": len(train),
        "heldout_rows": len(heldout),
        "epochs": EPOCHS,
        "estimated_train_tokens": train_tokens,
        "estimated_train_usd": round(train_usd, 3),
        "estimated_eval_usd": round(sample_usd + prefill_usd, 3),
        "estimated_total_usd": round(train_usd + sample_usd + prefill_usd, 3),
        "cap_usd": SPEND_CAP_USD,
    }


def _check_budget(report: dict) -> None:
    if report["estimated_total_usd"] > SPEND_CAP_USD:
        raise SystemExit(
            f"Estimate ${report['estimated_total_usd']} is above the ${SPEND_CAP_USD} cap for this run. Not starting."
        )


def _fit_check(train: list) -> None:
    from tinker_cookbook.renderers import TrainOnWhat, get_renderer
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tokenizer = get_tokenizer(BASE_MODEL)
    renderer = get_renderer("qwen3_5_disable_thinking", tokenizer)
    longest = 0
    longest_label = ""
    for row in train:
        _model_input, weights = renderer.build_supervised_example(
            row.messages(), train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE
        )
        length = len(weights)
        weight_sum = float(sum(weights))
        if length > longest:
            longest = length
            longest_label = row.label
        if length > 512 or weight_sum <= 0:
            raise SystemExit(f"Bad example '{row.label}': {length} tokens, weight {weight_sum}. Not starting.")
    print(f"longest example {longest} tokens ({longest_label})", flush=True)


async def _train(train: list, report: dict) -> None:
    import numpy as np
    import random
    import tinker
    from tinker_cookbook.renderers import TrainOnWhat, get_renderer
    from tinker_cookbook.supervised.data import conversation_to_datum

    _check_budget(report)
    _fit_check(train)
    service = tinker.ServiceClient(display_name="slothfill-mapper")
    client = await service.create_lora_training_client_async(base_model=BASE_MODEL, rank=RANK)
    tokenizer = client.get_tokenizer()
    renderer = get_renderer("qwen3_5_disable_thinking", tokenizer)
    data = [
        conversation_to_datum(
            row.messages(),
            renderer,
            max_length=512,
            train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
        )
        for row in train
    ]
    random.Random(0).shuffle(data)
    print(f"shuffled {len(data)} examples with seed 0", flush=True)
    steps = (len(data) + BATCH_SIZE - 1) // BATCH_SIZE * EPOCHS
    losses = []
    step = 0
    for _epoch in range(EPOCHS):
        for start in range(0, len(data), BATCH_SIZE):
            batch = data[start : start + BATCH_SIZE]
            lr = LEARNING_RATE * (1 - step / max(steps, 1))
            forward = await client.forward_backward_async(batch, "cross_entropy")
            optim = await client.optim_step_async(tinker.AdamParams(learning_rate=max(lr, 1e-6)))
            result = await forward.result_async()
            await optim.result_async()
            logprobs = np.concatenate([out["logprobs"].tolist() for out in result.loss_fn_outputs])
            weights = np.concatenate([item.loss_fn_inputs["weights"].tolist() for item in batch])
            loss = float(-np.dot(logprobs, weights) / max(weights.sum(), 1))
            losses.append({"step": step, "loss": round(loss, 4), "learning_rate": lr})
            print(f"step {step:02d}: loss {loss:.4f} lr {lr:.6f}", flush=True)
            partial = ROOT / "data" / "tinker_train.json"
            partial.parent.mkdir(parents=True, exist_ok=True)
            partial.write_text(
                json.dumps({"estimate": report, "losses": losses}, indent=2),
                encoding="utf-8",
            )
            step += 1
    save_future = await client.save_weights_for_sampler_async(name="slothfill-mapper")
    checkpoint = await save_future.result_async()
    path = checkpoint.path
    out = ROOT / "data" / "tinker_train.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"checkpoint": path, "estimate": report, "losses": losses}, indent=2),
        encoding="utf-8",
    )
    print(f"checkpoint {path}")
    print(f"wrote {out}")


def main() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Start the paid LoRA run")
    args = parser.parse_args()
    train, heldout = build_splits()
    report = estimate(train, heldout)
    print(json.dumps(report, indent=2))
    if not args.train:
        print("Dry run only. Pass --train after TINKER_API_KEY is set.")
        return
    _check_budget(report)
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not set. Put it in .env or the environment. Not starting.")
    asyncio.run(_train(train, report))


if __name__ == "__main__":
    main()
