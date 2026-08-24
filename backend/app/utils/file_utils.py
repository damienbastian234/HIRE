"""Filesystem utilities for the H.I.R.E. Data Ingestion Pipeline.

This module provides low-level, reusable filesystem primitives used by the
data ingestion layer: naming, hashing, directory management, and safe file
persistence/cleanup.

This module MUST remain strictly filesystem-only. It intentionally does
NOT perform validation of file contents, does NOT parse CSV/Excel/PDF
data, does NOT clean or preprocess data, and does NOT contain any
business logic. Those responsibilities belong to the service and AI
layers that consume these utilities.

Typical usage example:

    company_dir = create_company_directory(base_dir, company_id="acme-corp")
    processing_dirs = create_processing_directory(company_dir)
    unique_name = generate_unique_filename("resume.pdf")
    saved_path = save_uploaded_file(
        content=file_bytes,
        destination_dir=processing_dirs["raw"],
        filename=unique_name,
    )
    file_hash = calculate_file_hash(saved_path)
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Default chunk size (in bytes) used when streaming files for hashing.
DEFAULT_HASH_CHUNK_SIZE: Final[int] = 65536  # 64 KB

#: Standard subdirectories created for every processing workspace.
PROCESSING_SUBDIRECTORIES: Final[tuple[str, ...]] = (
    "raw",
    "processed",
    "reports",
    "logs",
)


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class FileUtilsError(Exception):
    """Base exception for all errors raised by this module.

    Note:
        If/when the project introduces a shared ``app/core/exceptions.py``,
        this hierarchy should be relocated there so all layers share one
        exception taxonomy. It is defined locally here to keep this module
        self-contained until that shared module exists.
    """


class DirectoryCreationError(FileUtilsError):
    """Raised when a required directory cannot be created."""


class FileNotFoundInStorageError(FileUtilsError):
    """Raised when an operation targets a file that does not exist."""


class FileAlreadyExistsError(FileUtilsError):
    """Raised when an operation would overwrite an existing file."""


class FileDeletionError(FileUtilsError):
    """Raised when a file cannot be deleted."""


class FileHashingError(FileUtilsError):
    """Raised when a file's hash cannot be computed."""


class FileSaveError(FileUtilsError):
    """Raised when a file cannot be persisted to storage."""


# --------------------------------------------------------------------------- #
# Naming & Metadata Utilities
# --------------------------------------------------------------------------- #


def get_file_extension(filename: str | Path) -> str:
    """Return the lowercase extension of a filename, including the dot.

    Args:
        filename: A filename or path (e.g. ``"resume.PDF"``).

    Returns:
        The lowercase extension including the leading dot (e.g. ``".pdf"``).
        Returns an empty string if the file has no extension.

    Example:
        >>> get_file_extension("Resume.PDF")
        '.pdf'
    """
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """Generate a collision-resistant filename that preserves the extension.

    Args:
        original_filename: The original filename supplied by the client
            (e.g. ``"resume.pdf"``).

    Returns:
        A new filename of the form ``"<uuid4-hex>.<ext>"``. If the original
        filename has no extension, only the UUID is returned.

    Example:
        >>> generate_unique_filename("resume.pdf")
        'a3f1c9e2b1a94c9db6f0b0e7d6b8d1f4.pdf'
    """
    extension = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{extension}"


def get_file_size(file_path: str | Path) -> int:
    """Return the size of a file in bytes.

    Args:
        file_path: Path to the target file.

    Returns:
        File size in bytes.

    Raises:
        FileNotFoundInStorageError: If the file does not exist or is not
            a regular file.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundInStorageError(f"File not found: {path}")
    return path.stat().st_size


def calculate_file_hash(
    file_path: str | Path,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
) -> str:
    """Compute the SHA-256 hash of a file by streaming it in chunks.

    The file is never fully loaded into memory, making this safe for
    large uploads (e.g. multi-page resumes or bulk exports).

    Args:
        file_path: Path to the target file.
        chunk_size: Number of bytes to read per chunk. Defaults to 64 KB.

    Returns:
        The hexadecimal SHA-256 digest of the file contents.

    Raises:
        FileNotFoundInStorageError: If the file does not exist.
        FileHashingError: If the file cannot be read.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundInStorageError(f"File not found: {path}")

    sha256 = hashlib.sha256()
    try:
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(chunk_size), b""):
                sha256.update(chunk)
    except OSError as exc:
        raise FileHashingError(f"Failed to hash file {path}: {exc}") from exc

    return sha256.hexdigest()


def file_exists(file_path: str | Path) -> bool:
    """Check whether a path points to an existing regular file.

    Args:
        file_path: Path to check.

    Returns:
        True if the path exists and is a regular file, otherwise False.
    """
    return Path(file_path).is_file()


# --------------------------------------------------------------------------- #
# Directory Management
# --------------------------------------------------------------------------- #


def ensure_directory_exists(directory_path: str | Path) -> Path:
    """Ensure a directory exists, creating parent directories as needed.

    Idempotent: if the directory already exists, this is a no-op.

    Args:
        directory_path: Path to the directory to create.

    Returns:
        The resolved ``Path`` of the ensured directory.

    Raises:
        DirectoryCreationError: If the directory cannot be created (e.g.
            due to a permissions error or because the path collides with
            an existing non-directory file).
    """
    path = Path(directory_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise DirectoryCreationError(
            f"Failed to create directory {path}: {exc}"
        ) from exc
    return path


def create_company_directory(base_dir: str | Path, company_id: str) -> Path:
    """Create (or reuse) the root storage directory for a company.

    Args:
        base_dir: The base storage root (e.g. the configured uploads root).
        company_id: A stable, unique identifier for the company/tenant.

    Returns:
        Path to the company's root directory.

    Raises:
        DirectoryCreationError: If the directory cannot be created.
    """
    company_dir = Path(base_dir) / company_id
    return ensure_directory_exists(company_dir)


def create_processing_directory(company_dir: str | Path) -> dict[str, Path]:
    """Create the standard processing workspace beneath a company directory.

    Creates the following subdirectories: ``raw/``, ``processed/``,
    ``reports/``, ``logs/``.

    Args:
        company_dir: The company's root directory, as returned by
            :func:`create_company_directory`.

    Returns:
        A mapping of subdirectory name to its resolved ``Path``, e.g.
        ``{"raw": Path(...), "processed": Path(...), ...}``.

    Raises:
        DirectoryCreationError: If any subdirectory cannot be created.
    """
    base = Path(company_dir)
    return {
        name: ensure_directory_exists(base / name)
        for name in PROCESSING_SUBDIRECTORIES
    }


# --------------------------------------------------------------------------- #
# File Persistence
# --------------------------------------------------------------------------- #


def save_uploaded_file(
    content: bytes,
    destination_dir: str | Path,
    filename: str,
) -> Path:
    """Persist raw file content to disk without overwriting existing files.

    This function is intentionally framework-agnostic: it accepts raw
    bytes rather than a web-framework upload object, so the caller
    (typically a service layer) is responsible for reading the upload
    stream beforehand.

    Args:
        content: Raw file bytes to write.
        destination_dir: Directory in which to save the file. Created if
            it does not already exist.
        filename: Target filename (e.g. produced by
            :func:`generate_unique_filename`).

    Returns:
        The full path to the saved file.

    Raises:
        FileAlreadyExistsError: If a file already exists at the target
            path, to guarantee uploads are never silently overwritten.
        FileSaveError: If the file cannot be written to disk.
    """
    directory = ensure_directory_exists(destination_dir)
    target_path = directory / filename

    if target_path.exists():
        raise FileAlreadyExistsError(
            f"Refusing to overwrite existing file: {target_path}"
        )

    try:
        with target_path.open("wb") as file_handle:
            file_handle.write(content)
    except OSError as exc:
        raise FileSaveError(
            f"Failed to save file to {target_path}: {exc}"
        ) from exc

    return target_path


# --------------------------------------------------------------------------- #
# Deletion & Cleanup
# --------------------------------------------------------------------------- #


def delete_file(file_path: str | Path) -> None:
    """Delete a single file from disk.

    Args:
        file_path: Path to the file to delete.

    Raises:
        FileNotFoundInStorageError: If the file does not exist.
        FileDeletionError: If the file exists but cannot be deleted.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundInStorageError(f"File not found: {path}")

    try:
        path.unlink()
    except OSError as exc:
        raise FileDeletionError(f"Failed to delete file {path}: {exc}") from exc


def cleanup_directory(directory_path: str | Path, *, recreate: bool = True) -> None:
    """Remove all contents of a directory, optionally recreating it empty.

    Args:
        directory_path: Directory whose contents should be removed.
        recreate: If True (default), the directory itself is recreated
            empty after removal so callers can continue writing to it.
            If False, the directory is left deleted.

    Raises:
        FileNotFoundInStorageError: If the directory does not exist.
        DirectoryCreationError: If cleanup or recreation fails.
    """
    path = Path(directory_path)
    if not path.is_dir():
        raise FileNotFoundInStorageError(f"Directory not found: {path}")

    try:
        shutil.rmtree(path)
    except OSError as exc:
        raise DirectoryCreationError(
            f"Failed to clean up directory {path}: {exc}"
        ) from exc

    if recreate:
        ensure_directory_exists(path)


def cleanup_temp_files(
    directory_path: str | Path,
    max_age_hours: float = 24.0,
) -> list[Path]:
    """Delete files in a directory older than a given age threshold.

    Intended for periodic cleanup of scratch/temp workspaces (e.g. a
    ``raw/`` staging directory). Only regular files are considered;
    subdirectories are left untouched.

    Args:
        directory_path: Directory to scan for stale files.
        max_age_hours: Maximum file age, in hours, before deletion.
            Defaults to 24 hours.

    Returns:
        A list of paths that were deleted.

    Raises:
        FileNotFoundInStorageError: If the directory does not exist.
        FileDeletionError: If a stale file is found but cannot be deleted.
    """
    path = Path(directory_path)
    if not path.is_dir():
        raise FileNotFoundInStorageError(f"Directory not found: {path}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    deleted_files: list[Path] = []

    for entry in path.iterdir():
        if not entry.is_file():
            continue

        modified_at = datetime.fromtimestamp(
            entry.stat().st_mtime, tz=timezone.utc
        )
        if modified_at < cutoff:
            try:
                entry.unlink()
            except OSError as exc:
                raise FileDeletionError(
                    f"Failed to delete stale file {entry}: {exc}"
                ) from exc
            deleted_files.append(entry)

    return deleted_files