"""Read PDF bytes. Text goes through pypdf. A scan is rendered for Gemma vision."""

from __future__ import annotations

import io
import re

from pypdf import PdfReader

SAMPLE_LINES = [
    "SYNTHETIC DOCUMENT. Not a real identity.",
    "Full name: Sana Qureshi",
    "Father's name: Imran Qureshi",
    "Date of birth: 14/08/2003",
    "Gender: Female",
    "Mobile: 9000000001",
    "Email: sana.qureshi@example.com",
    "Address line 1: 18 Banyan Lane",
    "Address line 2: Andheri West",
    "City: Mumbai",
    "State: Maharashtra",
    "PIN code: 400058",
    "Country: India",
    "PAN: SLTHF0000A",
    "Aadhaar: 000000000000",
    "Category: OBC",
    "Nationality: Indian",
    "Class 10 board: Maharashtra State Board",
    "Class 10 year: 2019",
    "Class 10 marks: 93.2%",
    "Class 10 school: St. Mary's High School",
    "Class 12 board: Maharashtra State Board",
    "Class 12 year: 2021",
    "Class 12 marks: 91.6%",
    "Class 12 college: St. Mary's Junior College",
]


def build_text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with Helvetica text. Enough for pypdf to read back."""
    commands = ["BT", "/F1 11 Tf"]
    y = 760
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        safe = safe.encode("latin-1", "replace").decode("latin-1")
        commands.append(f"1 0 0 1 54 {y} Tm ({safe}) Tj")
        y -= 16
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def build_blank_pdf() -> bytes:
    """A page with no text layer, so ingest must render it."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def extract_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages[:5]:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def has_text_layer(text: str) -> bool:
    return len(re.sub(r"[^A-Za-z0-9]", "", text)) >= 40


def render_pages(data: bytes, limit: int = 2) -> list[bytes]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    images: list[bytes] = []
    try:
        for index in range(min(len(pdf), limit)):
            page = pdf[index]
            bitmap = page.render(scale=2)
            image = bitmap.to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            images.append(buffer.getvalue())
            bitmap.close()
            page.close()
    finally:
        pdf.close()
    return images
