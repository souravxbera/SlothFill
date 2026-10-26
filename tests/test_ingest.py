import json

from slothfill.documents import SAMPLE_LINES, build_blank_pdf, build_text_pdf, extract_text, has_text_layer
from slothfill.extract import merge_profiles, profile_from_model, read_documents, empty_profile


def test_text_pdf_round_trip():
    text = extract_text(build_text_pdf(SAMPLE_LINES))
    assert "Sana Qureshi" in text
    assert "SLTHF0000A" in text
    assert has_text_layer(text)
    assert not has_text_layer("   ")


def test_model_json_is_normalized_and_aadhaar_is_not_kept():
    raw = """```json
    {"name": "Sana Qureshi", "dob": "14/08/2003", "gender": "f", "pan": "slthf 0000 a",
     "aadhaar": "0000 0000 0000", "category": "obc",
     "education": [{"level": "Class 12", "board": "CBSE", "year": "2021", "marks": "91%", "institution": ""}]}
    ```"""
    profile = profile_from_model(raw)
    assert profile["dob"] == "2003-08-14"
    assert profile["gender"] == "Female"
    assert profile["pan"] == "SLTHF0000A"
    assert profile["category"] == "OBC"
    assert profile["aadhaar_masked"] == "XXXX-XXXX-0000"
    assert "aadhaar" not in profile
    assert "000000000000" not in json.dumps(profile)
    assert profile["education"][0]["level"] == "12"


def test_merge_fills_blanks_and_reports_disagreement():
    base = empty_profile()
    base["name"] = "Sana Qureshi"
    extra = empty_profile()
    extra["name"] = "Someone Else"
    extra["email"] = "sana.qureshi@example.com"
    extra["education"] = [{"level": "10", "board": "CBSE", "year": "2019", "marks": "90%", "institution": "School"}]
    conflicts = merge_profiles(base, extra)
    assert conflicts == ["name"]
    assert base["name"] == "Sana Qureshi"
    assert base["email"] == "sana.qureshi@example.com"
    assert base["education"][0]["level"] == "10"


def test_blank_pdf_uses_vision_and_text_pdf_does_not():
    calls = []

    def chat(content, images=None):
        calls.append(images)
        if images:
            return '{"name": "Scan Person"}'
        return '{"name": "Sana Qureshi", "pan": "SLTHF0000A"}'

    text_profile, text_report = read_documents([("id.pdf", build_text_pdf(SAMPLE_LINES))], chat=chat)
    scan_profile, scan_report = read_documents([("scan.pdf", build_blank_pdf())], chat=chat)
    assert text_report["files"][0]["mode"] == "text"
    assert calls[0] is None
    assert text_profile["pan"] == "SLTHF0000A"
    assert scan_report["files"][0]["mode"] == "vision"
    assert calls[1][0].startswith(b"\x89PNG")
    assert scan_profile["name"] == "Scan Person"
