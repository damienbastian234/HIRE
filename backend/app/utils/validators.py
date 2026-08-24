"""
validators.py

Reusable validation utilities for the Data Ingestion Pipeline.

This module provides stateless, composable validation functions used to
verify uploaded files and their parsed contents before they are handed
off to cleaning, normalization, or analysis stages.

Design notes:
    - File-level validators (extension, size, MIME type, filename) act as
      hard gates and raise ``FileValidationError`` on failure, since an
      invalid file must stop the pipeline immediately.
    - Content-level validators (DataFrame shape, headers, data quality)
      return a ``ValidationResult`` instead of raising, so that multiple
      checks can be run together and aggregated into a single report via
      ``validate_dataframe``.

This module MUST NOT:
    - Read or write files.
    - Clean, transform, or mutate data.
    - Contain business/orchestration logic.

It contains ONLY validation checks.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, FrozenSet, Literal, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from app.utils import constants as const


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ValidationError(Exception):
    """Base exception for all validation failures in the ingestion pipeline."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        """Initialize the validation error.

        Args:
            message: Human-readable description of the validation failure.
            code: Machine-readable error code for API responses/logging.
        """
        super().__init__(message)
        self.message = message
        self.code = code


class FileValidationError(ValidationError):
    """Raised when a file fails a file-level validation gate."""


# =============================================================================
# RESULT TYPES
# =============================================================================


@dataclass(frozen=True)
class ValidationResult:
    """Structured result of a single validation check.

    Attributes:
        is_valid: Whether the check passed.
        code: Machine-readable identifier for the check.
        message: Human-readable message describing the outcome. Empty
            string when the check passed.
        details: Optional structured context about the failure
            (e.g. affected column names, counts).
        severity: Indicates how blocking the result is. One of
            ``"info"``, ``"warning"``, or ``"error"``. Defaults to
            ``"error"`` so existing callers that ignore this field keep
            their current blocking behavior.
    """

    is_valid: bool
    code: str
    message: str = ""
    details: Optional[Mapping[str, Any]] = None
    severity: Literal["info", "warning", "error"] = "error"


@dataclass(frozen=True)
class ValidationSummary:
    """Aggregated outcome of running multiple validation checks.

    Attributes:
        is_valid: True only if every check in ``results`` passed.
        results: All validation results, both passed and failed.
    """

    is_valid: bool
    results: Sequence[ValidationResult] = field(default_factory=tuple)

    @property
    def errors(self) -> Sequence[ValidationResult]:
        """Return only the failed validation results."""
        return tuple(result for result in self.results if not result.is_valid)


# =============================================================================
# FILE VALIDATION
# =============================================================================


def validate_file_extension(filename: str) -> None:
    """Validate that a filename has an allowed upload extension.

    Args:
        filename: Name of the uploaded file, including its extension.

    Raises:
        FileValidationError: If the extension is missing or not present
            in ``constants.ALLOWED_UPLOAD_EXTENSIONS``.
    """
    extension = Path(filename).suffix.lower()
    if extension not in const.ALLOWED_UPLOAD_EXTENSIONS:
        raise FileValidationError(
            const.ERROR_UNSUPPORTED_FILE_EXTENSION,
            code=const.VALIDATION_CODE_UNSUPPORTED_FILE_EXTENSION,
        )


def validate_file_size(size_bytes: int) -> None:
    """Validate that a file size is within allowed bounds.

    Args:
        size_bytes: Size of the uploaded file, in bytes.

    Raises:
        FileValidationError: If the file is empty or exceeds
            ``constants.MAX_UPLOAD_SIZE_BYTES``.
    """
    if size_bytes <= 0:
        raise FileValidationError(
            const.ERROR_EMPTY_FILE,
            code=const.VALIDATION_CODE_EMPTY_FILE,
        )

    if size_bytes > const.MAX_UPLOAD_SIZE_BYTES:
        raise FileValidationError(
            const.ERROR_FILE_TOO_LARGE,
            code=const.VALIDATION_CODE_FILE_TOO_LARGE,
        )


def validate_mime_type(mime_type: str) -> None:
    """Validate that a MIME type is supported for ingestion.

    Args:
        mime_type: MIME type reported for the uploaded file.

    Raises:
        FileValidationError: If the MIME type is not present in
            ``constants.SUPPORTED_MIME_TYPES``.
    """
    if mime_type not in const.SUPPORTED_MIME_TYPES:
        raise FileValidationError(
            const.ERROR_UNSUPPORTED_MIME_TYPE,
            code=const.VALIDATION_CODE_UNSUPPORTED_MIME_TYPE,
        )


def validate_filename(filename: str) -> None:
    """Validate that a filename is safe and well-formed.

    Args:
        filename: Name of the uploaded file.

    Raises:
        FileValidationError: If the filename is empty, whitespace-only,
            or contains path traversal sequences.
    """
    if not filename or not filename.strip():
        raise FileValidationError(
            "Filename must not be empty.",
            code=const.VALIDATION_CODE_EMPTY_FILENAME,
        )

    path_parts = Path(filename).parts
    if ".." in path_parts or filename.strip() in {".", ".."}:
        raise FileValidationError(
            "Filename must not contain path traversal sequences.",
            code=const.VALIDATION_CODE_INVALID_FILENAME,
        )


def validate_encoding(
    encoding: str,
    supported_encodings: FrozenSet[str] = const.SUPPORTED_ENCODINGS,
) -> None:
    """Validate that a text encoding is supported for ingestion.

    Args:
        encoding: Encoding name reported for the uploaded file
            (e.g. ``"utf-8"``, ``"latin-1"``). Comparison is
            case-insensitive.
        supported_encodings: Configurable set of allowed encoding names.
            Defaults to ``constants.SUPPORTED_ENCODINGS``.

    Raises:
        FileValidationError: If ``encoding`` is empty or not present in
            ``supported_encodings``.
    """
    normalized_encoding = encoding.strip().lower() if encoding else ""
    allowed_encodings = {value.lower() for value in supported_encodings}

    if not normalized_encoding or normalized_encoding not in allowed_encodings:
        raise FileValidationError(
            const.ERROR_INVALID_ENCODING,
            code=const.VALIDATION_CODE_INVALID_ENCODING,
        )


def validate_sheet_exists(
    sheet_name: str,
    available_sheets: Sequence[str],
) -> None:
    """Validate that a requested Excel sheet exists in the workbook.

    Args:
        sheet_name: Name of the sheet requested for parsing.
        available_sheets: Sheet names actually present in the workbook.

    Raises:
        FileValidationError: If ``sheet_name`` is not present in
            ``available_sheets``.
    """
    if sheet_name not in available_sheets:
        raise FileValidationError(
            const.ERROR_SHEET_NOT_FOUND,
            code=const.VALIDATION_CODE_SHEET_NOT_FOUND,
        )


def validate_duplicate_file(file_hash: str, existing_hashes: Sequence[str]) -> None:
    """Validate that a file's content hash has not already been ingested.

    This is a pure membership check; computing the hash and persisting
    known hashes are the caller's responsibility.

    Args:
        file_hash: SHA-256 hex digest of the uploaded file's content.
        existing_hashes: Collection of previously ingested file hashes
            to check against.

    Raises:
        FileValidationError: If ``file_hash`` is already present in
            ``existing_hashes``.
    """
    if file_hash in existing_hashes:
        raise FileValidationError(
            const.ERROR_DUPLICATE_FILE,
            code=const.VALIDATION_CODE_DUPLICATE_FILE,
        )


# =============================================================================
# DATAFRAME VALIDATION
# =============================================================================


def validate_empty_dataframe(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame is not empty.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult indicating whether the DataFrame contains data.
    """
    is_valid = not dataframe.empty
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_EMPTY_DATAFRAME,
        message="" if is_valid else const.ERROR_EMPTY_FILE,
    )


def validate_minimum_rows(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame meets the minimum row requirement.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult indicating whether the row count is sufficient.
    """
    row_count = len(dataframe)
    is_valid = row_count >= const.MIN_REQUIRED_ROWS
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_INSUFFICIENT_ROWS,
        message="" if is_valid else const.ERROR_INSUFFICIENT_ROWS,
        details=None if is_valid else {"row_count": row_count},
    )


def validate_minimum_columns(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame meets the minimum column requirement.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult indicating whether the column count is sufficient.
    """
    column_count = dataframe.shape[1]
    is_valid = column_count >= const.MIN_REQUIRED_COLUMNS
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_INSUFFICIENT_COLUMNS,
        message="" if is_valid else const.ERROR_INSUFFICIENT_COLUMNS,
        details=None if is_valid else {"column_count": column_count},
    )


def validate_maximum_columns(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame does not exceed the maximum column limit.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult indicating whether the column count is within
        the allowed limit.
    """
    column_count = dataframe.shape[1]
    is_valid = column_count <= const.MAX_ALLOWED_COLUMNS
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_TOO_MANY_COLUMNS,
        message="" if is_valid else const.ERROR_TOO_MANY_COLUMNS,
        details=None if is_valid else {"column_count": column_count},
    )


# =============================================================================
# HEADER VALIDATION
# =============================================================================


def validate_duplicate_columns(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame has no duplicate column names.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult listing any duplicated column names found.
    """
    column_counts = Counter(dataframe.columns)
    duplicates = sorted(column for column, count in column_counts.items() if count > 1)
    is_valid = not duplicates
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_DUPLICATE_COLUMNS,
        message="" if is_valid else const.ERROR_INVALID_HEADERS,
        details=None if is_valid else {"duplicate_columns": duplicates},
    )


def validate_empty_headers(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame has no blank or auto-generated headers.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult listing any empty or unnamed column headers.
    """
    empty_headers = [
        str(column)
        for column in dataframe.columns
        if not str(column).strip() or str(column).lower().startswith("unnamed")
    ]
    is_valid = not empty_headers
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_EMPTY_HEADERS,
        message="" if is_valid else const.ERROR_INVALID_HEADERS,
        details=None if is_valid else {"empty_headers": empty_headers},
    )


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: Sequence[str],
) -> ValidationResult:
    """Validate that a DataFrame contains all required columns.

    Args:
        dataframe: Parsed tabular data to validate.
        required_columns: Column names that must be present.

    Returns:
        ValidationResult listing any required columns that are missing.
    """
    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]
    is_valid = not missing_columns
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_MISSING_REQUIRED_COLUMNS,
        message="" if is_valid else const.ERROR_INVALID_HEADERS,
        details=None if is_valid else {"missing_columns": missing_columns},
    )


# =============================================================================
# DATA VALIDATION
# =============================================================================


def validate_duplicate_rows(dataframe: pd.DataFrame) -> ValidationResult:
    """Validate that a DataFrame contains no fully duplicated rows.

    Args:
        dataframe: Parsed tabular data to validate.

    Returns:
        ValidationResult indicating the number of duplicate rows found.
    """
    duplicate_count = int(dataframe.duplicated().sum())
    is_valid = duplicate_count == 0
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_DUPLICATE_ROWS,
        message="" if is_valid else const.ERROR_DUPLICATE_ROWS_FOUND,
        details=None if is_valid else {"duplicate_row_count": duplicate_count},
    )


def validate_null_values(
    dataframe: pd.DataFrame,
    null_values: frozenset[str] = const.ACCEPTED_NULL_VALUES,
) -> ValidationResult:
    """Validate that a DataFrame contains no null-like values.

    Checks both true pandas nulls (``NaN``/``None``) and string
    representations of null defined in ``constants.ACCEPTED_NULL_VALUES``
    (e.g. ``"n/a"``, ``"null"``).

    Args:
        dataframe: Parsed tabular data to validate.
        null_values: Set of lowercase string tokens treated as null.
            Defaults to ``constants.ACCEPTED_NULL_VALUES``.

    Returns:
        ValidationResult listing per-column counts of null-like values.
    """
    columns_with_nulls: dict[str, int] = {}

    for column in dataframe.columns:
        series = dataframe[column]
        null_like_mask = series.isnull()

        # Only object-dtype columns can contain string null tokens
        # (e.g. "n/a"); numeric/bool/datetime columns cannot, so the
        # relatively costly string comparison is skipped for them.
        if series.dtype == object:
            string_values = series.dropna().astype(str).str.strip().str.lower()
            null_like_mask = null_like_mask | series.index.isin(
                string_values[string_values.isin(null_values)].index
            )

        null_count = int(null_like_mask.sum())
        if null_count > 0:
            columns_with_nulls[str(column)] = null_count

    is_valid = not columns_with_nulls
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_NULL_VALUES,
        message="" if is_valid else const.ERROR_NULL_VALUES_FOUND,
        details=None if is_valid else {"null_counts": columns_with_nulls},
    )


# Dtype-level predicates for common Python types, checked via pandas'
# type-introspection utilities so NumPy scalars (e.g. numpy.int64) and
# pandas nullable/extension dtypes (e.g. "Int64", "boolean") are
# recognized without iterating row-by-row.
_TYPE_DTYPE_CHECKS: Mapping[type, Callable[[pd.Series], bool]] = {
    int: pd.api.types.is_integer_dtype,
    float: pd.api.types.is_float_dtype,
    bool: pd.api.types.is_bool_dtype,
    str: pd.api.types.is_string_dtype,
}

# Element-wise fallback scalar types, used when a column's dtype is
# "object" (mixed/unknown) and the dtype-level check above cannot decide.
_TYPE_SCALAR_CHECKS: Mapping[type, tuple] = {
    int: (int, np.integer),
    float: (float, np.floating),
    bool: (bool, np.bool_),
    str: (str,),
}


def _column_matches_expected_type(series: pd.Series, expected_type: type) -> bool:
    """Determine whether a Series' non-null values match an expected type.

    Uses pandas dtype introspection (``pd.api.types``) first, since it
    correctly recognizes NumPy scalar types and pandas nullable/extension
    dtypes without iterating row-by-row. Falls back to an element-wise
    ``isinstance`` check for object-dtype columns or types with no
    dedicated dtype predicate.

    Args:
        series: Column data to check (may still contain nulls).
        expected_type: Expected Python type for non-null values.

    Returns:
        True if all non-null values match the expected type.
    """
    non_null_values = series.dropna()
    if non_null_values.empty:
        return True

    dtype_check = _TYPE_DTYPE_CHECKS.get(expected_type)
    if dtype_check is not None and dtype_check(non_null_values):
        return True

    scalar_types = _TYPE_SCALAR_CHECKS.get(expected_type, (expected_type,))
    return non_null_values.map(lambda value: isinstance(value, scalar_types)).all()


def validate_column_types(
    dataframe: pd.DataFrame,
    expected_types: Mapping[str, type],
) -> ValidationResult:
    """Validate that DataFrame columns contain values of an expected type.

    Non-null values in each specified column are checked against the
    expected Python type. Missing columns are ignored by this check;
    use ``validate_required_columns`` to enforce column presence.

    Args:
        dataframe: Parsed tabular data to validate.
        expected_types: Mapping of column name to the expected Python
            type for non-null values in that column.

    Returns:
        ValidationResult listing columns whose values do not match the
        expected type.
    """
    mismatched_columns = []

    for column, expected_type in expected_types.items():
        if column not in dataframe.columns:
            continue

        if not _column_matches_expected_type(dataframe[column], expected_type):
            mismatched_columns.append(column)

    is_valid = not mismatched_columns
    return ValidationResult(
        is_valid=is_valid,
        code=const.VALIDATION_CODE_COLUMN_TYPE_MISMATCH,
        message="" if is_valid else "One or more columns contain unexpected data types.",
        details=None if is_valid else {"mismatched_columns": mismatched_columns},
    )


# =============================================================================
# MASTER VALIDATION
# =============================================================================


def validate_dataframe(
    dataframe: pd.DataFrame,
    required_columns: Optional[Sequence[str]] = None,
    expected_types: Optional[Mapping[str, type]] = None,
) -> ValidationSummary:
    """Run the full suite of content-level validation checks on a DataFrame.

    Aggregates shape, header, and data-quality checks into a single
    report. This function does not raise on failure; callers should
    inspect ``ValidationSummary.is_valid`` and ``ValidationSummary.errors``
    to decide how to respond.

    Args:
        dataframe: Parsed tabular data to validate.
        required_columns: Optional column names that must be present.
            Skipped if not provided.
        expected_types: Optional mapping of column name to expected
            Python type. Skipped if not provided.

    Returns:
        ValidationSummary containing the results of every check that ran.
    """
    results = [
        validate_empty_dataframe(dataframe),
        validate_minimum_rows(dataframe),
        validate_minimum_columns(dataframe),
        validate_maximum_columns(dataframe),
        validate_duplicate_columns(dataframe),
        validate_empty_headers(dataframe),
        validate_duplicate_rows(dataframe),
        validate_null_values(dataframe),
    ]

    if required_columns:
        results.append(validate_required_columns(dataframe, required_columns))

    if expected_types:
        results.append(validate_column_types(dataframe, expected_types))

    is_valid = all(result.is_valid for result in results)
    return ValidationSummary(is_valid=is_valid, results=tuple(results))