"""Local API. Bound to loopback by the module runner."""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from slothfill.cache import DomainCache
from slothfill.config import DOCUMENT_MODEL, HOST, MAPPER_MODEL, PORT
from slothfill.documents import SAMPLE_LINES, build_text_pdf
from slothfill.engine import map_fields
from slothfill.extract import ModelError, ParseError, profile_from_model, read_documents
from slothfill.folders import FolderError, list_pdfs, load_pdfs
from slothfill.fields import Field as FormField
from slothfill.llm_map import ask_mapper
from slothfill.profile import load_profile, save_profile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "sana_qureshi.json"
SITE = ROOT / "site"


class FieldIn(BaseModel):
    id: str
    label: str = ""
    name: str = ""
    placeholder: str = ""
    type: str = "text"
    options: list[str] = Field(default_factory=list)
    tag: str = "input"


class MapIn(BaseModel):
    url: str = ""
    fields: list[FieldIn]


class FolderIn(BaseModel):
    path: str = ""


class FolderReadIn(BaseModel):
    path: str = ""
    names: list[str] = Field(default_factory=list)


def create_app(profile_path: Path | None = None, cache_path: Path | None = None) -> FastAPI:
    profile_file = profile_path or (ROOT / "data" / "profile.json")
    cache_file = cache_path or (ROOT / "data" / "domain_cache.json")
    jobs: dict[str, dict] = {}
    jobs_lock = threading.Lock()
    app = FastAPI(title="SlothFill", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "host": HOST,
            "port": PORT,
            "mapper": f"rules+{MAPPER_MODEL}",
            "document_model": DOCUMENT_MODEL,
        }

    @app.get("/profile")
    def profile() -> dict:
        data, source = load_profile(profile_file, FIXTURE)
        return {"source": source, "profile": data}

    @app.post("/map")
    def map_form(body: MapIn) -> dict:
        data, _source = load_profile(profile_file, FIXTURE)
        fields = [FormField.from_dict(item.model_dump()) for item in body.fields[:200]]
        cache = DomainCache(cache_file)

        def chat(pending, profile):
            return ask_mapper(pending, profile)

        mapped = map_fields(fields, data, cache, body.url, chat=chat)
        return {"fields": [item.as_dict() for item in mapped]}

    @app.post("/profile")
    def save(body: dict) -> dict:
        try:
            profile = profile_from_model(json.dumps(body))
        except ParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not profile["name"]:
            raise HTTPException(status_code=400, detail="Add a name before saving.")
        save_profile(profile_file, profile)
        return {"source": "local", "profile": profile}

    def _store(parts: list[tuple[str, bytes]]) -> dict:
        try:
            profile, report = read_documents(parts)
        except ModelError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="That PDF could not be read.") from exc
        save_profile(profile_file, profile)
        return {"profile": profile, "report": report}

    @app.post("/ingest")
    async def ingest(files: list[UploadFile] = File(...)) -> dict:
        if not files:
            raise HTTPException(status_code=400, detail="Upload a PDF.")
        parts: list[tuple[str, bytes]] = []
        for upload in files[:5]:
            name = upload.filename or "document.pdf"
            if not name.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Upload PDFs only.")
            data = await upload.read()
            if len(data) > 15 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Each PDF must be under 15 MB.")
            parts.append((name, data))
        return _store(parts)

    def _job_view(job: dict) -> dict:
        elapsed = 0
        if job["state"] == "reading" and job["file"]:
            elapsed = max(0, int(time.time() - job["file_started"]))
        return {
            "state": job["state"],
            "index": job["index"],
            "total": job["total"],
            "file": job["file"],
            "elapsed": elapsed,
            "detail": job["detail"],
            "profile": job["profile"],
            "report": job["report"],
        }

    @app.post("/ingest/folder")
    def ingest_folder(body: FolderIn) -> dict:
        try:
            folder, files = list_pdfs(body.path)
        except FolderError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"path": str(folder), "files": files}

    @app.post("/ingest/folder/read")
    def ingest_folder_read(body: FolderReadIn) -> dict:
        try:
            parts = load_pdfs(body.path, body.names)
        except FolderError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job_id = uuid.uuid4().hex
        job = {
            "state": "reading",
            "index": 0,
            "total": len(parts),
            "file": "",
            "file_started": time.time(),
            "detail": "",
            "profile": None,
            "report": None,
        }
        with jobs_lock:
            jobs[job_id] = job
            if len(jobs) > 8:
                for old in list(jobs)[:-8]:
                    jobs.pop(old, None)

        def run() -> None:
            try:

                def on_file(index: int, total: int, name: str) -> None:
                    with jobs_lock:
                        job["index"] = index
                        job["total"] = total
                        job["file"] = name
                        job["file_started"] = time.time()

                profile, report = read_documents(parts, on_file=on_file)
            except ModelError as exc:
                detail = str(exc)
                state = "error"
                profile = None
                report = None
            except ParseError as exc:
                detail = str(exc)
                state = "error"
                profile = None
                report = None
            except Exception:
                detail = "That PDF could not be read."
                state = "error"
                profile = None
                report = None
            else:
                save_profile(profile_file, profile)
                detail = ""
                state = "done"
            with jobs_lock:
                job["state"] = state
                job["detail"] = detail
                job["profile"] = profile
                job["report"] = report
                if state == "done":
                    job["file"] = ""
                    job["index"] = job["total"]

        threading.Thread(target=run, daemon=True).start()
        return {"job": job_id}

    @app.get("/ingest/jobs/{job_id}")
    def ingest_job(job_id: str) -> dict:
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="That scan is no longer running.")
            return _job_view(job)

    @app.post("/ingest/sample")
    def ingest_sample() -> dict:
        sample = FIXTURE.with_name("sana_application.pdf")
        if not sample.exists():
            sample.write_bytes(build_text_pdf(SAMPLE_LINES))
        return _store([("sana_application.pdf", sample.read_bytes())])

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse("/demo/")

    if SITE.exists():
        app.mount("/demo", StaticFiles(directory=SITE, html=True), name="demo")
    return app


app = create_app()
