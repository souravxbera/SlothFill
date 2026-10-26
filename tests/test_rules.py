import json
from pathlib import Path

from slothfill.cache import DomainCache
from slothfill.engine import map_fields
from slothfill.fields import Field
from slothfill.profile import load_profile, resolve

ROOT = Path(__file__).resolve().parents[1]
PROFILE, SOURCE = load_profile(ROOT / "data" / "missing.json", ROOT / "fixtures" / "sana_qureshi.json")


def test_fixture_is_what_loads_when_no_local_profile_exists():
    assert SOURCE == "fixture"
    assert PROFILE["synthetic"] is True
    assert resolve(PROFILE, "education.10.marks") == "93.2%"
    assert resolve(PROFILE, "address.city") == "Mumbai"


def test_password_and_mother_name_are_not_filled():
    fields = [
        Field(id="pw", label="Password", type="password"),
        Field(id="mom", label="Mother's name"),
        Field(id="otp", label="OTP"),
    ]
    mapped = {item.id: item for item in map_fields(fields, PROFILE, None, "")}
    assert mapped["pw"].source == "none"
    assert mapped["mom"].source == "none"
    assert mapped["otp"].value == ""


def test_gender_radio_options_match():
    field = Field(id="gender", label="Gender", type="radio", options=["Female", "Male", "Other"])
    mapped = map_fields([field], PROFILE, None, "")[0]
    assert mapped.value == "Female"
    assert mapped.confidence >= 0.9


def test_repeat_visit_uses_the_cache_and_the_current_profile(tmp_path):
    cache = DomainCache(tmp_path / "cache.json")
    fields = [Field(id="full_name", label="Full name")]
    url = "http://127.0.0.1:8787/demo/admission.html"
    first = map_fields(fields, PROFILE, cache, url)[0]
    assert first.source == "rule"
    changed = json.loads(json.dumps(PROFILE))
    changed["name"] = "Amina Qureshi"
    second = map_fields(fields, changed, cache, url)[0]
    assert second.source == "cache"
    assert second.value == "Amina Qureshi"
