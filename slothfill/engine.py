"""Map a page: saved answers, synonym rules, then one model call for the rest."""

from __future__ import annotations

from slothfill.cache import DomainCache, replay
from slothfill.fields import Field, Mapped
from slothfill.llm_map import mappings_from_model
from slothfill.rules import mappable, match_field


def map_fields(
    fields: list[Field],
    profile: dict,
    cache: DomainCache | None,
    url: str,
    chat=None,
) -> list[Mapped]:
    saved = cache.lookup(url, fields) if cache else {}
    mapped: list[Mapped] = []
    for field in fields:
        hit = replay(field, profile, saved[field.id]) if field.id in saved else None
        if hit is None:
            hit = match_field(field, profile)
        if hit is None:
            hit = Mapped(id=field.id, value="", confidence=0, source="none")
        mapped.append(hit)
    gaps = [field for field, item in zip(fields, mapped) if item.source == "none" and mappable(field)]
    skipped: list[str] = []
    if gaps and chat is not None:
        try:
            updates = {item.id: item for item in mappings_from_model(gaps, profile, chat(gaps, profile))}
            skipped = [field.id for field in gaps if field.id not in updates]
        except Exception:
            updates = {}
        if updates:
            mapped = [updates.get(item.id, item) if item.source == "none" else item for item in mapped]
    if cache:
        cache.store(url, fields, mapped, skipped)
    return mapped
