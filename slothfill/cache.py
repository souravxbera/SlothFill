"""Remember how a page was filled, then replay it with no model call."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from slothfill.fields import Field, Mapped
from slothfill.rules import apply_transform, field_text


class DomainCache:
    def __init__(self, path: Path):
        self.path = path
        self.pages: dict = {}
        if path.exists():
            self.pages = json.loads(path.read_text(encoding="utf-8")).get("pages", {})

    def _key(self, url: str, fields: list[Field]) -> str:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        signature = "|".join(sorted(f"{item.id}:{field_text(item)}" for item in fields))
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
        return f"{origin}#{digest}"

    def lookup(self, url: str, fields: list[Field]) -> dict:
        if not url:
            return {}
        record = self.pages.get(self._key(url, fields))
        if not record:
            return {}
        return record.get("fields", {})

    def store(self, url: str, fields: list[Field], mapped: list[Mapped], skipped: list[str] | None = None) -> None:
        if not url:
            return
        remembered = {
            item.id: {"profile_key": item.profile_key, "transform": item.transform}
            for item in mapped
            if item.source in {"rule", "llm"} and item.confidence >= 0.8 and item.value and item.profile_key
        }
        for field_id in skipped or []:
            remembered.setdefault(field_id, {"skip": True})
        if not remembered:
            return
        self.pages[self._key(url, fields)] = {"url": url, "fields": remembered}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"pages": self.pages}, indent=2), encoding="utf-8")


def replay(field: Field, profile: dict, saved: dict) -> Mapped | None:
    if saved.get("skip"):
        return Mapped(id=field.id, value="", confidence=0, source="cache")
    key = saved.get("profile_key") or ""
    transform = saved.get("transform") or "text"
    if not key:
        return None
    value = apply_transform(profile, key, transform, field)
    if not value:
        return None
    return Mapped(
        id=field.id,
        value=value,
        confidence=0.97,
        source="cache",
        profile_key=key,
        transform=transform,
    )
