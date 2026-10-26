import json
from pathlib import Path

from slothfill.cache import DomainCache
from slothfill.engine import map_fields
from slothfill.fields import Field
from slothfill.llm_map import mappings_from_model
from slothfill.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE, _ = load_profile(ROOT / "data" / "missing.json", ROOT / "fixtures" / "sana_qureshi.json")


def test_model_json_uses_profile_values_and_drops_unknown_keys():
    raw = json.dumps(
        {
            "fields": [
                {"id": "whatsapp", "profile_key": "phone", "transform": "text"},
                {"id": "passport", "profile_key": "passport", "transform": "text"},
                {"id": "kin", "profile_key": "father_name", "value": "Invented Person"},
            ]
        }
    )
    fields = [
        Field(id="whatsapp", label="WhatsApp number"),
        Field(id="passport", label="Passport number"),
        Field(id="kin", label="Son / Daughter of"),
    ]
    mapped = {item.id: item for item in mappings_from_model(fields, PROFILE, raw)}
    assert mapped["whatsapp"].value == "9000000001"
    assert mapped["whatsapp"].confidence < 0.9
    assert "passport" not in mapped
    assert mapped["kin"].value == "Imran Qureshi"


def test_model_cannot_reuse_pan_or_category_for_unrelated_fields():
    raw = json.dumps(
        {
            "fields": [
                {"id": "passport", "profile_key": "pan", "transform": "text"},
                {"id": "course", "profile_key": "category", "transform": "option"},
                {"id": "whatsapp", "profile_key": "phone", "transform": "text"},
            ]
        }
    )
    fields = [
        Field(id="passport", label="Passport number"),
        Field(id="course", label="Preferred course", type="select", options=["B.A. Economics"]),
        Field(id="whatsapp", label="WhatsApp number"),
    ]
    mapped = {item.id: item for item in mappings_from_model(fields, PROFILE, raw)}
    assert "passport" not in mapped
    assert "course" not in mapped
    assert mapped["whatsapp"].value == "9000000001"


def test_unknown_fields_call_the_model_once_and_then_use_cache(tmp_path):
    calls = []

    def chat(pending, profile):
        calls.append([field.id for field in pending])
        return json.dumps({"fields": [{"id": "whatsapp", "profile_key": "phone", "transform": "text"}]})

    fields = [
        Field(id="full_name", label="Full name"),
        Field(id="whatsapp", label="WhatsApp number"),
        Field(id="passport", label="Passport number"),
    ]
    url = "http://127.0.0.1:8787/demo/job.html"
    cache = DomainCache(tmp_path / "cache.json")
    first = {item.id: item for item in map_fields(fields, PROFILE, cache, url, chat=chat)}
    second = {item.id: item for item in map_fields(fields, PROFILE, cache, url, chat=chat)}
    assert calls == [["whatsapp", "passport"]]
    assert first["full_name"].source == "rule"
    assert first["whatsapp"].source == "llm"
    assert first["passport"].source == "none"
    assert second["whatsapp"].source == "cache"
    assert second["whatsapp"].value == "9000000001"
