"""Upload orchestration service for the H.I.R.E. Data Ingestion Pipeline.

This service coordinates the end-to-end upload workflow: validating an
incoming ``UploadFile``, persisting it to temporary storage, parsing it
into a DataFrame, running content validation, and assembling structured
results.

This module MUST remain orchestration-only. It intentionally does NOT
implement validation rules (delegated to ``validators``), does NOT
implement filesystem primitives (delegated to ``file_utils``), and does
NOT implement CSV/Excel parsing (delegated to ``csv_utils`` /
``excel_utils``). It does not clean, normalize, preprocess, or run AI
analysis on the data.

Typical usage example:

    service = UploadService(upload_root=settings.UPLOAD_ROOT)
    result = await service.process_upload(upload_file, company_id="acme-corp")

    if result.is_success:
        dataframe = result.success.dataframe
        metadata = result.success.metadata
    else:
        errors = result.failure.validation_summary.errors
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from fastapi import UploadFile
import pandas as pd

from app.utils import csv_utils, excel_utils, file_utils
from app.utils.constants import (
    SUPPORTED_CSV_EXTENSIONS,
    SUPPORTED_EXCEL_EXTENSIONS,
    UPLOAD_STAGING_SUBDIRECTORY,
)
from app.utils.validators import (
    FileValidationError,
    ValidationResult,
    ValidationSummary,
    validate_dataframe,
    validate_file_extension,
    validate_file_size,
    validate_filename,
    validate_mime_type,
)

logger = logging.getLogger(__name__)

#: Exceptions raised by the parsing utilities that indicate a file passed
#: pre-upload validation but could not actually be parsed. Centralized
#: here so _parse_file() and _build_metadata() don't each redeclare the
#: same tuple.
_PARSER_ERRORS = (csv_utils.CsvUtilsError, excel_utils.ExcelUtilsError)


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class UploadServiceError(Exception):
    """Base exception for unrecoverable upload pipeline failures.

    Reserved for failures the pipeline cannot proceed past or produce a
    structured ``ValidationSummary`` for — e.g. storage failures, or a
    file that passes extension checks but is too corrupted to parse.
    Recoverable, expected content problems are represented as a
    ``ValidationSummary`` on the returned ``UploadResult`` instead of
    being raised.
    """


class UploadStorageError(UploadServiceError):
    """Raised when the uploaded file cannot be persisted to temp storage."""


class UnsupportedFileTypeError(UploadServiceError):
    """Raised when a file's type cannot be mapped to a known parser.

    This is a defensive guard only; in normal operation, extension
    validation in step 2 of the pipeline should prevent this from ever
    being reached.
    """


class FileParsingError(UploadServiceError):
    """Raised when a file passes validation but cannot be parsed.

    Indicates the file is likely corrupted, truncated, or malformed in a
    way that extension/MIME checks cannot catch (e.g. an .xlsx file that
    is not a valid zip archive). When this occurs after the file has
    already been persisted to temp storage, the pipeline removes the
    orphaned file before propagating this exception.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class FileType(str, Enum):
    """Supported upload file types."""

    CSV = "csv"
    EXCEL = "excel"


class UploadStage(str, Enum):
    """Pipeline stage at which an ``UploadResult`` failure occurred.

    Used instead of raw strings on ``UploadFailure.stage`` so failure
    stages are enumerable and typo-proof at call sites, while still
    behaving like a plain string (via the ``str`` mixin) for logging,
    comparisons, and JSON serialization in API responses.
    """

    PRE_UPLOAD_VALIDATION = "pre_upload_validation"
    CONTENT_VALIDATION = "content_validation"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class UploadMetadata:
    """Structural metadata describing a successfully ingested upload.

    Attributes:
        original_filename: The filename exactly as supplied by the
            client (e.g. ``"candidates.csv"``). Preserved for display,
            audit, and error-reporting purposes.
        stored_filename: The collision-resistant filename actually used
            on disk (e.g. a UUID-based name from ``file_utils``). Useful
            when downstream stages need to reference the file without
            re-deriving the full path.
        file_type: Detected file type (CSV or Excel).
        file_size_bytes: Size of the uploaded content, in bytes.
        saved_path: Path to the persisted temporary file.
        source_metadata: Raw metadata returned by ``csv_utils`` /
            ``excel_utils`` (headers, row/column counts, encoding or
            sheet names, etc.), passed through unmodified.
    """

    original_filename: str
    stored_filename: str
    file_type: FileType
    file_size_bytes: int
    saved_path: Path
    source_metadata: dict[str, Any]


@dataclass(frozen=True)
class UploadSuccess:
    """Payload returned when the upload pipeline completes successfully.

    Attributes:
        dataframe: The parsed file content.
        metadata: Structural metadata about the upload.
    """

    dataframe: pd.DataFrame
    metadata: UploadMetadata


@dataclass(frozen=True)
class UploadFailure:
    """Payload returned when the upload pipeline halts on a validation issue.

    Attributes:
        stage: The pipeline stage at which validation failed.
        validation_summary: The full set of validation issues found.
    """

    stage: UploadStage
    validation_summary: ValidationSummary


@dataclass(frozen=True)
class UploadResult:
    """Discriminated result of an upload pipeline run.

    Exactly one of ``success`` or ``failure`` is populated, indicated by
    ``is_success``. This invariant is enforced in ``__post_init__`` so
    that constructing an ``UploadResult`` outside of the ``succeeded()``/
    ``failed()`` factory methods (e.g. directly in a test) can't silently
    produce an inconsistent instance.

    Attributes:
        is_success: True if the pipeline completed successfully.
        success: Populated when ``is_success`` is True.
        failure: Populated when ``is_success`` is False.
    """

    is_success: bool
    success: UploadSuccess | None = None
    failure: UploadFailure | None = None

    def __post_init__(self) -> None:
        """Validate that exactly one of success/failure is populated.

        Raises:
            ValueError: If ``is_success`` and the populated payload
                disagree (e.g. ``is_success=True`` with no ``success``,
                or both ``success`` and ``failure`` set).
        """
        if self.is_success and self.success is None:
            raise ValueError("UploadResult with is_success=True requires a success payload.")
        if not self.is_success and self.failure is None:
            raise ValueError("UploadResult with is_success=False requires a failure payload.")
        if self.success is not None and self.failure is not None:
            raise ValueError("UploadResult cannot have both success and failure populated.")

    @classmethod
    def succeeded(cls, dataframe: pd.DataFrame, metadata: UploadMetadata) -> "UploadResult":
        """Build a successful result.

        Args:
            dataframe: The parsed file content.
            metadata: Structural metadata about the upload.

        Returns:
            An ``UploadResult`` with ``is_success=True``.
        """
        return cls(is_success=True, success=UploadSuccess(dataframe, metadata))

    @classmethod
    def failed(cls, stage: UploadStage, validation_summary: ValidationSummary) -> "UploadResult":
        """Build a failed result.

        Args:
            stage: The pipeline stage at which validation failed.
            validation_summary: The validation issues that caused the
                failure.

        Returns:
            An ``UploadResult`` with ``is_success=False``.
        """
        return cls(is_success=False, failure=UploadFailure(stage, validation_summary))


# --------------------------------------------------------------------------- #
# Upload Service
# --------------------------------------------------------------------------- #


class UploadService:
    """Orchestrates the resume/candidate-data upload pipeline.

    The service depends only on the utility modules injected/imported at
    construction time (filesystem root), making it straightforward to
    unit test with a temporary directory and in-memory ``UploadFile``
    instances — no network or database access is required.

    Attributes:
        upload_root: Base directory under which per-company upload
            workspaces are created.
    """

    def __init__(self, upload_root: str | Path) -> None:
        """Initialize the service.

        Args:
            upload_root: Base directory under which per-company upload
                workspaces are created (e.g. from application settings).
        """
        self.upload_root = Path(upload_root)

    async def process_upload(self, upload_file: UploadFile, company_id: str) -> UploadResult:
        """Run the full upload pipeline for a single file.

        Pipeline stages:
            1. Read the upload content into memory, then close the
               underlying ``UploadFile`` — its data now lives in
               ``content`` and the spooled temp file/socket resources
               backing it are no longer needed.
            2. Validate filename, extension, MIME type, and size.
            3. Persist the file to a temporary staging directory.
            4. Detect file type and parse it into a DataFrame. If
               parsing fails, the persisted file is removed before the
               error propagates, since a corrupted file has no further
               use in the pipeline.
            5. Validate the parsed DataFrame's content. A content
               validation failure is returned as a structured result
               without deleting the persisted file — it may be useful
               for the caller to inspect or re-attempt.
            6. On success, assemble and return metadata alongside the
               DataFrame. The persisted file is left in place, since
               downstream pipeline stages read it from disk.

        Args:
            upload_file: The incoming FastAPI ``UploadFile``.
            company_id: Identifier used to scope the temporary storage
                workspace for this upload.

        Returns:
            An ``UploadResult`` describing either a successful parse
            (DataFrame + metadata) or a validation failure (every issue
            found, without proceeding further in the pipeline).

        Raises:
            UploadStorageError: If the file cannot be persisted to disk.
            FileParsingError: If the file cannot be parsed, or its
                metadata cannot be extracted, despite passing pre-upload
                validation.
            UnsupportedFileTypeError: If the file type cannot be mapped
                to a known parser (defensive; should not occur in
                normal operation).
        """
        content = await upload_file.read()
        await upload_file.close()

        pre_validation = self._validate_pre_upload(upload_file, content)
        if not pre_validation.is_valid:
            return UploadResult.failed(UploadStage.PRE_UPLOAD_VALIDATION, pre_validation)

        file_type = self._detect_file_type(upload_file.filename)
        saved_path = self._persist_temp_file(upload_file.filename, content, company_id)

        try:
            dataframe = self._parse_file(saved_path, file_type)
        except FileParsingError:
            self._cleanup_temp_file(saved_path)
            raise

        content_validation = validate_dataframe(dataframe)
        if not content_validation.is_valid:
            return UploadResult.failed(UploadStage.CONTENT_VALIDATION, content_validation)

        try:
            metadata = self._build_metadata(
                original_filename=upload_file.filename or saved_path.name,
                saved_path=saved_path,
                file_type=file_type,
                file_size_bytes=len(content),
            )
        except FileParsingError:
            self._cleanup_temp_file(saved_path)
            raise

        return UploadResult.succeeded(dataframe, metadata)

    def _validate_pre_upload(
        self,
        upload_file: UploadFile,
        content: bytes,
    ) -> ValidationSummary:
        """Run all pre-parse validation checks against the raw upload.

        ``validators.py`` implements file-level checks as functions that
        raise ``FileValidationError`` on failure rather than returning a
        result object. This method adapts that exception-based contract
        into the same ``ValidationSummary`` shape used by content
        validation, so callers of ``process_upload`` have one consistent
        result type regardless of which pipeline stage failed.

        Every validator runs regardless of earlier failures — a caught
        ``FileValidationError`` is converted into a ``ValidationResult``
        and validation continues, so the caller gets every problem with
        the upload at once rather than one at a time.

        Args:
            upload_file: The incoming ``UploadFile`` (used for filename
                and declared content type).
            content: The raw bytes read from the upload.

        Returns:
            A ``ValidationSummary`` aggregating every issue found across
            filename, extension, MIME type, and size checks.
        """
        checks: tuple[Callable[[], None], ...] = (
            lambda: validate_filename(upload_file.filename),
            lambda: validate_file_extension(upload_file.filename or ""),
            lambda: validate_mime_type(upload_file.content_type),
            lambda: validate_file_size(len(content)),
        )

        results: list[ValidationResult] = []
        for check in checks:
            try:
                check()
            except FileValidationError as exc:
                results.append(self._as_validation_result(exc))

        return ValidationSummary(is_valid=not results, results=tuple(results))

    @staticmethod
    def _as_validation_result(error: FileValidationError) -> ValidationResult:
        """Convert a caught ``FileValidationError`` into a ``ValidationResult``.

        Extracted as its own method so the exception-to-result mapping is
        independently testable and has a single point of change if
        ``FileValidationError``'s shape ever evolves.

        Args:
            error: The caught validation error.

        Returns:
            An equivalent, failing ``ValidationResult``.
        """
        return ValidationResult(is_valid=False, code=error.code, message=error.message)

    def _detect_file_type(self, filename: str | None) -> FileType:
        """Map a filename's extension to a supported ``FileType``.

        Args:
            filename: The uploaded file's original filename.

        Returns:
            The detected ``FileType``.

        Raises:
            UnsupportedFileTypeError: If the extension does not map to a
                known file type. In normal operation this should be
                unreachable, since extension validation already ran.
        """
        extension = file_utils.get_file_extension(filename or "")
        if extension in SUPPORTED_CSV_EXTENSIONS:
            return FileType.CSV
        if extension in SUPPORTED_EXCEL_EXTENSIONS:
            return FileType.EXCEL
        raise UnsupportedFileTypeError(
            f"Cannot map extension '{extension}' to a supported file type."
        )

    def _persist_temp_file(
        self,
        filename: str | None,
        content: bytes,
        company_id: str,
    ) -> Path:
        """Persist uploaded content to a per-company staging directory.

        Args:
            filename: The uploaded file's original filename, used to
                derive a collision-resistant storage filename.
            content: The raw bytes to persist.
            company_id: Identifier used to scope the storage workspace.

        Returns:
            The path to the saved temporary file.

        Raises:
            UploadStorageError: If the directory or file cannot be
                created on disk.
        """
        try:
            company_dir = file_utils.create_company_directory(self.upload_root, company_id)
            processing_dirs = file_utils.create_processing_directory(company_dir)
            staging_dir = processing_dirs[UPLOAD_STAGING_SUBDIRECTORY]
            unique_filename = file_utils.generate_unique_filename(filename or "upload")
            return file_utils.save_uploaded_file(content, staging_dir, unique_filename)
        except file_utils.FileUtilsError as exc:
            raise UploadStorageError(f"Failed to persist uploaded file: {exc}") from exc

    def _cleanup_temp_file(self, saved_path: Path) -> None:
        """Best-effort removal of a persisted file after an unrecoverable failure.

        Only called when the pipeline is about to raise
        (``FileParsingError``) — never on a structured content-validation
        failure, since that file may still be useful to the caller.
        Cleanup failures are logged and swallowed rather than raised, so
        a secondary filesystem error never masks the primary parsing
        failure that triggered the cleanup.

        Args:
            saved_path: Path to the persisted file to remove.
        """
        try:
            file_utils.delete_file(saved_path)
        except file_utils.FileUtilsError:
            logger.warning(
                "Failed to clean up orphaned upload file after a pipeline failure: %s",
                saved_path,
                exc_info=True,
            )

    def _parse_file(self, file_path: Path, file_type: FileType) -> pd.DataFrame:
        """Parse a persisted file into a DataFrame using the correct utility.

        CSV rows are read via ``csv_utils`` (which returns ``list[dict]``)
        and adapted into a DataFrame here; Excel files are already
        returned as a DataFrame by ``excel_utils``. This adaptation is a
        data-shape conversion only — no parsing logic lives here.

        Args:
            file_path: Path to the persisted file.
            file_type: The detected file type.

        Returns:
            The parsed content as a ``pd.DataFrame``.

        Raises:
            FileParsingError: If the file cannot be parsed.
        """
        try:
            if file_type is FileType.CSV:
                rows = csv_utils.read_csv_file(file_path)
                return pd.DataFrame(rows)
            return excel_utils.read_excel_file(file_path)
        except _PARSER_ERRORS as exc:
            raise FileParsingError(f"Failed to parse {file_path.name}: {exc}") from exc

    def _build_metadata(
        self,
        original_filename: str,
        saved_path: Path,
        file_type: FileType,
        file_size_bytes: int,
    ) -> UploadMetadata:
        """Assemble structural metadata for a successfully parsed upload.

        Args:
            original_filename: The filename exactly as supplied by the
                client, preserved for display/audit purposes.
            saved_path: Path to the persisted temporary file.
            file_type: The detected file type.
            file_size_bytes: Size of the original uploaded content, in
                bytes.

        Returns:
            An ``UploadMetadata`` instance combining pipeline-level
            fields with the raw metadata from ``csv_utils`` /
            ``excel_utils``.

        Raises:
            FileParsingError: If metadata extraction fails.
        """
        try:
            if file_type is FileType.CSV:
                source_metadata = csv_utils.get_csv_metadata(saved_path)
            else:
                source_metadata = excel_utils.get_excel_metadata(saved_path)
        except _PARSER_ERRORS as exc:
            raise FileParsingError(
                f"Failed to extract metadata for {saved_path.name}: {exc}"
            ) from exc

        return UploadMetadata(
            original_filename=original_filename,
            stored_filename=saved_path.name,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            saved_path=saved_path,
            source_metadata=source_metadata,
        )