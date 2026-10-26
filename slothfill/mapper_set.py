"""Synthetic field-mapping rows for the Tinker LoRA.

Each row is one form field. The answer is a profile key and a transform,
never a person's name, number, or address. Held-out labels use different
phrasing from the training labels.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from slothfill.rules import norm

SYSTEM = (
    "Map one form field onto a profile key. Reply with JSON only: "
    '{"profile_key":"...","transform":"..."}. '
    "Use an empty profile_key when none of the keys fit. "
    "profile_key must be a key, never a copied value. "
    "Allowed keys: name, father_name, dob, gender, phone, email, pan, aadhaar_masked, "
    "category, nationality, address.line1, address.line2, address.city, address.state, "
    "address.pincode, address.country, education.10.board, education.10.year, "
    "education.10.marks, education.10.institution, education.12.board, education.12.year, "
    "education.12.marks, education.12.institution. "
    "Allowed transforms: text, first_name, last_name, dob_iso, dob_dmy_slash, dob_dmy_dash, option."
)

TRAIN_NAMES = ("applicant", "student", "candidate", "form", "entry")


@dataclass(frozen=True)
class Sample:
    label: str
    name: str
    placeholder: str
    field_type: str
    options: tuple[str, ...]
    profile_key: str
    transform: str

    def user_text(self) -> str:
        options = " | ".join(self.options)
        return (
            f"label: {self.label}\n"
            f"name: {self.name}\n"
            f"placeholder: {self.placeholder}\n"
            f"type: {self.field_type}\n"
            f"options: {options}"
        )

    def answer(self) -> str:
        return json.dumps(
            {"profile_key": self.profile_key, "transform": self.transform},
            separators=(",", ":"),
        )

    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": self.user_text()},
            {"role": "assistant", "content": self.answer()},
        ]


def _rows(
    labels: tuple[str, ...],
    names: tuple[str, ...],
    profile_key: str,
    transform: str,
    field_type: str = "text",
    placeholder: str = "",
    options: tuple[str, ...] = (),
) -> list[Sample]:
    return [
        Sample(label, name, placeholder, field_type, options, profile_key, transform)
        for label in labels
        for name in names
    ]


def _train() -> list[Sample]:
    gender = ("Select", "Female", "Male", "Other")
    category = ("Select", "General", "OBC", "SC", "ST", "EWS")
    state = ("Select state", "Maharashtra", "Karnataka", "Delhi", "Tamil Nadu")
    rows: list[Sample] = []
    rows += _rows(
        (
            "full name",
            "applicant name",
            "candidate name",
            "student name",
            "your name",
            "name of the applicant",
            "complete name",
        ),
        TRAIN_NAMES,
        "name",
        "text",
    )
    rows += _rows(
        (
            "first name",
            "given name",
            "forename",
            "applicant first name",
            "student given name",
            "name first part",
            "personal first name",
        ),
        TRAIN_NAMES,
        "name",
        "first_name",
    )
    rows += _rows(
        (
            "last name",
            "surname",
            "family name",
            "applicant surname",
            "student family name",
            "name last part",
            "family surname",
        ),
        TRAIN_NAMES,
        "name",
        "last_name",
    )
    rows += _rows(
        (
            "father name",
            "fathers name",
            "guardian name",
            "father guardian name",
            "fathers guardians name",
            "name of father",
            "guardian of applicant",
        ),
        TRAIN_NAMES,
        "father_name",
        "text",
    )
    rows += _rows(
        (
            "date of birth",
            "birth date",
            "dob",
            "applicant date of birth",
            "student birth date",
            "date of birth of candidate",
            "birth date of student",
        ),
        TRAIN_NAMES,
        "dob",
        "dob_dmy_slash",
        placeholder="DD/MM/YYYY",
    )
    rows += _rows(
        (
            "date of birth dd-mm-yyyy",
            "birth date with dashes",
            "dob dd-mm-yyyy",
            "applicant dob dashed",
            "student birth date dashed",
            "dashed date of birth",
            "birth date dd-mm",
        ),
        TRAIN_NAMES,
        "dob",
        "dob_dmy_dash",
        placeholder="DD-MM-YYYY",
    )
    rows += _rows(
        (
            "date of birth picker",
            "birth date field",
            "dob calendar",
            "applicant birth date picker",
            "student dob picker",
            "calendar date of birth",
            "birth date input",
        ),
        TRAIN_NAMES,
        "dob",
        "dob_iso",
        field_type="date",
    )
    rows += _rows(
        (
            "gender",
            "sex",
            "applicant gender",
            "student sex",
            "candidate gender",
            "gender of applicant",
            "sex of student",
        ),
        TRAIN_NAMES,
        "gender",
        "option",
        field_type="select",
        options=gender,
    )
    rows += _rows(
        (
            "mobile number",
            "phone number",
            "contact number",
            "mobile no",
            "telephone number",
            "cell number",
            "registered mobile",
        ),
        TRAIN_NAMES,
        "phone",
        "text",
    )
    rows += _rows(
        (
            "email",
            "email address",
            "e mail",
            "applicant email",
            "student email address",
            "contact email",
            "mail id",
        ),
        TRAIN_NAMES,
        "email",
        "text",
    )
    rows += _rows(
        (
            "pan",
            "pan number",
            "permanent account number",
            "applicant pan",
            "student pan number",
            "income tax pan",
            "pan of applicant",
        ),
        TRAIN_NAMES,
        "pan",
        "text",
    )
    rows += _rows(
        (
            "aadhaar",
            "aadhar",
            "aadhaar number",
            "applicant aadhaar",
            "student aadhaar number",
            "uidai number",
            "aadhaar of applicant",
        ),
        TRAIN_NAMES,
        "aadhaar_masked",
        "text",
    )
    rows += _rows(
        (
            "category",
            "caste category",
            "reservation category",
            "quota",
            "applicant category",
            "student caste category",
            "reservation quota",
        ),
        TRAIN_NAMES,
        "category",
        "option",
        field_type="select",
        options=category,
    )
    rows += _rows(
        (
            "nationality",
            "citizen of",
            "applicant nationality",
            "student nationality",
            "country of citizenship",
            "nationality of candidate",
            "citizenship",
        ),
        TRAIN_NAMES,
        "nationality",
        "text",
    )
    rows += _rows(
        (
            "address",
            "address line 1",
            "residential address",
            "street address",
            "house address",
            "applicant address",
            "present address line",
        ),
        TRAIN_NAMES,
        "address.line1",
        "text",
    )
    rows += _rows(
        (
            "address line 2",
            "street line 2",
            "apartment or area",
            "locality",
            "applicant address line 2",
            "landmark and area",
            "second address line",
        ),
        TRAIN_NAMES,
        "address.line2",
        "text",
    )
    rows += _rows(
        (
            "city",
            "town",
            "applicant city",
            "student city",
            "city or town",
            "place of residence",
            "home city",
        ),
        TRAIN_NAMES,
        "address.city",
        "text",
    )
    rows += _rows(
        (
            "state",
            "applicant state",
            "student state",
            "state or ut",
            "home state",
            "state of residence",
            "province",
        ),
        TRAIN_NAMES,
        "address.state",
        "option",
        field_type="select",
        options=state,
    )
    rows += _rows(
        (
            "pincode",
            "pin code",
            "postal code",
            "zip code",
            "applicant pincode",
            "student pin code",
            "area pin",
        ),
        TRAIN_NAMES,
        "address.pincode",
        "text",
    )
    rows += _rows(
        (
            "country",
            "country of residence",
            "applicant country",
            "student country",
            "home country",
            "residing country",
            "nation of residence",
        ),
        TRAIN_NAMES,
        "address.country",
        "text",
    )
    rows += _edu_rows("10")
    rows += _edu_rows("12")
    rows += _rows(
        (
            "passport number",
            "visa number",
            "preferred course",
            "portfolio url",
            "mother tongue",
            "religion",
            "blood group",
            "marital status",
            "salary",
            "mothers name",
            "otp",
            "password",
            "middle name",
            "spouse name",
            "username",
            "website",
            "linkedin",
            "github",
        ),
        TRAIN_NAMES,
        "",
        "text",
    )
    return rows


def _edu_rows(level: str) -> list[Sample]:
    if level == "10":
        board = (
            "10th board",
            "class 10 board",
            "ssc board",
            "matric board",
            "secondary board",
            "tenth board",
            "board of class 10",
        )
        year = (
            "10th year of passing",
            "class 10 passing year",
            "ssc year",
            "matric year",
            "secondary passing year",
            "tenth pass year",
            "year of class 10",
        )
        marks = (
            "10th percentage",
            "class 10 marks",
            "ssc percentage",
            "matric marks",
            "secondary percentage",
            "tenth score",
            "marks of class 10",
        )
        school = (
            "10th school",
            "class 10 institution",
            "ssc school",
            "matric school",
            "secondary school",
            "tenth institution",
            "school of class 10",
        )
    else:
        board = (
            "12th board",
            "class 12 board",
            "hsc board",
            "intermediate board",
            "senior secondary board",
            "twelfth board",
            "board of class 12",
        )
        year = (
            "12th year of passing",
            "class 12 passing year",
            "hsc year",
            "intermediate year",
            "senior secondary year",
            "twelfth pass year",
            "year of graduation",
        )
        marks = (
            "12th percentage",
            "class 12 marks",
            "hsc percentage",
            "intermediate marks",
            "senior secondary percentage",
            "twelfth score",
            "percentage of class 12",
        )
        school = (
            "12th college",
            "class 12 institution",
            "hsc college",
            "intermediate college",
            "senior secondary school",
            "twelfth institution",
            "college of class 12",
        )
    key = f"education.{level}"
    rows: list[Sample] = []
    rows += _rows(board, TRAIN_NAMES, f"{key}.board", "text")
    rows += _rows(year, TRAIN_NAMES, f"{key}.year", "text")
    rows += _rows(marks, TRAIN_NAMES, f"{key}.marks", "text")
    rows += _rows(school, TRAIN_NAMES, f"{key}.institution", "text")
    return rows


def _heldout() -> list[Sample]:
    gender = ("Woman", "Man", "Non-binary")
    category = ("Unreserved", "Other Backward Class", "Scheduled Caste", "Scheduled Tribe")
    state = ("Kerala", "Gujarat", "Rajasthan", "West Bengal")
    specs: list[tuple] = [
        ("name in full", "name", "text", "text", "", ()),
        ("legal name", "name", "text", "text", "", ()),
        ("name as per marksheet", "name", "text", "text", "", ()),
        ("name printed on the form", "name", "text", "text", "", ()),
        ("official full name", "name", "text", "text", "", ()),
        ("personal name", "name", "first_name", "text", "", ()),
        ("own given name", "name", "first_name", "text", "", ()),
        ("christian name", "name", "first_name", "text", "", ()),
        ("name before the surname", "name", "first_name", "text", "", ()),
        ("individual given name", "name", "first_name", "text", "", ()),
        ("hereditary family title", "name", "last_name", "text", "", ()),
        ("name after the given name", "name", "last_name", "text", "", ()),
        ("clan title", "name", "last_name", "text", "", ()),
        ("trailing family title", "name", "last_name", "text", "", ()),
        ("last written name", "name", "last_name", "text", "", ()),
        ("son daughter of", "father_name", "text", "text", "", ()),
        ("s o d o w o", "father_name", "text", "text", "", ()),
        ("name of parent", "father_name", "text", "text", "", ()),
        ("parent or guardian", "father_name", "text", "text", "", ()),
        ("c o of the student", "father_name", "text", "text", "", ()),
        ("born on", "dob", "dob_dmy_slash", "text", "DD/MM/YYYY", ()),
        ("day month year of birth", "dob", "dob_dmy_slash", "text", "DD/MM/YYYY", ()),
        ("birth as dd/mm/yyyy", "dob", "dob_dmy_slash", "text", "DD/MM/YYYY", ()),
        ("natal day slash", "dob", "dob_dmy_slash", "text", "DD/MM/YYYY", ()),
        ("when were you born slash", "dob", "dob_dmy_slash", "text", "DD/MM/YYYY", ()),
        ("born on dashed", "dob", "dob_dmy_dash", "text", "DD-MM-YYYY", ()),
        ("day-month-year of birth", "dob", "dob_dmy_dash", "text", "DD-MM-YYYY", ()),
        ("birth as dd-mm-yyyy", "dob", "dob_dmy_dash", "text", "DD-MM-YYYY", ()),
        ("natal day dash", "dob", "dob_dmy_dash", "text", "DD-MM-YYYY", ()),
        ("when were you born dashed", "dob", "dob_dmy_dash", "text", "DD-MM-YYYY", ()),
        ("born on calendar", "dob", "dob_iso", "date", "", ()),
        ("native date picker", "dob", "dob_iso", "date", "", ()),
        ("birth calendar control", "dob", "dob_iso", "date", "", ()),
        ("iso birth control", "dob", "dob_iso", "date", "", ()),
        ("html birth widget", "dob", "dob_iso", "date", "", ()),
        ("male or female", "gender", "option", "select", "", gender),
        ("woman man or other", "gender", "option", "select", "", gender),
        ("identity as woman or man", "gender", "option", "radio", "", gender),
        ("f or m selection", "gender", "option", "select", "", gender),
        ("presented gender", "gender", "option", "select", "", gender),
        ("whatsapp number", "phone", "text", "text", "", ()),
        ("handphone", "phone", "text", "text", "", ()),
        ("reachable number", "phone", "text", "text", "", ()),
        ("callback number", "phone", "text", "text", "", ()),
        ("number on whatsapp", "phone", "text", "text", "", ()),
        ("inbox address", "email", "text", "text", "", ()),
        ("electronic mail", "email", "text", "text", "", ()),
        ("mail box", "email", "text", "text", "", ()),
        ("write to address", "email", "text", "text", "", ()),
        ("notification mail", "email", "text", "text", "", ()),
        ("tax id pan card", "pan", "text", "text", "", ()),
        ("card permanent account", "pan", "text", "text", "", ()),
        ("it department number", "pan", "text", "text", "", ()),
        ("pan card no", "pan", "text", "text", "", ()),
        ("taxpayer account", "pan", "text", "text", "", ()),
        ("uid number", "aadhaar_masked", "text", "text", "", ()),
        ("twelve digit uid", "aadhaar_masked", "text", "text", "", ()),
        ("identity uidai", "aadhaar_masked", "text", "text", "", ()),
        ("aadhaar card no", "aadhaar_masked", "text", "text", "", ()),
        ("govt uid", "aadhaar_masked", "text", "text", "", ()),
        ("social group", "category", "option", "select", "", category),
        ("community class", "category", "option", "select", "", category),
        ("backward class selection", "category", "option", "select", "", category),
        ("reservation bucket", "category", "option", "select", "", category),
        ("caste group", "category", "option", "select", "", category),
        ("country of your citizenship", "nationality", "text", "text", "", ()),
        ("citizen nation", "nationality", "text", "text", "", ()),
        ("which country are you from", "nationality", "text", "text", "", ()),
        ("national status", "nationality", "text", "text", "", ()),
        ("born a citizen of", "nationality", "text", "text", "", ()),
        ("house number and street", "address.line1", "text", "text", "", ()),
        ("door no and road", "address.line1", "text", "text", "", ()),
        ("where do you live line", "address.line1", "text", "text", "", ()),
        ("plot and street", "address.line1", "text", "text", "", ()),
        ("residence first line", "address.line1", "text", "text", "", ()),
        ("flat society or area", "address.line2", "text", "text", "", ()),
        ("building and locality", "address.line2", "text", "text", "", ()),
        ("second line of residence", "address.line2", "text", "text", "", ()),
        ("area after the street", "address.line2", "text", "text", "", ()),
        ("colony or nagar", "address.line2", "text", "text", "", ()),
        ("town or city name", "address.city", "text", "text", "", ()),
        ("municipal city", "address.city", "text", "text", "", ()),
        ("which city", "address.city", "text", "text", "", ()),
        ("urban centre", "address.city", "text", "text", "", ()),
        ("city you live in", "address.city", "text", "text", "", ()),
        ("which state or union territory", "address.state", "option", "select", "", state),
        ("home province", "address.state", "option", "select", "", state),
        ("state you live in", "address.state", "option", "select", "", state),
        ("regional state", "address.state", "option", "select", "", state),
        ("union territory or state", "address.state", "option", "select", "", state),
        ("postal index", "address.pincode", "text", "text", "", ()),
        ("six digit pin", "address.pincode", "text", "text", "", ()),
        ("post office number", "address.pincode", "text", "text", "", ()),
        ("zip index", "address.pincode", "text", "text", "", ()),
        ("area postal index", "address.pincode", "text", "text", "", ()),
        ("which country do you live in", "address.country", "text", "text", "", ()),
        ("residence nation", "address.country", "text", "text", "", ()),
        ("country on the envelope", "address.country", "text", "text", "", ()),
        ("living country", "address.country", "text", "text", "", ()),
        ("present nation", "address.country", "text", "text", "", ()),
        ("std x board", "education.10.board", "text", "text", "", ()),
        ("grade 10 examining body", "education.10.board", "text", "text", "", ()),
        ("board at tenth standard", "education.10.board", "text", "text", "", ()),
        ("class x examination board", "education.10.board", "text", "text", "", ()),
        ("high school examining board", "education.10.board", "text", "text", "", ()),
        ("std x passout year", "education.10.year", "text", "text", "", ()),
        ("year cleared class x", "education.10.year", "text", "text", "", ()),
        ("tenth standard year", "education.10.year", "text", "text", "", ()),
        ("grade 10 completion year", "education.10.year", "text", "text", "", ()),
        ("when did class x finish", "education.10.year", "text", "text", "", ()),
        ("std x percent", "education.10.marks", "text", "text", "", ()),
        ("grade 10 result", "education.10.marks", "text", "text", "", ()),
        ("class x score", "education.10.marks", "text", "text", "", ()),
        ("tenth standard marks", "education.10.marks", "text", "text", "", ()),
        ("high school percentage", "education.10.marks", "text", "text", "", ()),
        ("std x school name", "education.10.institution", "text", "text", "", ()),
        ("grade 10 school", "education.10.institution", "text", "text", "", ()),
        ("where class x was studied", "education.10.institution", "text", "text", "", ()),
        ("tenth standard school", "education.10.institution", "text", "text", "", ()),
        ("high school attended", "education.10.institution", "text", "text", "", ()),
        ("std xii board", "education.12.board", "text", "text", "", ()),
        ("grade 12 examining body", "education.12.board", "text", "text", "", ()),
        ("board at twelfth standard", "education.12.board", "text", "text", "", ()),
        ("class xii examination board", "education.12.board", "text", "text", "", ()),
        ("junior college examining board", "education.12.board", "text", "text", "", ()),
        ("std xii passout year", "education.12.year", "text", "text", "", ()),
        ("year cleared class xii", "education.12.year", "text", "text", "", ()),
        ("twelfth standard year", "education.12.year", "text", "text", "", ()),
        ("grade 12 completion year", "education.12.year", "text", "text", "", ()),
        ("when did class xii finish", "education.12.year", "text", "text", "", ()),
        ("std xii percent", "education.12.marks", "text", "text", "", ()),
        ("grade 12 result", "education.12.marks", "text", "text", "", ()),
        ("class xii score", "education.12.marks", "text", "text", "", ()),
        ("twelfth standard marks", "education.12.marks", "text", "text", "", ()),
        ("junior college percentage", "education.12.marks", "text", "text", "", ()),
        ("std xii college name", "education.12.institution", "text", "text", "", ()),
        ("grade 12 college", "education.12.institution", "text", "text", "", ()),
        ("where class xii was studied", "education.12.institution", "text", "text", "", ()),
        ("twelfth standard college", "education.12.institution", "text", "text", "", ()),
        ("junior college attended", "education.12.institution", "text", "text", "", ()),
        ("travel document number", "", "text", "text", "", ()),
        ("programme applied for", "", "text", "text", "", ()),
        ("personal site", "", "text", "text", "", ()),
        ("native language", "", "text", "text", "", ()),
        ("faith", "", "text", "text", "", ()),
        ("blood type", "", "text", "text", "", ()),
        ("civil status", "", "text", "text", "", ()),
        ("expected stipend", "", "text", "text", "", ()),
        ("maternal parent name", "", "text", "text", "", ()),
        ("one time code", "", "text", "text", "", ()),
        ("secret password", "", "text", "text", "", ()),
        ("second given name", "", "text", "text", "", ()),
        ("husband or wife", "", "text", "text", "", ()),
        ("login name", "", "text", "text", "", ()),
        ("homepage link", "", "text", "text", "", ()),
        ("professional network url", "", "text", "text", "", ()),
        ("code host profile", "", "text", "text", "", ()),
        ("driving licence number", "", "text", "text", "", ()),
        ("voter id", "", "text", "text", "", ()),
        ("stream or major", "", "text", "text", "", ()),
        ("behance url", "", "text", "text", "", ()),
        ("emergency contact", "", "text", "text", "", ()),
        ("job title", "", "text", "text", "", ()),
        ("annual ctc", "", "text", "text", "", ()),
        ("skype id", "", "text", "text", "", ()),
    ]
    rows = []
    for index, (label, key, transform, field_type, placeholder, options) in enumerate(specs, start=1):
        rows.append(
            Sample(
                label=label,
                name=f"f{index:03d}",
                placeholder=placeholder,
                field_type=field_type,
                options=options,
                profile_key=key,
                transform=transform,
            )
        )
    return rows


def build_splits() -> tuple[list[Sample], list[Sample]]:
    return _train(), _heldout()


def overlapping_phrases(train: list[Sample], heldout: list[Sample], minimum: int = 12) -> list[tuple[str, str]]:
    """Held-out labels that still contain a long training phrase, or the reverse."""
    train_labels = {norm(row.label) for row in train}
    held_labels = {norm(row.label) for row in heldout}
    hits: list[tuple[str, str]] = []
    for held in held_labels:
        for trained in train_labels:
            if held == trained:
                hits.append((trained, held))
            elif len(trained) >= minimum and trained in held:
                hits.append((trained, held))
            elif len(held) >= minimum and held in trained:
                hits.append((held, trained))
    return hits
