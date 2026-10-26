# SlothFill

SlothFill fills college, KYC, and job forms from a profile that stays on your computer. You set it up once from PDFs. After that, one click fills a form. The form is never submitted.

Two open-weight models run locally through [Ollama](https://ollama.com). Gemma 4 reads the documents. A fine-tuned Qwen3.5-4B picks which profile field belongs in each box the rules do not already know.

The sample person, Sana Qureshi, is fictional. `SLTHF0000A` and `XXXX-XXXX-0000` are not real identity numbers.

## How it works

```
PDFs  ->  Gemma 4  ->  profile you review  ->  data/profile.json
                                                     |
page  ->  extension or demo button  ->  http://127.0.0.1:8787/map
                                                     |
                              rules, then memory, then the fine-tuned mapper
                                                     |
                              values written into the fields, form left unsent
```

Everything in that path stays on the machine. The server binds to `127.0.0.1:8787` only. The public pages are static demos. They do not receive IDs, marksheets, resumes, or the profile.

### Setup

On **Setup**, you upload PDFs, point at a folder on this computer, or press **Read the sample PDF**. A folder lists the PDFs sitting in it, and you uncheck any file that should stay out. The page then shows which file is being read, and how many seconds that file has taken, so a long CPU read does not look frozen. Subfolders are left alone. Up to 20 PDFs are read in one pass.

- A PDF with a text layer is read by `pypdf`. Gemma turns that text into profile JSON.
- A scan, with no text layer, is rendered to page images and read with Gemma vision.
- You check the result on the review page, then save it.
- Aadhaar is stored masked, last four digits visible.
- The saved file is `data/profile.json`. Git ignores it. Until you save one, the demo uses `fixtures/sana_qureshi.json`.

### Filling a form

The demo pages and the extension send the same thing: each field's label, name, placeholder, type, and options. They do not send the values already typed in the page. The server answers with values from the profile. The page writes those values and highlights the field. Green means confidence of 0.9 or higher. Yellow means look once. Submit is blocked. The status line says the form was not sent.

For each field, in order:

1. **Memory.** If this exact form was filled before, the saved profile key is used again. The value comes from the profile as it is now, so a corrected name shows up on the next visit. The memory file is `data/domain_cache.json`, also gitignored.
2. **Synonym rules.** Known labels map straight to a profile key. "Father's / Guardian name" is one example. Dates follow the input: ISO for `type=date`, otherwise `DD/MM/YYYY` or `DD-MM-YYYY`. Gender, category, and state match the options on the page. Password, OTP, captcha, username, mother's name, and similar fields are skipped.
3. **One model call for the rest.** Fields still empty go to `slothfill-mapper` in a single JSON request. The model returns a profile key, such as `phone`, and a transform, such as `text` or `first_name`. It does not return the value. Code looks the value up. A field with no fitting key is left blank. Passport, preferred course, and portfolio stay empty because they are not in the profile. WhatsApp is not in the rules, so the model maps it to the phone number.

A second visit to the same form replays memory and does not call the model again.

Ordinary HTML fields are filled, including React-style inputs, by setting the value through the native setter. A Google Form is read from the question heading, including choices drawn as buttons rather than real radio inputs. A choice such as 1st year stays empty when the profile only has a passing year. Shadow DOM and cross-origin iframes are outside what this version fills.

### The two models

| Job | Model | Where it runs |
| --- | --- | --- |
| Read PDFs into the profile | `gemma4:e2b-it-qat` | Ollama on this computer |
| Map leftover form fields | `slothfill-mapper` | Ollama on this computer |

`slothfill-mapper` is a Q4 GGUF of a LoRA trained with [Tinker](https://tinker.thinkingmachines.ai) on `Qwen/Qwen3.5-4B` (rank 16, one epoch). The LoRA was merged into the base weights and loaded with `ollama create`. Document reading stays on Gemma. The mapper runs at temperature 0 so the chosen key stays stable.

Held-out check, 165 rows, temperature 0, exact match of profile key and transform. JSON was valid for every row.

| Model | Exact match |
| --- | --- |
| Fine-tuned Qwen (Tinker LoRA) | 86.1% (142/165) |
| Base Qwen3.5-4B | 58.2% (96/165) |
| Gemma 4 E2B, local CPU | 51.5% (85/165) |

The GGUF is local and is not in this repo. Without `slothfill-mapper`, rules and memory still fill the fields they know. The leftover call then fails closed and those boxes stay empty.

## Run it

Install [Ollama](https://ollama.com), then:

```powershell
ollama pull gemma4:e2b-it-qat
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m slothfill
```

Open http://127.0.0.1:8787/demo/.

- **Setup** reads a PDF and opens the review page.
- **Admission**, **KYC**, and **Job** are the three demo forms. Press **Fill from local profile**.

`slothfill-mapper` has to exist in Ollama for leftover fields such as WhatsApp. Building that GGUF needs the trained adapter and the Qwen3.5-4B base weights. The training script is `scripts/train_mapper.py`. It reads `TINKER_API_KEY` from a gitignored `.env`.

## Extension

The extension fills a normal page the same way the demo button does.

1. Open `chrome://extensions` (Edge: `edge://extensions`).
2. Turn on Developer mode.
3. Load unpacked and choose the `extension` folder.
4. Keep the local server running. On a page, open SlothFill and press **Fill this page**.

It is Manifest V3. The only host it may call is `http://127.0.0.1:8787`. The content script is injected when you click Fill.

## Tests

```powershell
pytest
```

GitHub Actions runs the same tests on the rules path. That job does not start Ollama. A published release zips the `extension` folder.
