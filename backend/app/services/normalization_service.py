"""DataFrame normalization orchestration service for the H.I.R.E. backend.

This service runs as the pipeline stage immediately after
``cleaning_service.py`` and before preprocessing. It applies a small set
of representational-consistency operations that are deliberately
distinct from cleaning's scope (column names, whitespace, missing-value
tokens, control characters, empty/duplicate rows -- see
``cleaning_service.py``'s own docstring, which explicitly claims that
scope as "normalization" and fences off anything further).

.. IMPORTANT -- DOCUMENTED ASSUMPTIONS ::

    No project documentation defines a distinct "Normalization" pipeline
    stage, and the real ``preprocessing_service.py`` / ``ai_data_service.py``
    skeletons that would clarify Normalization's expected input/output
    contract were not available at the time this file was written (repeated
    upload attempts did not come through). Rather than invent broad business
    logic, this implementation is intentionally narrow and limited to
    operations with concrete grounding elsewhere in the project:

    1. Unicode normalization (NFKC) on every string cell -- a standard,
       business-logic-free data-hygiene operation. Not tied to any HIRE-
       specific rule; justified purely because unnormalized Unicode causes
       well-known data-integrity bugs (e.g. "cafe" as a composed vs.
       decomposed accent sequence comparing as unequal).
    2. Email address lowercasing, scoped only to a column literally named
       "email" (matching CleaningService's own column-naming convention:
       lowercase, spaces -> underscores). Justified by the ``UNIQUE``
       constraint on ``User.email`` in 04_DATABASE_DESIGN.md -- without
       case normalization, that uniqueness constraint could be silently
       bypassed by case variants of the same address. If no "email" column
       is present, this step is a no-op.

    Explicitly NOT implemented, since no specification exists to justify a
    concrete target format: phone number formatting, date/time
    canonicalization, or any casing convention for skill/category/free-text
    fields. If the real normalization contract specifies these, this file
    will need to be revised once that contract is available.

This module MUST NOT duplicate cleaning's responsibilities, implement
preprocessing (type inference, feature preparation), or implement AI
logic. It operates purely on an in-memory DataFrame -- no filesystem
access, no database access, no FastAPI dependency.

Typical usage example:

    service = NormalizationService()
    result = service.normalize_dataframe(cleaned_dataframe)

    if result.is_success:
        normalized_df = result.success.dataframe
        stats = result.success.metadata
    else:
        print(result.failure.stage, result.failure.message)
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)

#: Dtypes treated as "string-like" columns for cell-level transforms.
#: Mirrors the identically-named, identically-justified constant in
#: cleaning_service.py (pandas >= 3.0's dedicated ``str`` dtype vs. the
#: legacy ``object`` dtype). Duplicated locally rather than imported
#: since cleaning_service.py's version is a private module constant and
#: no shared utils module exists yet for this; a natural extraction
#: target once one does.
_STRING_LIKE_DTYPES: Final[list[str]] = ["object", "str"]

#: Column name (post-CleaningService naming convention: lowercase,
#: spaces -> underscores) treated as containing email addresses.
_EMAIL_COLUMN_NAME: Final[str] = "email"


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class NormalizationServiceError(Exception):
    """Base exception for unrecoverable normalization-pipeline failures.

    Reserved for failures that mean the pipeline cannot proceed at all
    (wrong input type, an unexpected exception from within a
    normalization step). Expected, recoverable input problems (e.g. a
    DataFrame with no columns) are represented as a
    ``NormalizationResult`` failure instead of being raised.
    """


class InvalidNormalizationInputError(NormalizationServiceError):
    """Raised when the input to :meth:`NormalizationService.normalize_dataframe` is not a DataFrame.

    This is a caller-contract violation rather than a data-quality
    problem, so it is raised immediately instead of being represented as
    a structured, recoverable failure.
    """


class NormalizationOperationError(NormalizationServiceError):
    """Raised when a normalization step fails with an unexpected exception.

    Indicates a bug in this service or an unsupported DataFrame shape
    that the pipeline's own transformations could not handle, as opposed
    to an expected, recoverable input-quality issue.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class NormalizationStage(str, Enum):
    """Identifies a stage of the normalization pipeline.

    Used both for structured failure reporting (currently only
    ``INPUT_VALIDATION`` can produce a recoverable failure) and for
    stage-by-stage logging, so pipeline progress is observable even on
    the success path.
    """

    INPUT_VALIDATION = "input_validation"
    UNICODE_NORMALIZATION = "unicode_normalization"
    EMAIL_NORMALIZATION = "email_normalization"
    COMPLETE = "complete"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class NormalizationMetadata:
    """Structural statistics describing what a normalization run changed.

    Attributes:
        original_row_count: Row count of the input DataFrame.
        original_column_count: Column count of the input DataFrame.
        final_row_count: Row count of the output DataFrame.
        final_column_count: Column count of the output DataFrame.
        unicode_normalized_cells: Number of string cells whose Unicode
            representation changed under NFKC normalization.
        email_column_detected: The email column's name if one was found
            (currently always ``"email"`` when present), else ``None``.
        emails_normalized: Number of email cells that were lowercased.
            Always 0 if no email column was detected.
    """

    original_row_count: int
    original_column_count: int
    final_row_count: int
    final_column_count: int
    unicode_normalized_cells: int
    email_column_detected: str | None
    emails_normalized: int


@dataclass(frozen=True)
class NormalizationSuccess:
    """Payload returned when the normalization pipeline completes successfully.

    Attributes:
        dataframe: The normalized DataFrame. The input DataFrame passed
            to ``normalize_dataframe()`` is never mutated; this is
            always a new object.
        metadata: Statistics describing what changed during normalization.
    """

    dataframe: pd.DataFrame
    metadata: NormalizationMetadata


@dataclass(frozen=True)
class NormalizationFailure:
    """Payload returned when the normalization pipeline halts before it can run.

    Attributes:
        stage: The stage at which normalization could not proceed.
        reason_code: A short, stable machine-readable failure code.
        message: A human-readable description of the failure.
    """

    stage: NormalizationStage
    reason_code: str
    message: str


@dataclass(frozen=True)
class NormalizationResult:
    """Discriminated result of a normalization pipeline run.

    Exactly one of ``success`` or ``failure`` is populated, indicated by
    ``is_success``; this invariant is enforced in ``__post_init__``.

    Attributes:
        is_success: True if normalization completed successfully.
        success: Populated when ``is_success`` is True.
        failure: Populated when ``is_success`` is False.
    """

    is_success: bool
    success: NormalizationSuccess | None = None
    failure: NormalizationFailure | None = None

    def __post_init__(self) -> None:
        """Validate that exactly one of success/failure is populated.

        Raises:
            ValueError: If ``is_success`` and the populated payload
                disagree.
        """
        if self.is_success and self.success is None:
            raise ValueError(
                "NormalizationResult with is_success=True requires a success payload."
            )
        if not self.is_success and self.failure is None:
            raise ValueError(
                "NormalizationResult with is_success=False requires a failure payload."
            )
        if self.success is not None and self.failure is not None:
            raise ValueError(
                "NormalizationResult cannot have both success and failure populated."
            )

    @classmethod
    def succeeded(
        cls, dataframe: pd.DataFrame, metadata: NormalizationMetadata
    ) -> "NormalizationResult":
        """Build a successful result.

        Args:
            dataframe: The normalized DataFrame.
            metadata: Statistics describing what changed.

        Returns:
            A ``NormalizationResult`` with ``is_success=True``.
        """
        return cls(is_success=True, success=NormalizationSuccess(dataframe, metadata))

    @classmethod
    def failed(
        cls, stage: NormalizationStage, reason_code: str, message: str
    ) -> "NormalizationResult":
        """Build a failed result.

        Args:
            stage: The stage at which normalization halted.
            reason_code: A short, stable machine-readable failure code.
            message: A human-readable description of the failure.

        Returns:
            A ``NormalizationResult`` with ``is_success=False``.
        """
        return cls(is_success=False, failure=NormalizationFailure(stage, reason_code, message))


# --------------------------------------------------------------------------- #
# Normalization Service
# --------------------------------------------------------------------------- #


class NormalizationService:
    """Orchestrates a small, deliberately narrow set of normalization steps.

    See the module docstring for why this implementation is limited to
    Unicode normalization and email lowercasing rather than a broader
    set of operations. Each step returns a *new* DataFrame rather than
    mutating its input, matching ``CleaningService``'s pattern.
    """

    def normalize_dataframe(self, dataframe: pd.DataFrame) -> NormalizationResult:
        """Run the normalization pipeline against an already-cleaned DataFrame.

        Pipeline stages, in order:
            1. Validate the input is a usable DataFrame.
            2. Apply Unicode (NFKC) normalization to all string cells.
            3. Lowercase the "email" column's values, if present.

        Args:
            dataframe: The cleaned DataFrame to normalize (expected to
                be the output of ``CleaningService.clean_dataframe()``).
                Never mutated.

        Returns:
            A ``NormalizationResult``. On success, contains the
            normalized DataFrame and statistics about what changed. On
            failure (currently only possible at input validation),
            contains a structured reason without raising.

        Raises:
            InvalidNormalizationInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance.
            NormalizationOperationError: If a normalization step fails
                with an unexpected exception.
        """
        failure_reason = self._validate_dataframe(dataframe)
        if failure_reason is not None:
            reason_code, message = failure_reason
            logger.warning("Normalization halted at input validation: %s", message)
            return NormalizationResult.failed(
                NormalizationStage.INPUT_VALIDATION, reason_code, message
            )

        original_row_count, original_column_count = dataframe.shape

        try:
            normalized, unicode_normalized_cells = self._normalize_unicode(dataframe)
            self._log_stage(
                NormalizationStage.UNICODE_NORMALIZATION,
                f"cells_changed={unicode_normalized_cells}",
            )

            normalized, email_column_detected, emails_normalized = self._normalize_email_column(
                normalized
            )
            self._log_stage(
                NormalizationStage.EMAIL_NORMALIZATION,
                f"column={email_column_detected} changed={emails_normalized}",
            )
        except NormalizationServiceError:
            raise
        except Exception as exc:
            logger.error("Unexpected failure during DataFrame normalization.", exc_info=True)
            raise NormalizationOperationError(
                f"Unexpected failure while normalizing DataFrame: {exc}"
            ) from exc

        metadata = self._build_metadata(
            original_shape=(original_row_count, original_column_count),
            final_shape=normalized.shape,
            unicode_normalized_cells=unicode_normalized_cells,
            email_column_detected=email_column_detected,
            emails_normalized=emails_normalized,
        )
        self._log_stage(
            NormalizationStage.COMPLETE,
            f"{original_row_count}x{original_column_count} -> "
            f"{metadata.final_row_count}x{metadata.final_column_count}",
        )
        return NormalizationResult.succeeded(normalized, metadata)

    # ----------------------------------------------------------------- #
    # Step 1: Input Validation
    # ----------------------------------------------------------------- #

    def _validate_dataframe(self, dataframe: pd.DataFrame) -> tuple[str, str] | None:
        """Validate that the input is a usable DataFrame.

        Mirrors ``CleaningService._validate_dataframe()`` exactly: a
        wrong input type is a caller-contract violation and is raised
        immediately, while a structurally unusable but correctly-typed
        DataFrame (no columns) is an expected, recoverable condition
        reported back to the caller instead of raised.

        Args:
            dataframe: The value passed to ``normalize_dataframe()``.

        Returns:
            None if the DataFrame is usable, otherwise a
            ``(reason_code, message)`` tuple describing why it isn't.

        Raises:
            InvalidNormalizationInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance at all.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise InvalidNormalizationInputError(
                f"Expected a pandas DataFrame, got {type(dataframe).__name__}."
            )

        if dataframe.shape[1] == 0:
            return "no_columns", "DataFrame has no columns to normalize."

        return None

    # ----------------------------------------------------------------- #
    # Step 2: Unicode Normalization
    # ----------------------------------------------------------------- #

    def _normalize_unicode(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Apply NFKC Unicode normalization to every string cell.

        Note:
            NFKC normalization can collapse compatibility-equivalent
            representations (e.g. full-width vs. half-width characters,
            certain ligatures) into a single canonical form. This is
            standard, expected NFKC behavior -- not data loss in the
            sense of losing information the pipeline cares about -- but
            it does mean the exact original byte sequence is not
            preserved for affected cells.

        Args:
            dataframe: The DataFrame to normalize. Not mutated.

        Returns:
            A tuple of (normalized DataFrame, number of cells changed).
        """
        normalized = dataframe.copy()
        changed_total = 0

        for column in normalized.select_dtypes(include=_STRING_LIKE_DTYPES).columns:
            original = normalized[column]
            is_string_mask = original.map(lambda v: isinstance(v, str))
            transformed = original.map(
                lambda v: unicodedata.normalize("NFKC", v) if isinstance(v, str) else v
            )
            changed_mask = is_string_mask & (original != transformed)
            changed_total += int(changed_mask.sum())
            normalized[column] = transformed

        return normalized, changed_total

    # ----------------------------------------------------------------- #
    # Step 3: Email Normalization
    # ----------------------------------------------------------------- #

    def _normalize_email_column(
        self, dataframe: pd.DataFrame
    ) -> tuple[pd.DataFrame, str | None, int]:
        """Lowercase the "email" column's values, if that column exists.

        Args:
            dataframe: The DataFrame to normalize. Not mutated.

        Returns:
            A tuple of (DataFrame with the email column lowercased if
            present, the detected email column name or None, number of
            cells changed).
        """
        if _EMAIL_COLUMN_NAME not in dataframe.columns:
            return dataframe.copy(), None, 0

        normalized = dataframe.copy()
        original = normalized[_EMAIL_COLUMN_NAME]
        is_string_mask = original.map(lambda v: isinstance(v, str))
        transformed = original.map(lambda v: v.lower() if isinstance(v, str) else v)
        changed_mask = is_string_mask & (original != transformed)
        changed_count = int(changed_mask.sum())
        normalized[_EMAIL_COLUMN_NAME] = transformed

        return normalized, _EMAIL_COLUMN_NAME, changed_count

    # ----------------------------------------------------------------- #
    # Metadata Assembly
    # ----------------------------------------------------------------- #

    def _build_metadata(
        self,
        *,
        original_shape: tuple[int, int],
        final_shape: tuple[int, int],
        unicode_normalized_cells: int,
        email_column_detected: str | None,
        emails_normalized: int,
    ) -> NormalizationMetadata:
        """Assemble structural statistics for a completed normalization run.

        Args:
            original_shape: ``(row_count, column_count)`` of the input
                DataFrame.
            final_shape: ``(row_count, column_count)`` of the normalized
                DataFrame.
            unicode_normalized_cells: Number of cells changed by NFKC
                normalization.
            email_column_detected: The detected email column name, if
                any.
            emails_normalized: Number of email cells lowercased.

        Returns:
            A ``NormalizationMetadata`` combining every statistic
            gathered during the pipeline run.
        """
        original_row_count, original_column_count = original_shape
        final_row_count, final_column_count = final_shape

        return NormalizationMetadata(
            original_row_count=original_row_count,
            original_column_count=original_column_count,
            final_row_count=final_row_count,
            final_column_count=final_column_count,
            unicode_normalized_cells=unicode_normalized_cells,
            email_column_detected=email_column_detected,
            emails_normalized=emails_normalized,
        )

    # ----------------------------------------------------------------- #
    # Logging
    # ----------------------------------------------------------------- #

    @staticmethod
    def _log_stage(stage: NormalizationStage, detail: str) -> None:
        """Emit a consistent, structured log line for a completed stage.

        Args:
            stage: The stage that just completed.
            detail: A short, human-readable summary of what happened.
        """
        logger.info("Normalization stage complete: %s (%s)", stage.value, detail)