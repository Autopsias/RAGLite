"""Base64 content handling for temporary files.

Handles decoding base64 content and creating temporary files with cleanup.
"""

from __future__ import annotations

import base64
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from raglite.shared.logging import get_logger

from ..constants import MAX_BASE64_CONTENT_SIZE_BYTES, SUPPORTED_EXTENSIONS

logger = get_logger(__name__)


@contextmanager
def temp_file_from_base64(content_b64: str, filename: str) -> Generator[str, None, None]:
    """Create temporary file from base64 content with automatic cleanup.

    Story 4.0.7 AC3/AC4: Context manager for safe temporary file handling.
    Decodes base64 content, writes to temp file, and ensures cleanup on exit.

    Args:
        content_b64: Base64-encoded file content (max 25MB encoded).
        filename: Original filename with extension (e.g., "report.pdf").
                  Used for extension detection and validation.

    Yields:
        str: Absolute path to temporary file with correct extension.

    Raises:
        ValueError: If base64 content is invalid, extension unsupported,
                    or size exceeds 25MB limit.

    Example:
        >>> with temp_file_from_base64(pdf_b64, "report.pdf") as tmp_path:
        ...     metadata = await ingest_document(tmp_path)
        >>> # tmp_path is automatically deleted after context exits
    """
    # AC5: Size check (before decoding to fail fast)
    if len(content_b64) > MAX_BASE64_CONTENT_SIZE_BYTES:
        size_mb = len(content_b64) / (1024 * 1024)
        raise ValueError(
            f"File content ({size_mb:.1f}MB encoded) exceeds 25MB limit. "
            "For larger files, save to filesystem and use doc_path parameter."
        )

    # AC3: Decode base64
    try:
        file_bytes = base64.b64decode(content_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {e}") from e

    # AC6: Extension validation
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type: {suffix}. Supported extensions: {supported}")

    # Create temp file with correct extension (required for format detection)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        logger.info(
            "Created temp file from base64 content",
            extra={
                "original_filename": filename,
                "extension": suffix,
                "size_bytes": len(file_bytes),
                "temp_path": tmp_path,
            },
        )

        yield tmp_path

    finally:
        # AC4: Guaranteed cleanup on success or failure
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug(
                    "Cleaned up temp file",
                    extra={"temp_path": tmp_path},
                )
            except Exception as e:
                logger.warning(
                    "Failed to clean up temp file",
                    extra={"temp_path": tmp_path, "error": str(e)},
                )


__all__ = ["temp_file_from_base64"]
