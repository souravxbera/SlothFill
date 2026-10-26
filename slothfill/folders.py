"""List PDFs in one folder the user named. The model never sees the path."""

from __future__ import annotations

from pathlib import Path

MAX_PDF_BYTES = 15 * 1024 * 1024
MAX_FOLDER_FILES = 20


class FolderError(ValueError):
    pass


def folder_path(raw: str) -> Path:
    text = (raw or "").strip()
    if not text:
        raise FolderError("Enter a folder path.")
    path = Path(text).expanduser()
    if not path.exists():
        raise FolderError("That folder does not exist.")
    resolved = path.resolve()
    if not resolved.is_dir():
        raise FolderError("That path is not a folder.")
    return resolved


def list_pdfs(raw: str, max_bytes: int = MAX_PDF_BYTES) -> tuple[Path, list[dict]]:
    folder = folder_path(raw)
    found: list[dict] = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
        if entry.is_symlink() or not entry.is_file():
            continue
        if entry.suffix.lower() != ".pdf":
            continue
        if entry.resolve().parent != folder:
            continue
        size = entry.stat().st_size
        if size <= 0:
            found.append({"name": entry.name, "bytes": size, "readable": False, "reason": "Empty file"})
        elif size > max_bytes:
            found.append({"name": entry.name, "bytes": size, "readable": False, "reason": "Over 15 MB"})
        else:
            found.append({"name": entry.name, "bytes": size, "readable": True, "reason": ""})
    return folder, found


def load_pdfs(raw: str, names: list[str], max_bytes: int = MAX_PDF_BYTES) -> list[tuple[str, bytes]]:
    folder = folder_path(raw)
    chosen: list[str] = []
    for name in names:
        if name not in chosen:
            chosen.append(name)
    if not chosen:
        raise FolderError("Select a PDF first.")
    if len(chosen) > MAX_FOLDER_FILES:
        raise FolderError(f"Select up to {MAX_FOLDER_FILES} PDFs.")
    parts: list[tuple[str, bytes]] = []
    for name in chosen:
        if name != Path(name).name or name in {".", ".."}:
            raise FolderError("Choose PDFs from the list.")
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".pdf":
            raise FolderError(f"{name} is not a PDF in that folder.")
        if path.resolve().parent != folder:
            raise FolderError(f"{name} is not a PDF in that folder.")
        data = path.read_bytes()
        if not data or len(data) > max_bytes:
            raise FolderError(f"{name} is empty or over 15 MB.")
        parts.append((name, data))
    return parts
