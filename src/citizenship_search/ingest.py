from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff", ".bmp"}


def _printable_text_fallback(data: bytes) -> str:
    decoded = data.decode("latin-1", errors="ignore")
    filtered = "".join(ch if ch.isprintable() or ch in "\n\r\t" else " " for ch in decoded)
    compact = " ".join(filtered.split())
    return compact[:4000]


def ingest_uploaded_file(
    filename: str,
    file_bytes: bytes,
    language: str,
    source_name: str | None = None,
) -> dict[str, object]:
    path = Path(filename)
    suffix = path.suffix.lower()
    source_name = source_name or f"Uploaded file: {filename}"
    result: dict[str, object] = {
        "filename": filename or "uploaded.bin",
        "source_name": source_name,
        "language": language or "unknown",
        "media_type": "binary",
        "extractor": "none",
        "extraction_status": "stored_only",
        "text": "",
        "original_bytes": file_bytes,
    }

    if suffix in TEXT_EXTENSIONS:
        result["media_type"] = "text"
        result["extractor"] = "utf-8-decode"
        result["extraction_status"] = "text_extracted"
        result["text"] = file_bytes.decode("utf-8", errors="replace")
        return result

    if suffix == ".pdf":
        result["media_type"] = "pdf"
        # Best-effort PDF -> text extraction using macOS `textutil`.
        # If it fails (bad/corrupt PDF or unsupported structure), we fall back.
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                in_path = Path(tmpdir) / (path.name or "input.pdf")
                out_path = Path(tmpdir) / "out.txt"
                in_path.write_bytes(file_bytes)

                # `-convert txt` can handle PDFs on macOS.
                proc = subprocess.run(
                    [
                        "textutil",
                        "-convert",
                        "txt",
                        "-output",
                        str(out_path),
                        str(in_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )

                if out_path.exists() and out_path.stat().st_size > 0 and proc.returncode == 0:
                    text = out_path.read_text(encoding="utf-8", errors="replace")
                    result["extractor"] = "textutil"
                    result["text"] = text
                    result["extraction_status"] = "textutil_pdf_text_extracted" if text.strip() else "pdf_no_text_from_textutil"
                    return result
        except Exception:
            # fall back below
            pass

        result["extractor"] = "printable-text-fallback"
        result["text"] = _printable_text_fallback(file_bytes)
        result["extraction_status"] = "partial_pdf_text" if result["text"] else "pdf_no_text_extractor"
        return result

    if suffix in IMAGE_EXTENSIONS:
        result["media_type"] = "image"
        result["extractor"] = "none"
        result["extraction_status"] = "image_saved_ocr_unavailable"
        return result

    result["text"] = _printable_text_fallback(file_bytes)
    if result["text"]:
        result["extractor"] = "printable-text-fallback"
        result["extraction_status"] = "partial_binary_text"
    return result
