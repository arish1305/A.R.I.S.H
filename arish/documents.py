from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from arish.config import AppConfig
from arish.tools import ToolResult


@dataclass(frozen=True)
class DocumentSummary:
    path: str
    characters: int
    preview: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "characters": self.characters,
            "preview": self.preview,
        }


class DocumentAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.documents_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> ToolResult:
        return ToolResult(
            "documents",
            True,
            "Document agent is ready for TXT and Markdown. PDF and DOCX work when optional packages are installed.",
            {
                "documents_dir": str(self.config.documents_dir),
                "supported": ["txt", "md", "markdown", "pdf", "docx"],
                "optional_packages": ["pypdf", "python-docx"],
            },
        )

    def read_document(self, path_text: str, max_chars: int = 6000) -> ToolResult:
        path = Path(path_text).expanduser()
        if not path.is_absolute():
            candidate = self.config.documents_dir / path
            path = candidate if candidate.exists() else Path.cwd() / path
        if not path.exists() or not path.is_file():
            return ToolResult("read_document", False, f"Document not found: {path}")

        try:
            text = self._extract_text(path)
        except Exception as exc:
            return ToolResult("read_document", False, f"Could not read {path.name}: {exc}")

        clipped = text[:max_chars]
        summary = DocumentSummary(
            path=str(path),
            characters=len(text),
            preview=clipped,
        )
        return ToolResult(
            "read_document",
            True,
            f"Read {path.name} ({len(text)} characters).",
            summary.to_dict(),
        )

    def answer_question(self, path_text: str, question: str) -> ToolResult:
        document = self.read_document(path_text, max_chars=8000)
        if not document.ok:
            return document
        return ToolResult(
            "document_chat",
            True,
            "Document text is ready for the LLM context.",
            {
                "question": question,
                "document": document.data,
            },
        )

    @staticmethod
    def _extract_text(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".markdown"}:
            return path.read_text(encoding="utf-8", errors="replace")
        if suffix == ".pdf":
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix == ".docx":
            from docx import Document  # type: ignore

            document = Document(str(path))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        raise ValueError("Supported formats: PDF, DOCX, TXT, Markdown.")
