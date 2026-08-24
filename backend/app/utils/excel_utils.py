"""Excel parsing and metadata utilities for the H.I.R.E. Data Ingestion Pipeline.

This module provides low-level, reusable primitives for reading Excel
workbooks (from file paths and in-memory bytes) and extracting structural
metadata (sheet names, headers, row/column counts, etc.), mirroring the
architecture and conventions of ``csv_utils.py``.

This module MUST remain strictly parsing/metadata-only. It intentionally
does NOT validate data, does NOT clean or normalize values, does NOT infer
column types or business meaning, does NOT handle file uploads, and does
NOT contain any business logic. Those responsibilities belong to the
validation and processing layers that consume this module's output.

All reads use pandas with the ``openpyxl`` engine, and every DataFrame-
returning function returns raw ``pd.DataFrame`` objects exactly as parsed.

Typical usage example:

    sheets = list_sheet_names(xlsx_path)
    metadata = get_excel_metadata(xlsx_path)
    preview = preview_excel(xlsx_path, sheet_name=sheets[0])
    df = read_excel_sheet(xlsx_path, sheet_name=sheets[0])
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.constants import (
    DEFAULT_EXCEL_ENGINE,
    DEFAULT_PREVIEW_ROWS,
    DEFAULT_SHEET_INDEX,
    MAX_PREVIEW_ROWS,
)


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class ExcelUtilsError(Exception):
    """Base exception for all errors raised by this module.

    Note:
        This mirrors the local-exception pattern used in
        ``file_utils.py`` and ``csv_utils.py``. If/when the project
        introduces a shared ``app/core/exceptions.py``, this hierarchy
        should be relocated there so all layers share one exception
        taxonomy.
    """


class ExcelFileNotFoundError(ExcelUtilsError):
    """Raised when a target Excel file does not exist on disk."""


class ExcelReadError(ExcelUtilsError):
    """Raised when an Excel file or byte stream cannot be parsed."""


class ExcelSheetNotFoundError(ExcelUtilsError):
    """Raised when a requested sheet name does not exist in the workbook."""


class ExcelEmptyError(ExcelUtilsError):
    """Raised when a workbook or sheet contains no usable content."""


# --------------------------------------------------------------------------- #
# Internal Helpers
# --------------------------------------------------------------------------- #


def _open_excel_file(source: str | Path | io.BytesIO) -> pd.ExcelFile:
    """Open a pandas ``ExcelFile`` handle for a path or in-memory buffer.

    Centralizes engine selection and error translation so every public
    function raises the same exception types regardless of source type.

    Args:
        source: A file path, ``Path``, or ``io.BytesIO`` buffer containing
            an Excel workbook.

    Returns:
        An open ``pd.ExcelFile`` handle.

    Raises:
        ExcelReadError: If the workbook cannot be opened or parsed.
    """
    try:
        return pd.ExcelFile(source, engine=DEFAULT_EXCEL_ENGINE)
    except (ValueError, OSError) as exc:
        raise ExcelReadError(f"Failed to open Excel workbook: {exc}") from exc


def _resolve_sheet_name(excel_file: pd.ExcelFile, sheet_name: str) -> None:
    """Validate that a sheet name exists in an already-open workbook.

    Args:
        excel_file: An open ``pd.ExcelFile`` handle.
        sheet_name: The sheet name to validate.

    Raises:
        ExcelSheetNotFoundError: If ``sheet_name`` is not present in the
            workbook.
    """
    if sheet_name not in excel_file.sheet_names:
        raise ExcelSheetNotFoundError(
            f"Sheet '{sheet_name}' not found. "
            f"Available sheets: {', '.join(excel_file.sheet_names)}"
        )


# --------------------------------------------------------------------------- #
# Sheet Discovery
# --------------------------------------------------------------------------- #


def list_sheet_names(file_path: str | Path) -> list[str]:
    """List the names of all sheets in an Excel workbook.

    Args:
        file_path: Path to the Excel workbook.

    Returns:
        Sheet names in the order they appear in the workbook.

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelReadError: If the workbook cannot be opened or parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ExcelFileNotFoundError(f"Excel file not found: {path}")

    excel_file = _open_excel_file(path)
    try:
        return list(excel_file.sheet_names)
    finally:
        excel_file.close()


def sheet_exists(file_path: str | Path, sheet_name: str) -> bool:
    """Check whether a named sheet exists in an Excel workbook.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: The sheet name to check for.

    Returns:
        True if the sheet exists, otherwise False.

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelReadError: If the workbook cannot be opened or parsed.
    """
    return sheet_name in list_sheet_names(file_path)


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def read_excel_sheet(
    file_path: str | Path,
    sheet_name: str,
) -> pd.DataFrame:
    """Read a specific named sheet from an Excel workbook into a DataFrame.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: Name of the sheet to read.

    Returns:
        A ``pd.DataFrame`` containing the sheet's raw contents.

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelSheetNotFoundError: If ``sheet_name`` is not present in the
            workbook.
        ExcelReadError: If the sheet cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ExcelFileNotFoundError(f"Excel file not found: {path}")

    excel_file = _open_excel_file(path)
    try:
        _resolve_sheet_name(excel_file, sheet_name)
        try:
            return excel_file.parse(sheet_name=sheet_name)
        except (ValueError, pd.errors.ParserError) as exc:
            raise ExcelReadError(
                f"Failed to parse sheet '{sheet_name}' in {path}: {exc}"
            ) from exc
    finally:
        excel_file.close()


def read_first_sheet(file_path: str | Path) -> pd.DataFrame:
    """Read the first sheet of an Excel workbook into a DataFrame.

    Args:
        file_path: Path to the Excel workbook.

    Returns:
        A ``pd.DataFrame`` containing the first sheet's raw contents.

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelEmptyError: If the workbook contains no sheets.
        ExcelReadError: If the sheet cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ExcelFileNotFoundError(f"Excel file not found: {path}")

    excel_file = _open_excel_file(path)
    try:
        if not excel_file.sheet_names:
            raise ExcelEmptyError(f"Workbook has no sheets: {path}")
        try:
            return excel_file.parse(sheet_name=DEFAULT_SHEET_INDEX)
        except (ValueError, pd.errors.ParserError) as exc:
            raise ExcelReadError(
                f"Failed to parse first sheet in {path}: {exc}"
            ) from exc
    finally:
        excel_file.close()


def read_excel_file(
    file_path: str | Path,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Read a sheet from an Excel workbook on disk into a DataFrame.

    Convenience wrapper that reads a named sheet if ``sheet_name`` is
    given, otherwise falls back to the first sheet in the workbook.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: Name of the sheet to read. If omitted, the first
            sheet is read.

    Returns:
        A ``pd.DataFrame`` containing the sheet's raw contents.

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelSheetNotFoundError: If ``sheet_name`` is given but not
            present in the workbook.
        ExcelEmptyError: If the workbook contains no sheets.
        ExcelReadError: If the sheet cannot be parsed.
    """
    if sheet_name is None:
        return read_first_sheet(file_path)
    return read_excel_sheet(file_path, sheet_name)


def read_excel_bytes(
    content: bytes,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Parse Excel content held in memory (e.g. an in-flight upload).

    Args:
        content: Raw Excel workbook bytes (.xlsx/.xlsm).
        sheet_name: Name of the sheet to read. If omitted, the first
            sheet is read.

    Returns:
        A ``pd.DataFrame`` containing the sheet's raw contents.

    Raises:
        ExcelSheetNotFoundError: If ``sheet_name`` is given but not
            present in the workbook.
        ExcelEmptyError: If the workbook contains no sheets.
        ExcelReadError: If the content cannot be parsed as an Excel
            workbook.
    """
    buffer = io.BytesIO(content)
    excel_file = _open_excel_file(buffer)
    try:
        if not excel_file.sheet_names:
            raise ExcelEmptyError("Workbook content has no sheets.")

        target_sheet: str | int = sheet_name if sheet_name is not None else DEFAULT_SHEET_INDEX
        if sheet_name is not None:
            _resolve_sheet_name(excel_file, sheet_name)

        try:
            return excel_file.parse(sheet_name=target_sheet)
        except (ValueError, pd.errors.ParserError) as exc:
            raise ExcelReadError(f"Failed to parse Excel content: {exc}") from exc
    finally:
        excel_file.close()


# --------------------------------------------------------------------------- #
# Preview & Metadata
# --------------------------------------------------------------------------- #


def preview_excel(
    file_path: str | Path,
    sheet_name: str | None = None,
    num_rows: int = DEFAULT_PREVIEW_ROWS,
) -> dict[str, Any]:
    """Return a lightweight preview of an Excel sheet's headers and rows.

    Intended for quick inspection (e.g. a UI preview before ingestion).
    The full sheet is parsed by pandas (Excel has no native streaming
    row API), but only the requested number of rows are included in the
    returned preview payload.

    Args:
        file_path: Path to the Excel workbook.
        sheet_name: Name of the sheet to preview. If omitted, the first
            sheet is used.
        num_rows: Number of data rows to include in the preview. Clamped
            to ``MAX_PREVIEW_ROWS``. Defaults to ``DEFAULT_PREVIEW_ROWS``.

    Returns:
        A dictionary with the shape::

            {
                "sheet_name": "Sheet1",
                "headers": ["col_a", "col_b"],
                "rows": [{"col_a": 1, "col_b": "x"}, ...],
                "row_count_previewed": 5,
            }

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelSheetNotFoundError: If ``sheet_name`` is given but not
            present in the workbook.
        ExcelEmptyError: If the workbook contains no sheets.
        ExcelReadError: If the sheet cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ExcelFileNotFoundError(f"Excel file not found: {path}")

    capped_rows = max(0, min(num_rows, MAX_PREVIEW_ROWS))

    excel_file = _open_excel_file(path)
    try:
        if not excel_file.sheet_names:
            raise ExcelEmptyError(f"Workbook has no sheets: {path}")

        resolved_sheet_name: str
        if sheet_name is not None:
            _resolve_sheet_name(excel_file, sheet_name)
            resolved_sheet_name = sheet_name
        else:
            resolved_sheet_name = excel_file.sheet_names[DEFAULT_SHEET_INDEX]

        try:
            dataframe = excel_file.parse(sheet_name=resolved_sheet_name, nrows=capped_rows)
        except (ValueError, pd.errors.ParserError) as exc:
            raise ExcelReadError(
                f"Failed to preview sheet '{resolved_sheet_name}' in {path}: {exc}"
            ) from exc
    finally:
        excel_file.close()

    return {
        "sheet_name": resolved_sheet_name,
        "headers": list(dataframe.columns.astype(str)),
        "rows": dataframe.to_dict(orient="records"),
        "row_count_previewed": len(dataframe),
    }


def get_excel_metadata(file_path: str | Path) -> dict[str, Any]:
    """Extract structural metadata about an Excel workbook.

    Reports metadata for every sheet in the workbook, plus file-level
    information. Row counts require a full parse of each sheet, since
    Excel workbooks (unlike CSVs) have no cheap streaming row count.

    Args:
        file_path: Path to the Excel workbook.

    Returns:
        A dictionary with the shape::

            {
                "file_name": "candidates.xlsx",
                "file_size_bytes": 20480,
                "sheet_names": ["Sheet1", "Sheet2"],
                "sheet_count": 2,
                "sheets": {
                    "Sheet1": {
                        "headers": ["col_a", "col_b"],
                        "column_count": 2,
                        "row_count": 150,
                    },
                    ...
                },
            }

    Raises:
        ExcelFileNotFoundError: If the file does not exist.
        ExcelEmptyError: If the workbook contains no sheets.
        ExcelReadError: If any sheet cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ExcelFileNotFoundError(f"Excel file not found: {path}")

    excel_file = _open_excel_file(path)
    try:
        sheet_names = list(excel_file.sheet_names)
        if not sheet_names:
            raise ExcelEmptyError(f"Workbook has no sheets: {path}")

        sheets_metadata: dict[str, dict[str, Any]] = {}
        for name in sheet_names:
            try:
                dataframe = excel_file.parse(sheet_name=name)
            except (ValueError, pd.errors.ParserError) as exc:
                raise ExcelReadError(
                    f"Failed to parse sheet '{name}' in {path}: {exc}"
                ) from exc

            sheets_metadata[name] = {
                "headers": list(dataframe.columns.astype(str)),
                "column_count": len(dataframe.columns),
                "row_count": len(dataframe),
            }
    finally:
        excel_file.close()

    return {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "sheet_names": sheet_names,
        "sheet_count": len(sheet_names),
        "sheets": sheets_metadata,
    }