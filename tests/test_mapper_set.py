import json

from slothfill.mapper_set import SYSTEM, build_splits, overlapping_phrases
from slothfill.rules import norm

ALLOWED = {
    "",
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


def test_splits_are_large_disjoint_and_answer_with_keys_only():
    train, heldout = build_splits()
    assert 950 <= len(train) <= 1100
    assert 140 <= len(heldout) <= 170
    assert not overlapping_phrases(train, heldout)
    train_labels = {norm(row.label) for row in train}
    held_labels = {norm(row.label) for row in heldout}
    assert train_labels.isdisjoint(held_labels)
    for row in train + heldout:
        assert row.profile_key in ALLOWED
        assert row.transform in TRANSFORMS
        parsed = json.loads(row.answer())
        assert set(parsed) == {"profile_key", "transform"}
        assert parsed["profile_key"] == row.profile_key
        blob = f"{row.label} {row.user_text()} {row.answer()}".lower()
        assert "sana" not in blob
        assert "9000000001" not in blob
        assert "slthf" not in blob
    covered = {row.profile_key for row in train}
    assert ALLOWED <= covered
    assert {row.profile_key for row in heldout} == ALLOWED
    whatsapp = next(row for row in heldout if row.label == "whatsapp number")
    assert whatsapp.profile_key == "phone"
    passport = next(row for row in heldout if row.label == "travel document number")
    assert passport.profile_key == ""
    assert "empty profile_key" in SYSTEM
