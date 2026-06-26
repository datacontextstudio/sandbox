import logging
from pathlib import Path

from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)

_converter = DocumentConverter()


def parse_document(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    logger.info("Parsing %s", path.name)
    result = _converter.convert(str(path))
    text = result.document.export_to_markdown()
    logger.info("Parsed %s → %d chars", path.name, len(text))
    return text
