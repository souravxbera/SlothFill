"""Form fields as the extension and the mapper both see them."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Field:
    id: str
    label: str = ""
    name: str = ""
    placeholder: str = ""
    type: str = "text"
    options: list[str] = field(default_factory=list)
    tag: str = "input"

    @classmethod
    def from_dict(cls, raw: dict) -> "Field":
        options = raw.get("options") or []
        return cls(
            id=str(raw.get("id") or ""),
            label=str(raw.get("label") or ""),
            name=str(raw.get("name") or ""),
            placeholder=str(raw.get("placeholder") or ""),
            type=str(raw.get("type") or "text"),
            options=[str(item) for item in options],
            tag=str(raw.get("tag") or "input"),
        )


@dataclass
class Mapped:
    id: str
    value: str
    confidence: float
    source: str
    profile_key: str = ""
    transform: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "profile_key": self.profile_key,
        }
