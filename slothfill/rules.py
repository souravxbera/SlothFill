"""Synonym rules for common college, KYC, and job fields."""

from __future__ import annotations

import re
from datetime import datetime

from slothfill.fields import Field, Mapped
from slothfill.profile import resolve

SKIP_TYPES = {"password", "hidden", "file", "submit", "button", "reset", "image", "checkbox"}

# Normalized phrase, profile key, transform. Longer phrases win.
RULES: list[tuple[str, str, str]] = [
    ("fathers guardians name", "father_name", "text"),
    ("fathers guardian name", "father_name", "text"),
    ("father guardian name", "father_name", "text"),
    ("guardian name", "father_name", "text"),
    ("fathers name", "father_name", "text"),
    ("father name", "father_name", "text"),
    ("date of birth", "dob", "dob"),
    ("birth date", "dob", "dob"),
    ("permanent account number", "pan", "text"),
    ("permanent account", "pan", "text"),
    ("pan number", "pan", "text"),
    ("year of passing", "education.year", "text"),
    ("passing year", "education.year", "text"),
    ("year of graduation", "education.year", "text"),
    ("mobile number", "phone", "text"),
    ("phone number", "phone", "text"),
    ("contact number", "phone", "text"),
    ("email address", "email", "text"),
    ("address line 2", "address.line2", "text"),
    ("address line 1", "address.line1", "text"),
    ("residential address", "address.line1", "text"),
    ("street address", "address.line1", "text"),
    ("postal code", "address.pincode", "text"),
    ("pin code", "address.pincode", "text"),
    ("zip code", "address.pincode", "text"),
    ("first name", "name", "first_name"),
    ("given name", "name", "first_name"),
    ("last name", "name", "last_name"),
    ("family name", "name", "last_name"),
    ("full name", "name", "text"),
    ("applicant name", "name", "text"),
    ("candidate name", "name", "text"),
    ("student name", "name", "text"),
    ("your name", "name", "text"),
    ("mobile no", "phone", "text"),
    ("e mail", "email", "text"),
    ("aadhaar number", "aadhaar_masked", "text"),
    ("aadhaar", "aadhaar_masked", "text"),
    ("aadhar", "aadhaar_masked", "text"),
    ("pincode", "address.pincode", "text"),
    ("nationality", "nationality", "text"),
    ("institution", "education.institution", "text"),
    ("percentage", "education.marks", "text"),
    ("college", "education.institution", "text"),
    ("school", "education.institution", "text"),
    ("surname", "name", "last_name"),
    ("gender", "gender", "option"),
    ("category", "category", "option"),
    ("address", "address.line1", "text"),
    ("country", "address.country", "text"),
    ("mobile", "phone", "text"),
    ("phone", "phone", "text"),
    ("email", "email", "text"),
    ("board", "education.board", "text"),
    ("marks", "education.marks", "text"),
    ("state", "address.state", "option"),
    ("city", "address.city", "text"),
    ("name", "name", "text"),
    ("pan", "pan", "text"),
    ("dob", "dob", "dob"),
    ("sex", "gender", "option"),
]

BLOCKS = (
    "password",
    "passcode",
    "otp",
    "captcha",
    "username",
    "user name",
    "csrf",
    "mother",
    "mothers",
    "middle name",
    "spouse",
    "spouses",
    "husband",
    "husbands",
    "wife",
    "wifes",
    "login",
)

GENDER_ALIASES = {
    "female": ["female", "f", "woman"],
    "male": ["male", "m", "man"],
    "other": ["other", "non binary"],
}
CATEGORY_ALIASES = {
    "gen": ["gen", "general", "ur", "unreserved", "open"],
    "general": ["gen", "general", "ur", "unreserved", "open"],
    "obc": ["obc", "obc ncl", "other backward class", "other backward"],
    "sc": ["sc", "scheduled caste"],
    "st": ["st", "scheduled tribe"],
    "ews": ["ews", "economically weaker"],
}

_SORTED_RULES = sorted(RULES, key=lambda item: len(item[0]), reverse=True)


def norm(value: str) -> str:
    text = value.lower().replace("'", "").replace("\u2019", "").replace("\u2018", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def field_text(field: Field) -> str:
    return norm(" ".join([field.label, field.name, field.placeholder, field.id]))


def _blocked(text: str) -> bool:
    padded = f" {text} "
    return any(f" {phrase} " in padded for phrase in BLOCKS)


def _education_level(text: str) -> str:
    if any(phrase in text for phrase in ("12th", "class 12", "senior secondary", "higher secondary", "intermediate", "hsc")):
        return "12"
    if any(phrase in text for phrase in ("10th", "class 10", "matric", "ssc")):
        return "10"
    if "secondary" in text:
        return "10"
    return "12"


def _dob_transform(field: Field) -> str:
    raw = f"{field.placeholder} {field.label}"
    if field.type == "date":
        return "dob_iso"
    if re.search(r"dd\s*-\s*mm", raw, re.I):
        return "dob_dmy_dash"
    return "dob_dmy_slash"


def _parse_dob(value: str) -> datetime | None:
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return None


def _format_dob(value: str, transform: str) -> str:
    parsed = _parse_dob(value)
    if parsed is None:
        return value
    if transform == "dob_iso":
        return parsed.strftime("%Y-%m-%d")
    if transform == "dob_dmy_dash":
        return parsed.strftime("%d-%m-%Y")
    return parsed.strftime("%d/%m/%Y")


def _alias_hit(alias: str, option_norm: str) -> bool:
    if len(alias) <= 3:
        return f" {alias} " in f" {option_norm} "
    return alias in option_norm or option_norm in alias


def match_option(profile_value: str, options: list[str], kind: str) -> str:
    usable = [option for option in options if option.strip() and not norm(option).startswith("select")]
    target = norm(profile_value)
    if not target:
        return ""
    for option in usable:
        if norm(option) == target:
            return option
    table = GENDER_ALIASES if kind == "gender" else CATEGORY_ALIASES if kind == "category" else {}
    for alias in table.get(target, []):
        for option in usable:
            if _alias_hit(alias, norm(option)):
                return option
    if kind == "text":
        for option in usable:
            option_norm = norm(option)
            if target in option_norm or option_norm in target:
                return option
    return ""


def apply_transform(profile: dict, key: str, transform: str, field: Field) -> str:
    if transform == "first_name":
        parts = resolve(profile, "name").split()
        return parts[0] if parts else ""
    if transform == "last_name":
        parts = resolve(profile, "name").split()
        return parts[-1] if len(parts) > 1 else ""
    raw = resolve(profile, key)
    if transform in {"dob_iso", "dob_dmy_slash", "dob_dmy_dash"}:
        return _format_dob(raw, transform)
    if transform == "option":
        kind = "gender" if key == "gender" else "category" if key == "category" else "text"
        if field.options:
            return match_option(raw, field.options, kind)
        return raw
    return raw


def mappable(field: Field) -> bool:
    """False for passwords, hidden controls, and labels we must not guess."""
    if not field.id or field.type.lower() in SKIP_TYPES:
        return False
    text = field_text(field)
    return bool(text) and not _blocked(text)


def match_field(field: Field, profile: dict) -> Mapped | None:
    if not field.id or field.type.lower() in SKIP_TYPES:
        return None
    text = field_text(field)
    if not text or _blocked(text):
        return None
    padded = f" {text} "
    found = None
    for phrase, key, transform in _SORTED_RULES:
        if f" {phrase} " in padded:
            found = (key, transform)
            break
    if found is None:
        return None
    key, transform = found
    if key.startswith("education."):
        key = f"education.{_education_level(text)}.{key.split('.', 1)[1]}"
    if transform == "dob":
        transform = _dob_transform(field)
    value = apply_transform(profile, key, transform, field)
    if not value:
        return None
    confidence = 0.92 if transform == "option" else 0.95
    return Mapped(
        id=field.id,
        value=value,
        confidence=confidence,
        source="rule",
        profile_key=key,
        transform=transform,
    )
