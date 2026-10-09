"""Unit tests for document validation (extension whitelist + size)."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationAppError
from app.presentation.schemas.documents import ALLOWED_EXTENSIONS, MAX_SIZE_BYTES


class TestValidateDocumentInput:
    """Tests for validate_document_input()."""

    def _validate(self, filename: str, size_bytes: int) -> str:
        from app.application.documents.use_cases import validate_document_input

        return validate_document_input(filename, size_bytes)

    # ── Valid extensions ────────────────────────────────────────────

    @pytest.mark.parametrize(
        "filename",
        [
            "report.pdf",
            "photo.png",
            "avatar.jpg",
            "snapshot.jpeg",
            "resume.docx",
            "REPORT.PDF",
            "My File.DOCX",
        ],
    )
    def test_valid_extensions_accepted(self, filename: str):
        ext = self._validate(filename, 1024)
        assert ext in ALLOWED_EXTENSIONS

    # ── Invalid extensions ──────────────────────────────────────────

    @pytest.mark.parametrize(
        "filename",
        [
            "script.exe",
            "archive.zip",
            "data.csv",
            "macro.xlsm",
            "page.html",
            "noext",
        ],
    )
    def test_invalid_extensions_rejected(self, filename: str):
        with pytest.raises(ValidationAppError, match="not allowed"):
            self._validate(filename, 1024)

    # ── Size limits ─────────────────────────────────────────────────

    def test_max_size_exactly_allowed(self):
        ext = self._validate("doc.pdf", MAX_SIZE_BYTES)
        assert ext == "pdf"

    def test_over_max_size_rejected(self):
        with pytest.raises(ValidationAppError, match="exceeds maximum"):
            self._validate("doc.pdf", MAX_SIZE_BYTES + 1)

    def test_zero_size_not_passed_through(self):
        """Zero-size files should still have ext validation pass (size > 0
        is enforced by Pydantic on the request schema, not here)."""
        ext = self._validate("doc.pdf", 0)
        assert ext == "pdf"

    # ── Edge cases ──────────────────────────────────────────────────

    def test_double_extension_uses_last(self):
        ext = self._validate("archive.tar.pdf", 500)
        assert ext == "pdf"

    def test_case_insensitive_extension(self):
        ext = self._validate("Photo.JPG", 500)
        assert ext == "jpg"
