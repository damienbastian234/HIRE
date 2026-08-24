"""Validation orchestration service for the H.I.R.E. Data Ingestion Pipeline.

This service coordinates validation of upload candidates: running the
exception-based file-level checks from ``validators.py`` against raw
upload attributes (filename, content type, size), running content
validation against an already-parsed DataFrame, and combining both into
a single structured report.

This module MUST remain orchestration-only. It intentionally does NOT
implement any validation rules itself — every rule lives in
``validators.py`` and is only adapted/aggregated here. It does NOT read
files, does NOT parse CSV/Excel content, and does NOT persist anything;
those responsibilities belong to ``file_utils``, ``csv_utils``,
``excel_utils``, and ``upload_service`` respectively. This service has
no filesystem dependency at all — it operates purely on data already
available in memory (a candidate's declared attributes and/or an
already-parsed ``pd.DataFrame``), which is what makes it usable both
standalone (e.g. a "would this upload be accepted?" check before any
file I/O happens) and alongside the upload pipeline.

Typical usage example:

    service = ValidationService()
    candidate = FileValidationCandidate(
        filename=upload_file.filename,
        content_type=upload_file.content_type,
        size_bytes=len(content),
    )
    report = service.validate_upload(candidate, dataframe=parsed_dataframe)

    if not report.is_valid:
        for issue in report.errors:
            print(issue.code, issue.message)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import pandas as pd

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


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class ValidationServiceError(Exception):
    """Base exception for unrecoverable validation-orchestration failures.

    Reserved for failures that indicate a contract violation with
    ``validators.py`` rather than an expected, recoverable validation
    problem with the data being checked. Recoverable, expected problems
    (bad filename, unsupported extension, empty DataFrame, etc.) are
    represented as a ``ValidationSummary``/``ValidationReport`` instead
    of being raised.
    """


class UnexpectedValidatorFailureError(ValidationServiceError):
    """Raised when a validator raises something other than ``FileValidationError``.

    Every file-level validator in ``validators.py`` is documented to
    signal failure exclusively via ``FileValidationError``. If one raises
    any other exception type, that is a bug or contract change in
    ``validators.py`` rather than a normal validation failure, so it is
    surfaced loudly instead of being silently absorbed into a
    ``ValidationResult``.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class ValidationStage(str, Enum):
    """Identifies which validation stage produced a given outcome.

    Mirrors the intent of ``upload_service.UploadStage`` but is defined
    independently here rather than imported, to keep this service free
    of any dependency on ``upload_service`` — the two are siblings, not
    layered on one another.
    """

    FILE_LEVEL = "file_level"
    CONTENT = "content"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FileValidationCandidate:
    """The raw, declared attributes of an upload to validate before parsing.

    Bundling these together (rather than passing three loose parameters)
    gives callers a single, reusable, self-documenting object to
    construct once and pass around.

    Attributes:
        filename: The filename as declared by the client, if any.
        content_type: The MIME type as declared by the client, if any.
        size_bytes: The size of the uploaded content, in bytes.
    """

    filename: str | None
    content_type: str | None
    size_bytes: int


@dataclass(frozen=True)
class ValidationOutcome:
    """The result of running a single validation stage.

    Attributes:
        stage: Which validation stage produced this outcome.
        summary: The ``ValidationSummary`` returned by that stage.
    """

    stage: ValidationStage
    summary: ValidationSummary


@dataclass(frozen=True)
class ValidationReport:
    """Aggregated result of running one or more validation stages in sequence.

    Attributes:
        is_valid: True only if every stage that ran passed. A stage that
            was skipped (e.g. content validation skipped because
            file-level validation already failed) does not count against
            this.
        outcomes: The per-stage outcomes, in the order the stages ran.
    """

    is_valid: bool
    outcomes: tuple[ValidationOutcome, ...]

    @property
    def errors(self) -> tuple[ValidationResult, ...]:
        """Every failing ``ValidationResult`` across all stages, flattened.

        Returns:
            A tuple of all failing results, in stage order, then
            within-stage order. Empty if ``is_valid`` is True.
        """
        return tuple(
            result
            for outcome in self.outcomes
            for result in outcome.summary.errors
        )

    def for_stage(self, stage: ValidationStage) -> ValidationOutcome | None:
        """Look up the outcome for a specific stage, if it ran.

        Args:
            stage: The stage to look up.

        Returns:
            The matching ``ValidationOutcome``, or None if that stage did
            not run (e.g. content validation was skipped).
        """
        return next((o for o in self.outcomes if o.stage is stage), None)


# --------------------------------------------------------------------------- #
# Validation Service
# --------------------------------------------------------------------------- #


class ValidationService:
    """Orchestrates file-level and content validation for upload candidates.

    Every validation *rule* lives in ``validators.py``; this service only
    adapts its exception-based file-level contract and its
    ``ValidationSummary``-based content contract into one consistent
    reporting shape, and decides which stages to run and in what order.
    It holds no state and has no filesystem dependency, which makes it
    trivial to unit test with plain in-memory inputs.
    """

    def validate_file_candidate(self, candidate: FileValidationCandidate) -> ValidationSummary:
        """Run every file-level validator against a candidate upload.

        Each validator in ``validators.py`` raises ``FileValidationError``
        on failure rather than returning a result, so this method runs
        every validator regardless of earlier failures and converts each
        caught error into a ``ValidationResult``. This means the caller
        gets every problem with the candidate at once, rather than
        stopping at the first one.

        Args:
            candidate: The declared attributes of the upload to check.

        Returns:
            A ``ValidationSummary`` aggregating every issue found across
            filename, extension, MIME type, and size checks.

        Raises:
            UnexpectedValidatorFailureError: If a validator raises
                anything other than ``FileValidationError``.
        """
        checks: tuple[Callable[[], None], ...] = (
            lambda: validate_filename(candidate.filename),
            lambda: validate_file_extension(candidate.filename or ""),
            lambda: validate_mime_type(candidate.content_type),
            lambda: validate_file_size(candidate.size_bytes),
        )

        results = self._run_checks(checks)
        summary = ValidationSummary(is_valid=not results, results=tuple(results))
        self._log_outcome(ValidationStage.FILE_LEVEL, summary)
        return summary

    def validate_content(self, dataframe: pd.DataFrame) -> ValidationSummary:
        """Run content validation against an already-parsed DataFrame.

        Delegates entirely to ``validators.validate_dataframe()`` — no
        content-validation rules are implemented in this service.

        Args:
            dataframe: The parsed CSV/Excel content to validate.

        Returns:
            The ``ValidationSummary`` returned by ``validate_dataframe()``.
        """
        summary = validate_dataframe(dataframe)
        self._log_outcome(ValidationStage.CONTENT, summary)
        return summary

    def validate_upload(
        self,
        candidate: FileValidationCandidate,
        dataframe: pd.DataFrame | None = None,
    ) -> ValidationReport:
        """Run the full validation sequence for an upload candidate.

        Runs file-level validation first. Content validation only runs
        if file-level validation passed *and* a DataFrame was supplied —
        there is no reason to validate the content of a file whose
        declared attributes were already rejected, and a caller may not
        have parsed the file yet (e.g. checking acceptability before
        doing any parsing work).

        Args:
            candidate: The declared attributes of the upload to check.
            dataframe: The parsed content to validate, if available.
                Pass ``None`` to run file-level validation only.

        Returns:
            A ``ValidationReport`` combining every stage that ran.
        """
        outcomes: list[ValidationOutcome] = []

        file_summary = self.validate_file_candidate(candidate)
        outcomes.append(ValidationOutcome(ValidationStage.FILE_LEVEL, file_summary))

        if file_summary.is_valid and dataframe is not None:
            content_summary = self.validate_content(dataframe)
            outcomes.append(ValidationOutcome(ValidationStage.CONTENT, content_summary))

        report = ValidationReport(
            is_valid=all(outcome.summary.is_valid for outcome in outcomes),
            outcomes=tuple(outcomes),
        )
        logger.info(
            "Validation report complete: is_valid=%s stages_run=%d",
            report.is_valid,
            len(outcomes),
        )
        return report

    def _run_checks(self, checks: tuple[Callable[[], None], ...]) -> list[ValidationResult]:
        """Execute a sequence of exception-based validator calls.

        Every check runs regardless of earlier failures. A caught
        ``FileValidationError`` is converted into a ``ValidationResult``;
        any other exception is treated as an unrecoverable contract
        violation and raised immediately.

        Args:
            checks: Zero-argument callables, each wrapping a call to one
                validator function.

        Returns:
            A ``ValidationResult`` for every check that failed (empty if
            all checks passed).

        Raises:
            UnexpectedValidatorFailureError: If a check raises an
                exception other than ``FileValidationError``.
        """
        results: list[ValidationResult] = []
        for check in checks:
            try:
                check()
            except FileValidationError as exc:
                results.append(self._as_validation_result(exc))
            except Exception as exc:
                logger.error("Unexpected exception raised by a validator.", exc_info=True)
                raise UnexpectedValidatorFailureError(
                    f"Validator raised an unexpected exception: {exc}"
                ) from exc
        return results

    @staticmethod
    def _as_validation_result(error: FileValidationError) -> ValidationResult:
        """Convert a caught ``FileValidationError`` into a ``ValidationResult``.

        Args:
            error: The caught validation error.

        Returns:
            An equivalent, failing ``ValidationResult``.
        """
        return ValidationResult(is_valid=False, code=error.code, message=error.message)

    @staticmethod
    def _log_outcome(stage: ValidationStage, summary: ValidationSummary) -> None:
        """Log the result of a single validation stage.

        Args:
            stage: The stage that just completed.
            summary: The resulting summary.
        """
        if summary.is_valid:
            logger.info("%s validation passed.", stage.value)
        else:
            logger.warning(
                "%s validation failed with %d issue(s): %s",
                stage.value,
                len(summary.results),
                [result.code for result in summary.errors],
            )