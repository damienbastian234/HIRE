"""
constants.py

Centralized constants for the Data Ingestion Pipeline module.

This module contains ONLY static, immutable configuration values used
across the ingestion pipeline (upload validation, parsing defaults,
processing status tracking, and standardized API messages).

No functions or business logic should be added to this file.
"""

from typing import Final


# =============================================================================
# 1. ALLOWED UPLOAD EXTENSIONS
# =============================================================================

ALLOWED_UPLOAD_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".csv",
    ".xlsx",
    ".xls",
})


# =============================================================================
# 2. SUPPORTED MIME TYPES
# =============================================================================

SUPPORTED_MIME_TYPES: Final[frozenset[str]] = frozenset({
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})


# =============================================================================
# 3. MAXIMUM UPLOAD SIZE
# =============================================================================

MAX_UPLOAD_SIZE_MB: Final[int] = 25
MAX_UPLOAD_SIZE_BYTES: Final[int] = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# =============================================================================
# 4. UPLOAD FOLDER NAMES
# =============================================================================

UPLOAD_ROOT_FOLDER: Final[str] = "uploads"
RAW_UPLOAD_FOLDER: Final[str] = f"{UPLOAD_ROOT_FOLDER}/raw"
PROCESSED_UPLOAD_FOLDER: Final[str] = f"{UPLOAD_ROOT_FOLDER}/processed"
FAILED_UPLOAD_FOLDER: Final[str] = f"{UPLOAD_ROOT_FOLDER}/failed"
TEMP_UPLOAD_FOLDER: Final[str] = f"{UPLOAD_ROOT_FOLDER}/temp"


# =============================================================================
# 5. CSV DEFAULTS
# =============================================================================

DEFAULT_CSV_ENCODING: Final[str] = "utf-8"
DEFAULT_CSV_DELIMITER: Final[str] = ","


# =============================================================================
# 6. EXCEL DEFAULTS
# =============================================================================

DEFAULT_EXCEL_SHEET_INDEX: Final[int] = 0


# =============================================================================
# 7. VALIDATION LIMITS
# =============================================================================

MIN_REQUIRED_ROWS: Final[int] = 1
MIN_REQUIRED_COLUMNS: Final[int] = 1
MAX_ALLOWED_COLUMNS: Final[int] = 200


# =============================================================================
# 8. ACCEPTED NULL VALUES
# =============================================================================

ACCEPTED_NULL_VALUES: Final[frozenset[str]] = frozenset({
    "",
    "na",
    "n/a",
    "null",
    "none",
    "nan",
    "-",
    "--",
})


# =============================================================================
# 9. PROCESSING STATUS CONSTANTS
# =============================================================================

STATUS_PENDING: Final[str] = "pending"
STATUS_UPLOADING: Final[str] = "uploading"
STATUS_VALIDATING: Final[str] = "validating"
STATUS_CLEANING: Final[str] = "cleaning"
STATUS_NORMALIZING: Final[str] = "normalizing"
STATUS_PREPROCESSING: Final[str] = "preprocessing"
STATUS_ANALYZING: Final[str] = "analyzing"
STATUS_READY: Final[str] = "ready"
STATUS_COMPLETED: Final[str] = "completed"
STATUS_FAILED: Final[str] = "failed"


# =============================================================================
# 10. STANDARDIZED ERROR MESSAGES
# =============================================================================

ERROR_UNSUPPORTED_FILE_EXTENSION: Final[str] = (
    "Unsupported file extension. Allowed extensions are: .csv, .xlsx, .xls"
)
ERROR_UNSUPPORTED_MIME_TYPE: Final[str] = (
    "Unsupported file MIME type."
)
ERROR_FILE_TOO_LARGE: Final[str] = (
    f"File exceeds the maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB."
)
ERROR_EMPTY_FILE: Final[str] = "The uploaded file is empty."
ERROR_CORRUPTED_FILE: Final[str] = "The uploaded file could not be read or is corrupted."
ERROR_INSUFFICIENT_ROWS: Final[str] = (
    f"The file must contain at least {MIN_REQUIRED_ROWS} row(s) of data."
)
ERROR_INSUFFICIENT_COLUMNS: Final[str] = (
    f"The file must contain at least {MIN_REQUIRED_COLUMNS} column(s)."
)
ERROR_TOO_MANY_COLUMNS: Final[str] = (
    f"The file exceeds the maximum allowed column count of {MAX_ALLOWED_COLUMNS}."
)
ERROR_FILE_PARSING_FAILED: Final[str] = "Failed to parse the uploaded file."
ERROR_UPLOAD_FAILED: Final[str] = "File upload failed. Please try again."
ERROR_DUPLICATE_FILE: Final[str] = "A file with the same content has already been uploaded."
ERROR_INVALID_HEADERS: Final[str] = "The file contains invalid or missing column headers."
ERROR_NULL_VALUES_FOUND: Final[str] = "The file contains unexpected null values."
ERROR_DUPLICATE_ROWS_FOUND: Final[str] = "The file contains duplicate rows."
ERROR_INVALID_ENCODING: Final[str] = "The file encoding is invalid or unsupported."
ERROR_EMPTY_COLUMNS: Final[str] = "The file contains one or more empty columns."
ERROR_EMPTY_ROWS: Final[str] = "The file contains one or more empty rows."
ERROR_SHEET_NOT_FOUND: Final[str] = "The specified sheet could not be found in the file."


# =============================================================================
# 11. STANDARDIZED SUCCESS MESSAGES
# =============================================================================

SUCCESS_FILE_UPLOADED: Final[str] = "File uploaded successfully."
SUCCESS_FILE_VALIDATED: Final[str] = "File validated successfully."
SUCCESS_FILE_CLEANED: Final[str] = "File cleaned successfully."
SUCCESS_FILE_PREPROCESSED: Final[str] = "File preprocessed successfully."
SUCCESS_PROCESSING_COMPLETED: Final[str] = "File processing completed successfully."


# =============================================================================
# 12. STANDARDIZED API RESPONSE KEYS
# =============================================================================

RESPONSE_SUCCESS: Final[str] = "success"
RESPONSE_ERROR: Final[str] = "error"
RESPONSE_MESSAGE: Final[str] = "message"
RESPONSE_DATA: Final[str] = "data"
RESPONSE_STATUS: Final[str] = "status"


# =============================================================================
# 13. PARSER ENGINE CONSTANTS
# =============================================================================

CSV_ENGINE: Final[str] = "python"
EXCEL_ENGINE: Final[str] = "openpyxl"


# =============================================================================
# 14. SUPPORTED FILE TYPES
# =============================================================================

FILE_TYPE_CSV: Final[str] = "csv"
FILE_TYPE_EXCEL: Final[str] = "excel"


# =============================================================================
# 15. UPLOAD LIMITS
# =============================================================================

MAX_UPLOAD_FILES: Final[int] = 10


# =============================================================================
# 16. EXCEL LIMITS
# =============================================================================

MAX_SHEET_NAME_LENGTH: Final[int] = 31


# =============================================================================
# 17. SUPPORTED ENCODINGS
# =============================================================================

SUPPORTED_ENCODINGS: Final[frozenset[str]] = frozenset({
    "utf-8",
    "utf-8-sig",
    "latin-1",
    "iso-8859-1",
    "cp1252",
})


# =============================================================================
# 18. VALIDATION CODE CONSTANTS
# =============================================================================

VALIDATION_CODE_UNSUPPORTED_FILE_EXTENSION: Final[str] = "UNSUPPORTED_FILE_EXTENSION"
VALIDATION_CODE_EMPTY_FILE: Final[str] = "EMPTY_FILE"
VALIDATION_CODE_FILE_TOO_LARGE: Final[str] = "FILE_TOO_LARGE"
VALIDATION_CODE_UNSUPPORTED_MIME_TYPE: Final[str] = "UNSUPPORTED_MIME_TYPE"
VALIDATION_CODE_EMPTY_FILENAME: Final[str] = "EMPTY_FILENAME"
VALIDATION_CODE_INVALID_FILENAME: Final[str] = "INVALID_FILENAME"
VALIDATION_CODE_INVALID_ENCODING: Final[str] = "INVALID_ENCODING"
VALIDATION_CODE_SHEET_NOT_FOUND: Final[str] = "SHEET_NOT_FOUND"
VALIDATION_CODE_DUPLICATE_FILE: Final[str] = "DUPLICATE_FILE"
VALIDATION_CODE_EMPTY_DATAFRAME: Final[str] = "EMPTY_DATAFRAME"
VALIDATION_CODE_INSUFFICIENT_ROWS: Final[str] = "INSUFFICIENT_ROWS"
VALIDATION_CODE_INSUFFICIENT_COLUMNS: Final[str] = "INSUFFICIENT_COLUMNS"
VALIDATION_CODE_TOO_MANY_COLUMNS: Final[str] = "TOO_MANY_COLUMNS"
VALIDATION_CODE_DUPLICATE_COLUMNS: Final[str] = "DUPLICATE_COLUMNS"
VALIDATION_CODE_EMPTY_HEADERS: Final[str] = "EMPTY_HEADERS"
VALIDATION_CODE_MISSING_REQUIRED_COLUMNS: Final[str] = "MISSING_REQUIRED_COLUMNS"
VALIDATION_CODE_DUPLICATE_ROWS: Final[str] = "DUPLICATE_ROWS"
VALIDATION_CODE_NULL_VALUES: Final[str] = "NULL_VALUES_FOUND"
VALIDATION_CODE_COLUMN_TYPE_MISMATCH: Final[str] = "COLUMN_TYPE_MISMATCH"