"""One local mapper call for the fields synonym rules could not fill."""

from __future__ import annotations

import json
import re

from slothfill.extract import _json_object, complete
from slothfill.fields import Field, Mapped
from slothfill.rules import apply_transform, field_text

ALLOWED = {
    "name",
    "father_name",
    "dob",
    "gender",
    "phone",
    "email",
    "pan",
    "aadhaar_masked",
    "category",
    "nationality",
    "address.line1",
    "address.line2",
    "address.city",
    "address.state",
    "address.pincode",
    "address.country",
    "education.10.board",
    "education.10.year",
    "education.10.marks",
    "education.10.institution",
    "education.12.board",
    "education.12.year",
    "education.12.marks",
    "education.12.institution",
}
TRANSFORMS = {"text", "first_name", "last_name", "dob_iso", "dob_dmy_slash", "dob_dmy_dash", "option"}
KEY_ALIASES = {
    "first_name": ("name", "first_name"),
    "given_name": ("name", "first_name"),
    "last_name": ("name", "last_name"),
    "surname": ("name", "last_name"),
    "pincode": ("address.pincode", "text"),
    "pin": ("address.pincode", "text"),
    "aadhaar": ("aadhaar_masked", "text"),
    "aadhar": ("aadhaar_masked", "text"),
}

SYSTEM = (
    "You map form fields onto profile keys. Reply with JSON only. "
    "Omit a field when none of the keys fit. Do not guess, and do not copy a value into profile_key."
)

# The profile has no value for these, so a guessed key would fill the wrong box.
OMIT_PHRASES = (
    "passport",
    "visa",
    "course",
    "programme",
    "program",
    "portfolio",
    "linkedin",
    "github",
    "mother tongue",
    "religion",
    "blood group",
    "marital",
    "salary",
    "website",
)

# An ID or category key only fits a field that actually asks for it.
KEY_NEEDS = {
    "pan": ("pan", "permanent account"),
    "aadhaar_masked": ("aadhaar", "aadhar"),
    "category": ("category", "caste", "reservation"),
}


def ask_mapper(fields: list[Field], profile: dict) -> str:
    described = [
        {
            "id": field.id,
            "label": field.label,
            "name": field.name,
            "placeholder": field.placeholder,
            "type": field.type,
            "options": field.options,
        }
        for field in fields
    ]
    user = (
        "Allowed profile_key values:\n"
        + "\n".join(f"- {key}" for key in sorted(ALLOWED))
        + "\nAllowed transform values: text, first_name, last_name, dob_iso, dob_dmy_slash, dob_dmy_dash, option.\n"
        + "Pair profile_key name with first_name or last_name when the field wants only part of the name.\n"
        + "Use transform option for gender, category, and state when the field lists options.\n"
        + "Use dob_iso when the input type is date, and dob_dmy_slash for DD/MM/YYYY.\n"
        + "Omit passport, visa, course, programme, portfolio, website, mother tongue, religion, blood group, marital status, and salary.\n"
        + "Use pan only for a PAN field, and category only for caste or reservation. Leave the field out otherwise.\n"
        + "Profile:\n"
        + json.dumps(profile, ensure_ascii=False)
        + "\nFields:\n"
        + json.dumps(described, ensure_ascii=False)
        + '\nReturn {"fields":[{"id":"...","profile_key":"...","transform":"..."}]}'
    )
    return complete(SYSTEM, user)


def _refused(field: Field, key: str) -> bool:
    padded = f" {field_text(field)} "
    if any(f" {phrase} " in padded for phrase in OMIT_PHRASES):
        return True
    needed = KEY_NEEDS.get(key)
    return bool(needed) and not any(f" {phrase} " in padded for phrase in needed)


def _choice(field: Field, raw_key: str, raw_transform: str) -> tuple[str, str] | None:
    key = raw_key.strip()
    transform = raw_transform.strip() or "text"
    if key in KEY_ALIASES and key not in ALLOWED:
        key, alias_transform = KEY_ALIASES[key]
        if transform == "text":
            transform = alias_transform
    if key not in ALLOWED:
        return None
    if key == "dob":
        blob = f"{field.placeholder} {field.label}"
        if field.type == "date":
            transform = "dob_iso"
        elif re.search(r"dd\s*-\s*mm", blob, re.I):
            transform = "dob_dmy_dash"
        elif transform not in {"dob_iso", "dob_dmy_slash", "dob_dmy_dash"}:
            transform = "dob_dmy_slash"
    elif key in {"gender", "category", "address.state"} and field.options:
        transform = "option"
    elif transform not in TRANSFORMS or transform in {"dob_iso", "dob_dmy_slash", "dob_dmy_dash"}:
        transform = "text"
    return key, transform


def mappings_from_model(fields: list[Field], profile: dict, raw: str) -> list[Mapped]:
    parsed = _json_object(raw)
    by_id = {field.id: field for field in fields}
    mapped: list[Mapped] = []
    seen: set[str] = set()
    for item in parsed.get("fields") or []:
        if not isinstance(item, dict):
            continue
        field_id = str(item.get("id") or "")
        field = by_id.get(field_id)
        if field is None or field_id in seen:
            continue
        choice = _choice(field, str(item.get("profile_key") or ""), str(item.get("transform") or ""))
        if choice is None:
            continue
        key, transform = choice
        if _refused(field, key):
            continue
        value = apply_transform(profile, key, transform, field)
        if not value:
            continue
        seen.add(field_id)
        mapped.append(
            Mapped(
                id=field_id,
                value=value,
                confidence=0.86,
                source="llm",
                profile_key=key,
                transform=transform,
            )
        )
    return mapped
