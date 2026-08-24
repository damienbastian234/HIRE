"""CSV parsing and metadata utilities for the H.I.R.E. Data Ingestion Pipeline.

This module provides low-level, reusable primitives for reading CSV files
and bytes streams and extracting structural metadata (headers, row counts,
delimiter, encoding, etc.).

This module MUST remain strictly parsing/metadata-only. It intentionally
does NOT validate data, does NOT clean or normalize values, does NOT infer
column types or business meaning, and does NOT contain any business logic.
Those responsibilities belong to the validation and processing layers that
consume this module's output.

Typical usage example:

    encoding = detect_csv_encoding(csv_path)
    metadata = get_csv_metadata(csv_path)
    preview = preview_csv(csv_path, num_rows=5)
    rows = read_csv_file(csv_path)
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Final

from app.utils.constants import (
    CSV_DETECTION_SAMPLE_SIZE,
    DEFAULT_CSV_DELIMITER,
    DEFAULT_CSV_ENCODING,
    DEFAULT_PREVIEW_ROWS,
    MAX_PREVIEW_ROWS,
    SUPPORTED_CSV_DELIMITERS,
    SUPPORTED_CSV_ENCODINGS,
)

#: Candidate delimiters passed to csv.Sniffer, as a single string.
_SNIFFER_DELIMITERS: Final[str] = "".join(SUPPORTED_CSV_DELIMITERS)


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class CsvUtilsError(Exception):
    """Base exception for all errors raised by this module.

    Note:
        This mirrors the local-exception pattern used in
        ``file_utils.py``. If/when the project introduces a shared
        ``app/core/exceptions.py``, this hierarchy should be relocated
        there so all layers share one exception taxonomy.
    """


class CsvFileNotFoundError(CsvUtilsError):
    """Raised when a target CSV file does not exist on disk."""


class CsvEncodingDetectionError(CsvUtilsError):
    """Raised when no supported encoding can successfully decode a file."""


class CsvReadError(CsvUtilsError):
    """Raised when a CSV file or byte stream cannot be parsed."""


class CsvEmptyError(CsvUtilsError):
    """Raised when a CSV source contains no header row / no content."""


# --------------------------------------------------------------------------- #
# Encoding & Dialect Detection
# --------------------------------------------------------------------------- #


def detect_csv_encoding(
    file_path: str | Path,
    sample_size: int = CSV_DETECTION_SAMPLE_SIZE,
) -> str:
    """Detect the character encoding of a CSV file.

    Attempts each encoding in ``SUPPORTED_CSV_ENCODINGS`` (in order)
    against a sample of the file, returning the first encoding that
    decodes the sample without error.

    Args:
        file_path: Path to the CSV file.
        sample_size: Number of bytes to sample from the start of the file
            for detection. Defaults to ``CSV_DETECTION_SAMPLE_SIZE``.

    Returns:
        The name of the detected encoding (e.g. ``"utf-8"``).

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        CsvEncodingDetectionError: If none of the supported encodings can
            decode the sampled content.
    """
    path = Path(file_path)
    if not path.is_file():
        raise CsvFileNotFoundError(f"CSV file not found: {path}")

    try:
        with path.open("rb") as file_handle:
            sample = file_handle.read(sample_size)
    except OSError as exc:
        raise CsvReadError(f"Failed to read file {path}: {exc}") from exc

    for encoding in SUPPORTED_CSV_ENCODINGS:
        try:
            sample.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    raise CsvEncodingDetectionError(
        f"Unable to detect a supported encoding for {path}. "
        f"Tried: {', '.join(SUPPORTED_CSV_ENCODINGS)}"
    )


def _detect_delimiter(sample_text: str) -> str:
    """Detect the most likely delimiter from a sample of CSV text.

    Falls back to ``DEFAULT_CSV_DELIMITER`` if detection is inconclusive,
    rather than raising, since delimiter detection is inherently a
    best-effort heuristic.

    Args:
        sample_text: A decoded text sample from the start of a CSV source.

    Returns:
        The detected delimiter character.
    """
    if not sample_text.strip():
        return DEFAULT_CSV_DELIMITER

    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=_SNIFFER_DELIMITERS)
        if dialect.delimiter in SUPPORTED_CSV_DELIMITERS:
            return dialect.delimiter
    except csv.Error:
        pass

    return DEFAULT_CSV_DELIMITER


def detect_csv_delimiter(
    file_path: str | Path,
    encoding: str | None = None,
    sample_size: int = CSV_DETECTION_SAMPLE_SIZE,
) -> str:
    """Detect the delimiter used by a CSV file.

    Args:
        file_path: Path to the CSV file.
        encoding: Encoding to use when sampling the file. If omitted, it
            is auto-detected via :func:`detect_csv_encoding`.
        sample_size: Number of bytes to sample for detection.

    Returns:
        The detected delimiter character (falls back to
        ``DEFAULT_CSV_DELIMITER`` if detection is inconclusive).

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        CsvEncodingDetectionError: If encoding auto-detection fails.
        CsvReadError: If the file cannot be read.
    """
    path = Path(file_path)
    if not path.is_file():
        raise CsvFileNotFoundError(f"CSV file not found: {path}")

    resolved_encoding = encoding or detect_csv_encoding(path, sample_size)

    try:
        with path.open("rb") as file_handle:
            raw_sample = file_handle.read(sample_size)
    except OSError as exc:
        raise CsvReadError(f"Failed to read file {path}: {exc}") from exc

    sample_text = raw_sample.decode(resolved_encoding, errors="ignore")
    return _detect_delimiter(sample_text)


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def read_csv_file(
    file_path: str | Path,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> list[dict[str, Any]]:
    """Read a CSV file from disk into a list of row dictionaries.

    Rows are parsed as-is (no cleaning, casting, or validation). Keys are
    taken verbatim from the header row.

    Args:
        file_path: Path to the CSV file.
        encoding: Encoding to use. If omitted, it is auto-detected via
            :func:`detect_csv_encoding`.
        delimiter: Field delimiter to use. If omitted, it is auto-detected
            via :func:`detect_csv_delimiter`.

    Returns:
        A list of dictionaries, one per data row, mapping header names to
        raw string values.

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        CsvEncodingDetectionError: If encoding auto-detection fails.
        CsvEmptyError: If the file has no header row.
        CsvReadError: If the file cannot be parsed as CSV.
    """
    path = Path(file_path)
    if not path.is_file():
        raise CsvFileNotFoundError(f"CSV file not found: {path}")

    resolved_encoding = encoding or detect_csv_encoding(path)
    resolved_delimiter = delimiter or detect_csv_delimiter(
        path, encoding=resolved_encoding
    )

    try:
        with path.open("r", newline="", encoding=resolved_encoding) as file_handle:
            reader = csv.DictReader(file_handle, delimiter=resolved_delimiter)
            if reader.fieldnames is None:
                raise CsvEmptyError(f"CSV file has no header row: {path}")
            return [dict(row) for row in reader]
    except CsvEmptyError:
        raise
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        raise CsvReadError(f"Failed to parse CSV file {path}: {exc}") from exc


def read_csv_bytes(
    content: bytes,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> list[dict[str, Any]]:
    """Parse CSV content held in memory (e.g. an in-flight upload).

    Args:
        content: Raw CSV bytes.
        encoding: Encoding to use. If omitted, each encoding in
            ``SUPPORTED_CSV_ENCODINGS`` is attempted in order.
        delimiter: Field delimiter to use. If omitted, it is auto-detected
            from the decoded content.

    Returns:
        A list of dictionaries, one per data row, mapping header names to
        raw string values.

    Raises:
        CsvEncodingDetectionError: If no supported encoding can decode
            the content.
        CsvEmptyError: If the content has no header row.
        CsvReadError: If the content cannot be parsed as CSV.
    """
    resolved_encoding, decoded_text = _decode_bytes(content, encoding)
    resolved_delimiter = delimiter or _detect_delimiter(
        decoded_text[:CSV_DETECTION_SAMPLE_SIZE]
    )

    try:
        buffer = io.StringIO(decoded_text)
        reader = csv.DictReader(buffer, delimiter=resolved_delimiter)
        if reader.fieldnames is None:
            raise CsvEmptyError("CSV content has no header row.")
        return [dict(row) for row in reader]
    except CsvEmptyError:
        raise
    except csv.Error as exc:
        raise CsvReadError(f"Failed to parse CSV content: {exc}") from exc


def _decode_bytes(
    content: bytes,
    encoding: str | None,
) -> tuple[str, str]:
    """Decode raw bytes using a given or auto-detected encoding.

    Args:
        content: Raw bytes to decode.
        encoding: Encoding to use, or None to attempt auto-detection.

    Returns:
        A tuple of ``(encoding_used, decoded_text)``.

    Raises:
        CsvEncodingDetectionError: If no supported encoding succeeds.
    """
    if encoding:
        try:
            return encoding, content.decode(encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            raise CsvEncodingDetectionError(
                f"Failed to decode content using encoding '{encoding}': {exc}"
            ) from exc

    for candidate in SUPPORTED_CSV_ENCODINGS:
        try:
            return candidate, content.decode(candidate)
        except (UnicodeDecodeError, LookupError):
            continue

    raise CsvEncodingDetectionError(
        f"Unable to decode content using any supported encoding: "
        f"{', '.join(SUPPORTED_CSV_ENCODINGS)}"
    )


# --------------------------------------------------------------------------- #
# Preview & Metadata
# --------------------------------------------------------------------------- #


def preview_csv(
    file_path: str | Path,
    num_rows: int = DEFAULT_PREVIEW_ROWS,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> dict[str, Any]:
    """Return a lightweight preview of a CSV file's headers and first rows.

    Intended for quick inspection (e.g. a UI preview before ingestion)
    without reading the entire file into memory.

    Args:
        file_path: Path to the CSV file.
        num_rows: Number of data rows to include in the preview. Clamped
            to ``MAX_PREVIEW_ROWS``. Defaults to ``DEFAULT_PREVIEW_ROWS``.
        encoding: Encoding to use. If omitted, it is auto-detected.
        delimiter: Field delimiter to use. If omitted, it is auto-detected.

    Returns:
        A dictionary with the shape::

            {
                "headers": ["col_a", "col_b"],
                "rows": [{"col_a": "1", "col_b": "x"}, ...],
                "row_count_previewed": 5,
            }

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        CsvEncodingDetectionError: If encoding auto-detection fails.
        CsvEmptyError: If the file has no header row.
        CsvReadError: If the file cannot be parsed as CSV.
    """
    path = Path(file_path)
    if not path.is_file():
        raise CsvFileNotFoundError(f"CSV file not found: {path}")

    capped_rows = max(0, min(num_rows, MAX_PREVIEW_ROWS))
    resolved_encoding = encoding or detect_csv_encoding(path)
    resolved_delimiter = delimiter or detect_csv_delimiter(
        path, encoding=resolved_encoding
    )

    try:
        with path.open("r", newline="", encoding=resolved_encoding) as file_handle:
            reader = csv.DictReader(file_handle, delimiter=resolved_delimiter)
            if reader.fieldnames is None:
                raise CsvEmptyError(f"CSV file has no header row: {path}")

            headers = list(reader.fieldnames)
            preview_rows: list[dict[str, Any]] = []
            for row in reader:
                if len(preview_rows) >= capped_rows:
                    break
                preview_rows.append(dict(row))
    except CsvEmptyError:
        raise
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        raise CsvReadError(f"Failed to preview CSV file {path}: {exc}") from exc

    return {
        "headers": headers,
        "rows": preview_rows,
        "row_count_previewed": len(preview_rows),
    }


def get_csv_metadata(
    file_path: str | Path,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> dict[str, Any]:
    """Extract structural metadata about a CSV file.

    Performs a single streaming pass over the file to count rows without
    loading all rows into memory.

    Args:
        file_path: Path to the CSV file.
        encoding: Encoding to use. If omitted, it is auto-detected.
        delimiter: Field delimiter to use. If omitted, it is auto-detected.

    Returns:
        A dictionary with the shape::

            {
                "file_name": "candidates.csv",
                "file_size_bytes": 20480,
                "encoding": "utf-8",
                "delimiter": ",",
                "headers": ["col_a", "col_b"],
                "column_count": 2,
                "row_count": 150,
            }

    Raises:
        CsvFileNotFoundError: If the file does not exist.
        CsvEncodingDetectionError: If encoding auto-detection fails.
        CsvEmptyError: If the file has no header row.
        CsvReadError: If the file cannot be parsed as CSV.
    """
    path = Path(file_path)
    if not path.is_file():
        raise CsvFileNotFoundError(f"CSV file not found: {path}")

    resolved_encoding = encoding or detect_csv_encoding(path)
    resolved_delimiter = delimiter or detect_csv_delimiter(
        path, encoding=resolved_encoding
    )

    try:
        with path.open("r", newline="", encoding=resolved_encoding) as file_handle:
            reader = csv.DictReader(file_handle, delimiter=resolved_delimiter)
            if reader.fieldnames is None:
                raise CsvEmptyError(f"CSV file has no header row: {path}")

            headers = list(reader.fieldnames)
            row_count = sum(1 for _ in reader)
    except CsvEmptyError:
        raise
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        raise CsvReadError(
            f"Failed to extract metadata from CSV file {path}: {exc}"
        ) from exc

    return {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "encoding": resolved_encoding,
        "delimiter": resolved_delimiter,
        "headers": headers,
        "column_count": len(headers),
        "row_count": row_count,
    }