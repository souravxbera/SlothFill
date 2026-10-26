"""Turn PDF bytes into a profile. Gemma runs on this computer through Ollama."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime

from slothfill.config import DOCUMENT_MODEL, MAPPER_MODEL
from slothfill.documents import extract_text, has_text_layer, render_pages

STRING_KEYS = (
    "name",
    "father_name",
    "dob",
    "gender",
    "phone",
    "email",
    "pan",
    "category",
    "nationality",
)
ADDRESS_KEYS = ("line1", "line2", "city", "state", "pincode", "country")
EDU_KEYS = ("board", "year", "marks", "institution")

PROMPT = """Extract identity and education facts from this document.
Reply with one JSON object and no other text.
Use these keys:
name, father_name, dob, gender, phone, email, pan, aadhaar, category, nationality,
address as an object with line1, line2, city, state, pincode, country,
education as a list of objects with level ("10" or "12"), board, year, marks, institution.
dob must be YYYY-MM-DD when you can tell the date.
Use an empty string for an unknown string and an empty list when there is no education.
Do not invent a value that is not in the document.
"""


class ModelError(Exception):
    pass


class ParseError(Exception):
    pass


def empty_profile() -> dict:
    return {
        "synthetic": False,
        "name": "",
        "father_name": "",
        "dob": "",
        "gender": "",
        "phone": "",
        "email": "",
        "address": {key: "" for key in ADDRESS_KEYS},
        "pan": "",
        "aadhaar_masked": "",
        "category": "",
        "nationality": "",
        "education": [],
    }


def _chat(
    system: str,
    content: str,
    images: list[bytes] | None = None,
    timeout: int = 300,
    model: str = DOCUMENT_MODEL,
    temperature: float = 1.0,
) -> str:
    message: dict = {"role": "user", "content": content}
    if images:
        import base64

        message["images"] = [base64.b64encode(image).decode("ascii") for image in images]
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            message,
        ],
        "options": {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 64,
            "image_token_budget": 1120,
        },
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise ModelError(detail or "Ollama rejected the request.") from exc
    except urllib.error.URLError as exc:
        raise ModelError("Ollama is not running on this computer.") from exc
    reply = body.get("message") or {}
    text = reply.get("content") or reply.get("thinking") or ""
    if not text:
        raise ModelError("The model returned an empty reply.")
    return text


def ask_gemma(content: str, images: list[bytes] | None = None) -> str:
    return _chat(
        "You extract facts from a personal document and reply with JSON only.",
        content,
        images,
        timeout=300,
    )


def complete(system: str, user: str) -> str:
    return _chat(system, user, None, timeout=120, model=MAPPER_MODEL, temperature=0.0)


def _json_object(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ParseError("Gemma did not return JSON.")
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(text[start : index + 1])
                except json.JSONDecodeError as exc:
                    raise ParseError("Gemma returned JSON that could not be read.") from exc
                if not isinstance(parsed, dict):
                    raise ParseError("Gemma returned JSON that was not an object.")
                return parsed
    raise ParseError("Gemma returned JSON that was cut off.")


def _clean(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _dob(value: str) -> str:
    text = value.strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def _gender(value: str) -> str:
    key = value.strip().lower()
    if key in {"f", "female", "woman"}:
        return "Female"
    if key in {"m", "male", "man"}:
        return "Male"
    if key in {"other", "non-binary", "nonbinary"}:
        return "Other"
    return value.strip()


def _category(value: str) -> str:
    key = re.sub(r"[^a-z]", "", value.lower())
    if key in {"gen", "general", "ur", "unreserved", "open"}:
        return "GEN"
    if key.startswith("obc"):
        return "OBC"
    if key == "sc":
        return "SC"
    if key == "st":
        return "ST"
    if key == "ews":
        return "EWS"
    return value.strip().upper() if len(value.strip()) <= 4 else value.strip()


def mask_aadhaar(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return ""
    return f"XXXX-XXXX-{digits[-4:]}"


def _level(value: str) -> str:
    text = value.lower()
    if any(token in text for token in ("12", "xii", "senior", "higher secondary", "hsc", "intermediate")):
        return "12"
    if any(token in text for token in ("10", "matric", "ssc", "secondary")):
        return "10"
    return ""


def profile_from_model(raw: str) -> dict:
    parsed = _json_object(raw)
    profile = empty_profile()
    for key in STRING_KEYS:
        profile[key] = _clean(parsed.get(key))
    profile["dob"] = _dob(profile["dob"])
    profile["gender"] = _gender(profile["gender"])
    profile["category"] = _category(profile["category"]) if profile["category"] else ""
    profile["pan"] = re.sub(r"[^A-Za-z0-9]", "", profile["pan"]).upper()
    profile["phone"] = re.sub(r"[^0-9+]", "", profile["phone"])
    address = parsed.get("address") if isinstance(parsed.get("address"), dict) else {}
    for key in ADDRESS_KEYS:
        profile["address"][key] = _clean(address.get(key))
    profile["aadhaar_masked"] = mask_aadhaar(_clean(parsed.get("aadhaar") or parsed.get("aadhaar_masked")))
    rows = []
    for item in parsed.get("education") or []:
        if not isinstance(item, dict):
            continue
        level = _level(_clean(item.get("level")))
        if not level:
            continue
        rows.append({key: _clean(item.get(key)) for key in ("board", "year", "marks", "institution")} | {"level": level})
    profile["education"] = rows
    return profile


def has_facts(profile: dict) -> bool:
    if any(profile.get(key) for key in STRING_KEYS):
        return True
    if any(profile["address"].values()):
        return True
    return bool(profile["education"]) or bool(profile["aadhaar_masked"])


def merge_profiles(base: dict, extra: dict) -> list[str]:
    """Fill blanks. Return keys where the new document disagreed."""
    conflicts = []
    for key in (*STRING_KEYS, "aadhaar_masked"):
        current = base.get(key) or ""
        incoming = extra.get(key) or ""
        if incoming and not current:
            base[key] = incoming
        elif incoming and current and incoming.casefold() != current.casefold():
            conflicts.append(key)
    for key in ADDRESS_KEYS:
        current = base["address"].get(key) or ""
        incoming = extra["address"].get(key) or ""
        if incoming and not current:
            base["address"][key] = incoming
        elif incoming and current and incoming.casefold() != current.casefold():
            conflicts.append(f"address.{key}")
    by_level = {row["level"]: row for row in base["education"]}
    for row in extra["education"]:
        existing = by_level.get(row["level"])
        if existing is None:
            base["education"].append(row)
            by_level[row["level"]] = row
            continue
        for key in EDU_KEYS:
            if row[key] and not existing[key]:
                existing[key] = row[key]
            elif row[key] and existing[key] and row[key].casefold() != existing[key].casefold():
                conflicts.append(f"education.{row['level']}.{key}")
    return conflicts


def read_documents(files: list[tuple[str, bytes]], chat=None, on_file=None) -> tuple[dict, dict]:
    speak = chat or ask_gemma
    merged = empty_profile()
    report = []
    total = len(files)
    for index, (name, data) in enumerate(files, start=1):
        if on_file is not None:
            on_file(index, total, name)
        text = extract_text(data)
        if has_text_layer(text):
            clipped = text[:12000]
            raw = speak(PROMPT + "\nDocument text:\n" + clipped, None)
            mode = "text"
        else:
            images = render_pages(data, limit=2)
            if not images:
                raise ParseError(f"{name} has no pages.")
            raw = speak(PROMPT + "\nThe document is the attached page image. Read the image before this text.", images)
            mode = "vision"
        extracted = profile_from_model(raw)
        conflicts = merge_profiles(merged, extracted)
        report.append({"file": name, "mode": mode, "conflicts": conflicts})
    if not has_facts(merged):
        raise ParseError("Gemma did not find any profile fields in the PDF.")
    return merged, {"files": report}
