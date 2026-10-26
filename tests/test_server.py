import json
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from slothfill.config import HOST
from slothfill.documents import SAMPLE_LINES, build_text_pdf
from slothfill.server import create_app


def test_server_stays_on_loopback_and_maps_a_field(tmp_path):
    assert HOST == "127.0.0.1"
    app = create_app(profile_path=tmp_path / "profile.json", cache_path=tmp_path / "cache.json")
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["host"] == "127.0.0.1"
    profile = client.get("/profile")
    assert profile.json()["source"] == "fixture"
    assert profile.json()["profile"]["synthetic"] is True
    mapped = client.post(
        "/map",
        json={
            "url": "http://127.0.0.1:8787/demo/kyc.html",
            "fields": [{"id": "pan_number", "label": "Permanent Account Number"}],
        },
    )
    assert mapped.status_code == 200
    assert mapped.json()["fields"][0]["value"] == "SLTHF0000A"
    page = client.get("/demo/admission.html")
    assert page.status_code == 200
    assert "Fill from local profile" in page.text


def test_sample_ingest_masks_aadhaar_and_saves_locally(tmp_path, monkeypatch):
    def fake(content, images=None):
        assert images is None
        assert "Sana Qureshi" in content
        return json.dumps(
            {
                "name": "Sana Qureshi",
                "dob": "14/08/2003",
                "pan": "SLTHF0000A",
                "aadhaar": "000000000000",
                "address": {"city": "Mumbai"},
            }
        )

    monkeypatch.setattr("slothfill.extract.ask_gemma", fake)
    app = create_app(profile_path=tmp_path / "profile.json", cache_path=tmp_path / "cache.json")
    client = TestClient(app)
    response = client.post("/ingest/sample")
    assert response.status_code == 200
    body = response.json()
    assert body["report"]["files"][0]["mode"] == "text"
    assert body["profile"]["aadhaar_masked"] == "XXXX-XXXX-0000"
    assert body["profile"]["dob"] == "2003-08-14"
    assert "000000000000" not in json.dumps(body["profile"])
    saved = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert saved["name"] == "Sana Qureshi"
    rejected = client.post("/ingest", files=[("files", ("notes.txt", b"hello", "text/plain"))])
    assert rejected.status_code == 400


def test_folder_lists_pdfs_and_reports_scan_progress(tmp_path, monkeypatch):
    folder = tmp_path / "papers"
    folder.mkdir()
    (folder / "id.pdf").write_bytes(build_text_pdf(SAMPLE_LINES))
    (folder / "notes.txt").write_text("skip me", encoding="utf-8")
    nested = folder / "old"
    nested.mkdir()
    (nested / "hidden.pdf").write_bytes(build_text_pdf(["Hidden person"]))
    try:
        (folder / "link.pdf").symlink_to(folder / "id.pdf")
    except OSError:
        pass

    started = threading.Event()
    release = threading.Event()

    def fake(content, images=None):
        assert images is None
        started.set()
        assert release.wait(5)
        return json.dumps({"name": "Sana Qureshi", "pan": "SLTHF0000A"})

    monkeypatch.setattr("slothfill.extract.ask_gemma", fake)
    app = create_app(profile_path=tmp_path / "profile.json", cache_path=tmp_path / "cache.json")
    client = TestClient(app)

    missing = client.post("/ingest/folder", json={"path": str(tmp_path / "nope")})
    assert missing.status_code == 400
    listed = client.post("/ingest/folder", json={"path": str(folder)})
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()["files"]] == ["id.pdf"]

    outside = client.post(
        "/ingest/folder/read",
        json={"path": str(folder), "names": ["../profile.json"]},
    )
    assert outside.status_code == 400

    started_job = client.post(
        "/ingest/folder/read",
        json={"path": str(folder), "names": ["id.pdf"]},
    )
    assert started_job.status_code == 200
    job = started_job.json()["job"]
    assert started.wait(5)
    progress = client.get(f"/ingest/jobs/{job}")
    assert progress.status_code == 200
    body = progress.json()
    assert body["state"] == "reading"
    assert body["index"] == 1
    assert body["total"] == 1
    assert body["file"] == "id.pdf"
    assert body["elapsed"] >= 0
    release.set()
    finished = {}
    for _ in range(50):
        finished = client.get(f"/ingest/jobs/{job}").json()
        if finished["state"] == "done":
            break
    assert finished["state"] == "done"
    assert finished["profile"]["name"] == "Sana Qureshi"
    assert finished["report"]["files"][0]["file"] == "id.pdf"
    saved = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert saved["name"] == "Sana Qureshi"
