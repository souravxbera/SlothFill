# SlothFill — agent tracker

Working notes for this repo. Read this before changing anything. Building started 23 October 2026, night IST. Follow the approved order. Explain a plan change and wait for permission before taking it.

Goal: win the Hacktoberfest Week 3 overall prize or any category prize, by solving a real problem (repetitive Indian college, KYC, and job forms).

If a change to this plan looks necessary, explain it and wait for permission. Then follow whichever version was agreed.

## How to work

1. Confirm the ask, then do only that. If a step is ambiguous, ask before inventing scope.
2. The user said to start on 23 October 2026. This file is the agent session for the DEV post.
3. Ship a working project and a DEV post before the deadline. Writing quality is the heaviest judging criterion, so the post is part of the build.
4. Documents and `profile.json` stay on the machine. The local server binds to `127.0.0.1` only. The public site never receives IDs, marksheets, resumes, or the profile.
5. The repo and the demo use synthetic documents only. Real Aadhaar, PAN, marksheets, and resumes stay out of git. `profile.json` is gitignored. Aadhaar is stored masked (last 4 visible) unless the user reveals it locally.
6. The extension fills and highlights. It never auto-submits.
7. Use each partner technology for real. List a prize category only after that use exists.
8. Credit any non-trivial borrowed code in the README and the DEV post.
9. After the deadline, any further commit must be called out in the README.
10. Update this file when a decision lands.
11. After every step, append the useful output to **Results for the DEV post** below. Record what a person saw, the numbers, what broke, and what we decided. Leave out secrets, including the Tinker key. These notes are the raw material for the article. Do not publish the post until the entry is real. Writing quality is weighted most heavily: a working project with a thin write-up will not win. The other criteria are relevance to the prompt and theme, creativity, technical execution, and real use of each partner technology we claim.

## People and accounts

- DEV username: `souravxbera`. Solo entry unless the user adds teammates.
- Repo: https://github.com/souravxbera/SlothFill. Judges need the public repo. This file is the agent-session record for the DEV post.
- Tinker: $10 of credits, already claimed.

## Deadline

- Challenge window: 19–25 October 2026. New project, started and finished inside the window. This repo is that project.
- Submissions close **25 October 2026, 11:59 PM PDT** (about **26 October 2026, 12:30 PM IST**).
- Publish the DEV post on **25 October, evening IST**, with hours to spare. The post is the entry. Tags: `#devchallenge` and `#hf26challenge`.
- English. Winners the week of 26 October. A submission can win only one prize, and is judged for Overall plus every category named in the post.

Challenge page: https://dev.to/challenges/hacktoberfest-week3-2026-10-19
Partner credits: https://hacktoberfest.com/my/promos

## What we are building

**SlothFill** is a local-first, open-weight form filler.

- One-time setup reads PDFs on-device with Gemma 4 and writes a private profile the user reviews once.
- A Chrome/Edge Manifest V3 extension then fills a form in one click.
- Mapping order: synonym rules, then a per-domain cache, then one structured-JSON LLM call for the remaining fields of that form.
- Gemma 4 is the document reader. The default mapper is the local Q4 of the Tinker LoRA, `slothfill-mapper`. It beat Gemma on the held-out set and loaded in Ollama.
- Open matters because ID documents never go to a closed API, inference costs nothing ongoing, and the mapper model can be swapped.

Machine: CPU, 16 GB RAM, no GPU and no VRAM. Python. Ollama for local models. The folder `SlothFill` is the project. Do not create a nested project folder.

## Locked technical choices

- User-facing upload is PDF only. A text layer goes through `pypdf`, then Gemma writes the profile JSON. A scanned PDF with no text is rendered to page images inside the pipeline and sent to Gemma vision. RapidOCR stays out unless a sample scanned PDF fails vision.
- The promised fill targets are the three demo forms and ordinary HTML fields, including React-style inputs via the native value setter. The post shows those forms working. Shadow DOM and cross-origin iframes are outside the promise.
- Runtime: Ollama. Default model `gemma4:e2b-it-qat`. Leave `gemma4:e4b` unpulled unless E2B misreads one sample document. On 16 GB, E4B (about 7–10 GB) plus Chrome will swap. E2B is weaker on documents (OmniDocBench edit distance 0.290 vs 0.181), so that one sample is the check.
- Gemma sampling: temperature 1.0, top_p 0.95, top_k 64. For document pages, use vision token budget 1120 and put the image before the text. Turn thinking off for JSON extraction.
- Local API: FastAPI on `127.0.0.1`. `GET /profile`, `POST /map`. Backend switch: `gemma4:e2b-it-qat`, optional `gemma4:e4b`, optional `slothfill-mapper`.
- Extension: Chrome and Edge, Manifest V3. Sends label, name, placeholder, type, and options. Green = filled, yellow = uncertain.
- Demo forms: college admission, KYC-like, job application. Static files.
- Profile fields: name, father's name, DOB, gender, phone, email, address parts, PAN, Aadhaar (masked), education (board, year, marks). Mapper data includes Indian phrasing ("Father's/Guardian name", category GEN/OBC/SC/ST, DD/MM/YYYY).
- Tinker: LoRA SFT, rank 16, base model `Qwen/Qwen3.5-4B` at 64K context. Train about $0.74 / 1M tokens, sample about $1.01 / 1M. About 1,000 short train rows and 150 held-out rows whose phrasing differs from train. Hard stop: ask before a run that would push total spend past $6, so about $4 remains for eval and one retry.
- Eval: base Qwen3.5-4B vs the LoRA, both sampled on Tinker (accuracy, JSON validity, and Tinker cost). Gemma 4 E2B is a separate local column (accuracy and CPU latency). The table goes in the DEV post. The LoRA ships as the local mapper only if it beats Gemma on accuracy and the GGUF loads in Ollama.
- Colab GPU is a fallback, not the product. Documents never go to Colab. Tinker already does the training. Use Colab only if the 16 GB machine runs out of memory while merging the LoRA or converting GGUF. Colab cannot fix a llama.cpp gap on Qwen3.5's hybrid architecture. If conversion fails, publish the Tinker comparison and keep Gemma as the default mapper.
- GitHub Actions: tests, mapper eval on the rules path only (no Ollama in CI), zip the extension on release.
- Public site: the demo pages can be served as static files. Filling still happens on the computer running the local server.

## Prize map

| Target | What qualifies | SlothFill use |
| --- | --- | --- |
| Overall ($250) | Open-source AI, laziness theme, write-up weighted most | Set up once from PDFs, then one click. Indian college/KYC/job forms. |
| Gemma ($200) | Run, fine-tune, or serve Gemma | `gemma4:e2b-it-qat` reads the PDFs. |
| Tinker ($200) | Fine-tune and show a gain in performance, latency, or cost | LoRA on Qwen3.5-4B. Fair gain is held-out accuracy of the LoRA against base Qwen, both sampled on Tinker. |

Not entering: .tech, GitHub Copilot, ElevenLabs, Entire, Render, DigitalOcean, TabPFN, Arduino, Browserbase, Mastra, MongoDB, Tiger Data, Auth0, Sentry, SerpApi, Backboard, Ultramarine, Temporal.

## Approved build order

1. **Local setup.** Install Ollama, pull only `gemma4:e2b-it-qat`, create the venv.
2. **Fill path with no model.** Hand-written synthetic profile, three demo forms, rules mapper, extension. This demos the lazy payoff and keeps CI green.
3. **Gemma ingest.** Text PDFs, then scanned-PDF page render + vision. Review page to confirm the profile once.
4. **Mapper LLM.** Done. One JSON call per form for the fields rules missed. Domain cache after a successful fill. A second visit replays the cache. Passport, course, and portfolio stay empty.
5. **Tinker, timeboxed.** Train inside the $6 cap. Score base vs LoRA on Tinker. Then try merge + GGUF Q4 + Ollama, with Colab only if local RAM runs out. If conversion breaks, keep the Tinker numbers and ship Gemma.
6. **Ship the entry.** Public repo, DEV post with the eval table. This file is the agent session the post can point at.

Draft the post from step 2 onward. Sections: the hour people lose to these forms, the one-click payoff, why a closed API would mean uploading an ID, architecture, eval table, how to run it, prize categories.

## DEV post checklist

- What it is, who it saves time for, and the lazy payoff in the first screen.
- Why open-weight and local beat a closed form API.
- Eval table: base Qwen, Tinker LoRA, Gemma. State the winner and what shipped as the default mapper.
- Prize Categories section listing only Overall, Gemma, and Tinker.
- Public GitHub repo, install steps, and this file as the agent session. Author `souravxbera`.
- Synthetic data called out, so judges know the sample IDs are fake.

## Status

- Ollama 0.35.1 is installed. `gemma4:e2b-it-qat` (4.3 GB) and `qwen3.5:4b` (3.4 GB) are local. Do not pull E4B unless a sample PDF fails.
- Prize list is Overall, Gemma, and Tinker. .tech, GitHub Copilot, ElevenLabs, and Entire are not entered. This file is the agent session.
- Mapper step is in. Rules fill known labels. One Gemma call covers the rest of that form, then `data/domain_cache.json` remembers it. WhatsApp maps to the phone. Passport, preferred course, and portfolio stay empty.
- Tinker LoRA is trained. Base model `Qwen/Qwen3.5-4B` (64K), rank 16, one shuffled epoch. Held-out exact match at temperature 0, 165 rows: LoRA 86.1%, base Qwen 58.2%, Gemma 4 E2B 51.5% (local, median 3.9s). Checkpoint `tinker://dc5187e2-b9cb-5b09-be4e-ec338c6d4ae8:train:0/sampler_weights/slothfill-mapper`. Estimated spend about $0.40. The key stays in gitignored `.env`.
- The merged Q4 loaded. `ollama create slothfill-mapper` succeeded, and a three-field smoke returned phone, an empty key, and father_name. Details are in the post log.

## Results for the DEV post

Raw material. Lift the story from here. Do not paste this section into DEV as-is.

Judging, from the user on 24 October: Writing Quality is weighted most. Then relevance to the prompt and theme, creativity, technical execution, and, for a partner prize, real use of that partner. A great project with a thin write-up will not win.

### The lazy payoff, rules only

- Three demo forms fill from a synthetic profile. The extension and the page button never submit. Submit stays on the page and says the form was not sent.
- Admission filled 21 fields. Preferred course stays on “Select course” because a course is not in the profile.
- KYC filled the Female radio and wrote the date of birth as an ISO date.
- The job form splits the name into Sana and Qureshi.
- The sample person is fictional. PAN `SLTHF0000A`, Aadhaar `XXXX-XXXX-0000`, phone `9000000001`, email `sana.qureshi@example.com`. The post must say the sample IDs are fake.

### Reading a PDF on this PC

- A text PDF went through pypdf, then one Gemma call. The profile came back exact, including the masked Aadhaar. That call took about 46 seconds on CPU.
- The same page sent as an image got the name, father, date of birth, both classes, and the masked Aadhaar, and misread the PAN as `SLTHF00000A` (one extra 0). The review page exists because of that. The user checks the profile once before any form uses it.
- Nothing from that read left the machine.

### One Gemma call for the labels the rules miss

- On a live call, Gemma mapped WhatsApp number to the phone `9000000001` and “Son / Daughter of” to Imran Qureshi.
- It also tried to put the PAN, then the Aadhaar, into Passport number, and the category into Preferred course and Portfolio URL. The code drops those guesses. Passport, course, and portfolio stay empty.
- On the job form, the first fill marked WhatsApp for a look (confidence 0.86) and reported 9 filled fields. The second fill of the same form reused the saved mapping, marked WhatsApp sure, and reported 0 fields that needed a look.
- Admission still filled 21 fields after this change. Preferred course stayed on “Select course.”

### The Tinker LoRA

- Training set: 1,070 short rows. Held-out set: 165 rows whose labels are different phrases, not a reshuffle of the training labels. Example: “mobile number” is in training, “WhatsApp number” is held out. Answers are profile keys, never a person’s value.
- Base model `Qwen/Qwen3.5-4B`, the 64K id. The 256K id costs more to train and was not used. Rank 16. Prices checked 24 October 2026: train $0.737 per million tokens, sample $1.005 per million.
- The first training pass kept the rows grouped by field type, so the harder labels arrived after the learning rate had nearly reached zero. That checkpoint was kept and not used for the score.
- The second pass shuffled the rows (seed 0). Loss fell to about 0 by the end of the epoch. That is the scored checkpoint: `tinker://dc5187e2-b9cb-5b09-be4e-ec338c6d4ae8:train:0/sampler_weights/slothfill-mapper`.
- Held-out score, temperature 0, one guess each, 165 labels. All three models returned valid JSON.

| Model | Exact match | Where it ran |
| --- | --- | --- |
| Tinker LoRA | 86.1% (142/165) | Tinker |
| Base Qwen3.5-4B | 58.2% (96/165) | Tinker |
| Gemma 4 E2B | 51.5% (85/165) | This PC, median 3.9 seconds |

- The fair gain is LoRA against base Qwen, both sampled on Tinker. Gemma’s 3.9 seconds is local CPU time and stays in its own column.
- Two training passes plus the scoring were estimated at about $0.40 of the $10 credit. The hard stop is still $6.
- The 23 LoRA misses are odd paraphrases: “clan title,” “s o d o w o,” “inbox address,” “it department number.” It did not invent a passport value on the held-out travel-document row in the cases we inspected; several misses were an empty key or the wrong nearby key.

### The GGUF break, 24 October about 1:50 AM IST

- Ollama on this PC is 0.35.1. It already runs `qwen3.5:4b`. Since 0.34.1 it rejects a Modelfile `ADAPTER` line, so the LoRA cannot be attached beside the base model. It has to be merged, then loaded as one GGUF.
- The downloaded adapter is 146 MB and 498 tensors. A lot of them are the linear-attention layers (`in_proj_q`, `in_proj_k`, `in_proj_v`, `in_proj_z`), which a side-car LoRA file would drop or fail to convert. That is why the merge has to be into the full base weights.
- `Qwen/Qwen3.5-4B` weights are about 8.7 GB, two shards of about 5 GB. Memory was not the problem. The download was. Hugging Face sent them at about 50 KB/s, and the Python downloader timed out. A 45-second timed fetch got 2.2 MB. At that speed one 5 GB shard is about 28 hours, and the second shard is the same again, which misses the deadline.
- The merge retry was aborted after another timeout. Left on disk: the 146 MB adapter, and `data/qwen35_base/model.safetensors-00001-of-00002.safetensors.partial` at 2.2 MB.
- Decision waiting on the user: a faster connection, or Colab for the merge. Colab was reserved for running out of RAM. The block here is the link, and a finished GGUF would still have to come back down that link.
- Until a merged GGUF loads in Ollama, Gemma stays the mapper that fills forms. The Tinker numbers still stand.

### Adapter-only import, checked 24 October about 9:45 PM IST

- A plan to skip the 8.7 GB download: convert the LoRA with llama.cpp and load it in Ollama with `FROM qwen3.5:4b` plus `ADAPTER`.
- Step 1 is already done. `data/tinker_adapter` is PEFT format (`adapter_config.json`, `adapter_model.safetensors`, 146 MB, rank 16, all-linear). No Tinker rebuild needed.
- Step 2 is plausible and untested. On 30 September 2026 llama.cpp merged PR 28324, which fixes the Qwen3.5 LoRA crash in `convert_lora_to_gguf.py` while reordering linear-attention heads. That script needs the config and tokenizer, not the full weights.
- Step 3 fails on this PC. Ollama 0.35.1 returned `LoRA adapters are no longer supported` and exited before opening the adapter file. `ADAPTER` was removed in 0.34.1 on 15 September 2026 and is still rejected in later releases. `qwen3.5:4b` is already local (3.4 GB), so the base download in that plan was not the blocker.
- Decision: this route does not load the fine-tune in Ollama. A merged GGUF is still required for that, or Gemma stays the mapper.

### llama.cpp beside the Ollama blob, checked 24 October about 10:00 PM IST

- `ollama show --modelfile qwen3.5:4b` points at `C:\Users\sbera\.ollama\models\blobs\sha256-81fb60c7daa80fc1123380b98970b320ae233409f0f71a72ed7b9b0d62f40490`. The file is 3.16 GB, GGUF version 3, architecture `qwen35`, file type 15 (Q4_K_M). Hidden size 2560, 32 layers, 16 heads. That matches the cached `Qwen/Qwen3.5-4B` config. No new 8.7 GB download for the base.
- The config and tokenizer are already in the Hugging Face cache. `convert_lora_to_gguf.py` has a `--base` flag and its help says only the config is required. `base_model_name_or_path` in our adapter is null, so `--base` must be that local config, with the hub offline, or the script will try to download.
- This PC has no `llama-server`, no cmake, and no C++ compiler. A prebuilt Windows llama.cpp build, plus a converter newer than 30 September 2026, still has to be downloaded. That is much smaller than the base weights.
- The Ollama file is the vision build: 393 `v.*` tensors and an MTP block. The adapter has neither. Text can still run.
- Linear-attention layers in the blob are fused into `blk.N.attn_qkv` plus `ssm_*`. The adapter stores `in_proj_q`, `in_proj_k`, `in_proj_v`, and `in_proj_z` separately. The LoRA converter has no fuse flag. Full-attention layers and the MLP layers are separate on both sides, so those can attach. Load may reject the adapter or skip the linear layers.
- Word embeddings are tied, and the adapter also has an `unembed_tokens` pair. That pair may have no separate base tensor.
- Serving is llama-server on port 8080, OpenAI-style. The mapper today posts to Ollama `/api/chat`. Gemma stays on Ollama for documents. Both models resident at once is tight on 16 GB.
- A Q4 base plus an f16 LoRA will not reproduce the 86.1% Tinker score exactly. Switch the mapper only after a local held-out check. Conversion itself is still untested.

### Local download retry, 24 October about 10:15 PM IST

- Outsourcing and any extra API are off the table. The retry is a download from Hugging Face onto this PC, then a local shard merge.
- The weight files are shard 1 at 5,329,398,688 bytes and shard 2 at 3,990,429,408 bytes. The config and tokenizer were already cached.
- One connection still runs at about 70 KB/s. Eight connections together reach about 1 MB/s, and sixteen did not go faster. The CDN answering now is `aws-ap-southeast-1`, through a Kolkata CloudFront node, instead of the US node from the first attempt.
- `scripts/download_qwen_base.py` fetches both shards in eight resumable pieces, checks the sizes, then runs the merge against `data/qwen35_base` with the hub offline. S drive has about 91 GB free. At 1 MB/s the download is a few hours, then the merge still has to finish on 16 GB of RAM.
- The first run reached the end of shard 1 in about 2.5 hours, then stopped. Curl retried a stalled piece by writing the same bytes again onto the end of the file, so six of the eight pieces were larger than their range. Two pieces, 01 and 02, were the exact size and were kept. The retry-on-the-same-file behavior was removed, and the download was started again from the good pieces.
- The resume finished at about 2:06 AM IST on 25 October. Both shards match the published sizes. The link stalled for long stretches and then moved in bursts, sometimes above 10 MB/s. The merge ran on this PC and wrote `data/merged_mapper`: two shards of the same sizes as the base, 5,329,398,688 and 3,990,429,408 bytes. The new index file is 68,084 bytes, against 76,196 bytes for the base index, so the folder was rewritten rather than copied.

### GGUF loaded in Ollama, 26 October about 2:00 AM IST

- llama.cpp b11887 converted the merged folder with `--no-mtp`. The GGUF is architecture `qwen35`, 32 blocks, 426 tensors, text only. Forcing F16 overflowed a bfloat16 tensor, so the file that was quantized is BF16, 8.42 GB.
- The first quantize stopped on `blk.10.ffn_up.weight`: 464 NaNs. The same NaNs were already in base shard 1, in three MLP tensors (layer 10 up, layer 12 down and gate). Shard 2's SHA-256 matched the published checksum `cb544bd9…`. Shard 1 did not. The bad bytes were piece 02, kept from the first parallel download at the right length. That 635 MB piece was downloaded again and spliced back. A fresh range from Hugging Face then matched the file at every piece edge, and a NaN scan of shard 1 was clean. The full-file SHA-256 is still `9b3429a1…`, not the published `26a93f06…`.
- The repaired base was merged again, converted, and quantized to Q4_K_M in 72 seconds: 8,024 MiB down to 2,573 MiB. `ollama create slothfill-mapper` accepted the file.
- A cold map of three fields took 14.7 seconds, then about 5 seconds each. WhatsApp number returned `phone`. Passport number returned an empty key. Father's name returned `father_name`. The product prompt, all three fields in one JSON call, returned the same three answers in about 30 seconds.
- `MAPPER_MODEL` is now `slothfill-mapper`, called at temperature 0. Document reading stays on `gemma4:e2b-it-qat`.

### Folder read, 26 October about 2:50 AM IST

- Setup can take a folder path. The server lists PDFs in that folder only. Text files, subfolders, and symlinks stay out. The page shows a checklist before Gemma starts, capped at 20 files.
- While a file is being read, a label updates every second: `Reading 1 of 1 — id.pdf — 6s`, with a progress bar. A sample text PDF in a temp folder reached the review page. The saved profile was put back afterwards, so that sample did not replace the local profile.

### Google Forms, 26 October about 11:20 AM IST

- A Google Form filled 0 fields because the question lives on a heading (`aria-labelledby`) and the year choices are `role="radio"` buttons, not `<input type="radio">`. The extension now reads that heading and clicks those choices. A local copy of the IETE form filled the name and left 1st/2nd/3rd/4th empty, because the profile has a passing year, not a study year. The ordinary KYC form still fills. Reload the unpacked extension so Chrome picks up the new script.

### Render, 26 October about 11:51 AM IST

- A complete deploy on Render does not fit. The API is loopback-only, the profile and PDFs stay on the PC, and Gemma plus the Q4 mapper need more RAM than a cheap Render instance and are not installed there. The guide is `docs/render.md`. A static site of `site/` can be hosted. A public rules-only demo of the fictional profile would need a separate code change and must refuse uploads. Not built.
