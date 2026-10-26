import json
from html.parser import HTMLParser
from pathlib import Path

from slothfill.engine import map_fields
from slothfill.fields import Field
from slothfill.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE, _ = load_profile(ROOT / "data" / "missing.json", ROOT / "fixtures" / "sana_qureshi.json")


class FormFields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields: list[Field] = []
        self._label_for: str | None = None
        self._label_parts: list[str] = []
        self._labels: dict[str, str] = {}
        self._select_id: str | None = None
        self._options: list[str] = []
        self._in_option = False
        self._option_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "label" and attr.get("for"):
            self._label_for = attr["for"]
            self._label_parts = []
        elif tag == "select":
            self._select_id = attr.get("id") or attr.get("name")
            self._options = []
        elif tag == "option" and self._select_id:
            self._in_option = True
            self._option_parts = []
        elif tag == "input":
            kind = attr.get("type", "text")
            if kind in {"submit", "button", "hidden", "password", "checkbox", "radio"}:
                return
            field_id = attr.get("id") or attr.get("name") or ""
            self.fields.append(
                Field(
                    id=field_id,
                    name=attr.get("name", ""),
                    placeholder=attr.get("placeholder", ""),
                    type=kind,
                )
            )

    def handle_endtag(self, tag):
        if tag == "label" and self._label_for:
            self._labels[self._label_for] = "".join(self._label_parts).strip()
            self._label_for = None
        elif tag == "option" and self._in_option:
            self._options.append("".join(self._option_parts).strip())
            self._in_option = False
        elif tag == "select" and self._select_id:
            self.fields.append(
                Field(id=self._select_id, name=self._select_id, type="select", options=list(self._options))
            )
            self._select_id = None

    def handle_data(self, data):
        if self._label_for:
            self._label_parts.append(data)
        if self._in_option:
            self._option_parts.append(data)

    def finish(self) -> list[Field]:
        labeled = []
        for field in self.fields:
            field.label = self._labels.get(field.id, field.label)
            labeled.append(field)
        return labeled


def fields_in(name: str) -> list[Field]:
    parser = FormFields()
    parser.feed((ROOT / "site" / name).read_text(encoding="utf-8"))
    return parser.finish()


def filled(name: str) -> dict[str, str]:
    mapped = map_fields(fields_in(name), PROFILE, cache=None, url="")
    return {item.id: item.value for item in mapped}


def test_admission_form_uses_the_synthetic_profile():
    values = filled("admission.html")
    assert values["full_name"] == "Sana Qureshi"
    assert values["father_name"] == "Imran Qureshi"
    assert values["dob"] == "14/08/2003"
    assert values["gender"] == "Female"
    assert values["category"] == "OBC"
    assert values["phone"] == "9000000001"
    assert values["email"] == "sana.qureshi@example.com"
    assert values["line1"] == "18 Banyan Lane"
    assert values["line2"] == "Andheri West"
    assert values["city"] == "Mumbai"
    assert values["state"] == "Maharashtra"
    assert values["pincode"] == "400058"
    assert values["board10"] == "Maharashtra State Board"
    assert values["year10"] == "2019"
    assert values["marks10"] == "93.2%"
    assert values["board12"] == "Maharashtra State Board"
    assert values["year12"] == "2021"
    assert values["marks12"] == "91.6%"
    assert values["school12"] == "St. Mary's Junior College"
    assert values["pan"] == "SLTHF0000A"
    assert values["aadhaar"] == "XXXX-XXXX-0000"
    assert values["course"] == ""


def test_kyc_date_input_is_iso_and_aadhaar_stays_masked():
    values = filled("kyc.html")
    assert values["applicant_name"] == "Sana Qureshi"
    assert values["birth"] == "2003-08-14"
    assert values["pan_number"] == "SLTHF0000A"
    assert values["aadhaar_number"] == "XXXX-XXXX-0000"
    assert values["mail"] == "sana.qureshi@example.com"
    assert values["postal"] == "400058"
    assert values["nationality"] == "Indian"


def test_job_form_splits_the_name_and_leaves_portfolio_blank():
    values = filled("job.html")
    assert values["first"] == "Sana"
    assert values["last"] == "Qureshi"
    assert values["college"] == "St. Mary's Junior College"
    assert values["grad_year"] == "2021"
    assert values["score"] == "91.6%"
    assert values["whatsapp"] == ""
    assert values["passport"] == ""
    assert values["portfolio"] == ""


def test_extension_only_talks_to_loopback_and_does_not_submit():
    manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["host_permissions"] == ["http://127.0.0.1:8787/*"]
    assert "content_scripts" not in manifest
    script = (ROOT / "extension" / "content.js").read_text(encoding="utf-8")
    assert "requestSubmit" not in script
    assert ".submit(" not in script
    demo = (ROOT / "site" / "fill.js").read_text(encoding="utf-8")
    assert "preventDefault" in demo
