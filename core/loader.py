import os
from pathlib import Path
from typing import List, Dict

import PyPDF2


class NotesLoader:
    """
    Loads study notes from a folder.
    Supports:
      - .txt, .md
      - .pdf (text extraction)
    """

    TEXT_EXTENSIONS = {".txt", ".md"}

    def load_notes_from_folder(self, folder: str) -> List[Dict[str, str]]:
        """
        Returns a list of dicts with:
          - 'name': file name
          - 'path': full path
          - 'content': extracted text
        """
        notes = []
        root = Path(folder).expanduser()

        if not root.exists():
            raise FileNotFoundError(f"Notes folder not found: {folder}")

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            ext = path.suffix.lower()
            content = ""

            if ext in self.TEXT_EXTENSIONS:
                content = self._read_text(path)
            elif ext == ".pdf":
                content = self._read_pdf(path)

            if content.strip():
                notes.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "content": content,
                    }
                )

        return notes

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _read_pdf(self, path: Path) -> str:
        text = ""
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
        except Exception:
            return text
        return text
