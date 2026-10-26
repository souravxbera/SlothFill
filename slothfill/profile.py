"""Load the private profile and read a value by key."""

from __future__ import annotations

import json
from pathlib import Path


def load_profile(path: Path, fixture: Path) -> tuple[dict, str]:
    """Return the profile and whether it came from the local file or the fixture."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), "local"
    return json.loads(fixture.read_text(encoding="utf-8")), "fixture"


def save_profile(path: Path, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def resolve(profile: dict, key: str) -> str:
    if key.startswith("education."):
        _, level, field_name = key.split(".", 2)
        for row in profile.get("education") or []:
            if str(row.get("level")) == level:
                value = row.get(field_name, "")
                return "" if value is None else str(value)
        return ""
    current = profile
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return ""
        current = current[part]
    if current is None or isinstance(current, (dict, list)):
        return ""
    return str(current)
