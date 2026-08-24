"""DataFrame cleaning orchestration service for the H.I.R.E. backend.

This service applies a fixed sequence of structural, non-semantic
cleaning operations to an already-parsed ``pd.DataFrame``: normalizing
column names, trimming whitespace, normalizing common missing-value
tokens, stripping control characters, and removing empty/duplicate rows.

This module MUST NOT perform normalization beyond the six operations
listed below, preprocessing, feature engineering, type coercion, or any
AI/business analysis. It operates purely on an in-memory DataFrame — no
filesystem access, no database access, no FastAPI dependency. Each
operation is implemented as its own small, single-purpose private
method; the public entry point only sequences them in a fixed order.

Typical usage example:

    service = CleaningService()
    result = service.clean_dataframe(raw_dataframe)

    if result.is_success:
        cleaned_df = result.success.dataframe
        stats = result.success.metadata
    else:
        print(result.failure.stage, result.failure.message)
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

import pandas as pd

logger = logging.getLogger(__name__)

type CleaningStepResult = tuple[pd.DataFrame, int]
"""A DataFrame produced by a cleaning step, paired with the number of
cells (or rows) that step actually changed. Used as the return type for
every step except column-name cleaning, whose "change count" is more
naturally a rename map than an integer.
"""

type ColumnRenameResult = tuple[pd.DataFrame, dict[str, str]]
"""The result of the column-name cleaning step: a DataFrame with cleaned
column names, paired with a map of original name -> cleaned name for
every column that was actually renamed.
"""

#: String tokens treated as representing a missing value once
#: encountered as a standalone cell value. Compared after whitespace
#: trimming has already run earlier in the pipeline, but kept broad here
#: so this step remains correct even if called independently.
_MISSING_VALUE_TOKENS: Final[frozenset[str]] = frozenset(
    {"", " ", "N/A", "NA", "null", "None", "-"}
)

#: Matches ASCII control characters, including but not limited to
#: newline, carriage return, and tab (the C0 control range 0x00-0x1F,
#: plus DEL 0x7F).
_CONTROL_CHARACTER_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1f\x7f]")

#: Dtypes treated as "string-like" columns for cell-level transforms.
#: pandas >= 3.0 introduced a dedicated ``str`` dtype distinct from the
#: legacy ``object`` dtype; both are included explicitly here rather
#: than relying on ``select_dtypes(include="object")`` alone, since that
#: currently includes ``str`` only for backward compatibility and pandas
#: has announced that fallback will be removed in a future release —
#: silently matching zero columns thereafter. Column data produced by
#: this project's csv_utils/excel_utils commonly arrives as one or the
#: other depending on how it was parsed.
_STRING_LIKE_DTYPES: Final[list[str]] = ["object", "str"]


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class CleaningServiceError(Exception):
    """Base exception for unrecoverable cleaning-pipeline failures.

    Reserved for failures that mean the pipeline cannot proceed at all
    (wrong input type, an unexpected exception from within a cleaning
    step). Expected, recoverable input problems (e.g. a DataFrame with
    no columns) are represented as a ``CleaningResult`` failure instead
    of being raised.
    """


class InvalidCleaningInputError(CleaningServiceError):
    """Raised when the input to :meth:`CleaningService.clean_dataframe` is not a DataFrame.

    This is a caller-contract violation rather than a data-quality
    problem, so it is raised immediately instead of being represented as
    a structured, recoverable failure.
    """


class CleaningOperationError(CleaningServiceError):
    """Raised when a cleaning step fails with an unexpected exception.

    Indicates a bug in this service or an unsupported DataFrame shape
    that the pipeline's own transformations could not handle, as opposed
    to an expected, recoverable input-quality issue.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class CleaningStage(str, Enum):
    """Identifies a stage of the cleaning pipeline.

    Used both for structured failure reporting (currently only
    ``INPUT_VALIDATION`` can produce a recoverable failure) and for
    stage-by-stage logging, so pipeline progress is observable even on
    the success path.
    """

    INPUT_VALIDATION = "input_validation"
    COLUMN_NAME_CLEANING = "column_name_cleaning"
    WHITESPACE_TRIM = "whitespace_trim"
    MISSING_VALUE_NORMALIZATION = "missing_value_normalization"
    CONTROL_CHARACTER_REMOVAL = "control_character_removal"
    EMPTY_ROW_REMOVAL = "empty_row_removal"
    DUPLICATE_REMOVAL = "duplicate_removal"
    COMPLETE = "complete"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CleaningMetadata:
    """Structural statistics describing what a cleaning run changed.

    Attributes:
        original_row_count: Row count of the input DataFrame.
        original_column_count: Column count of the input DataFrame.
        final_row_count: Row count of the output DataFrame.
        final_column_count: Column count of the output DataFrame.
        rows_removed: Total rows removed (empty + duplicate), i.e.
            ``original_row_count - final_row_count``.
        empty_rows_removed: Number of rows removed for being completely
            empty.
        duplicate_rows_removed: Number of rows removed as duplicates of
            an earlier row.
        columns_cleaned: Map of original column name -> cleaned column
            name, containing only columns whose name actually changed.
        cells_trimmed: Number of string cells that had leading/trailing
            whitespace removed.
        missing_values_normalized: Number of string cells that matched a
            known missing-value token and were converted to ``pd.NA``.
        control_characters_removed: Number of string cells that had one
            or more control characters removed.
    """

    original_row_count: int
    original_column_count: int
    final_row_count: int
    final_column_count: int
    rows_removed: int
    empty_rows_removed: int
    duplicate_rows_removed: int
    columns_cleaned: dict[str, str]
    cells_trimmed: int
    missing_values_normalized: int
    control_characters_removed: int


@dataclass(frozen=True)
class CleaningSuccess:
    """Payload returned when the cleaning pipeline completes successfully.

    Attributes:
        dataframe: The cleaned DataFrame. The input DataFrame passed to
            ``clean_dataframe()`` is never mutated; this is always a new
            object.
        metadata: Statistics describing what changed during cleaning.
    """

    dataframe: pd.DataFrame
    metadata: CleaningMetadata


@dataclass(frozen=True)
class CleaningFailure:
    """Payload returned when the cleaning pipeline halts before it can run.

    Attributes:
        stage: The stage at which cleaning could not proceed.
        reason_code: A short, stable machine-readable failure code.
        message: A human-readable description of the failure.
    """

    stage: CleaningStage
    reason_code: str
    message: str


@dataclass(frozen=True)
class CleaningResult:
    """Discriminated result of a cleaning pipeline run.

    Exactly one of ``success`` or ``failure`` is populated, indicated by
    ``is_success``; this invariant is enforced in ``__post_init__``.

    Attributes:
        is_success: True if cleaning completed successfully.
        success: Populated when ``is_success`` is True.
        failure: Populated when ``is_success`` is False.
    """

    is_success: bool
    success: CleaningSuccess | None = None
    failure: CleaningFailure | None = None

    def __post_init__(self) -> None:
        """Validate that exactly one of success/failure is populated.

        Raises:
            ValueError: If ``is_success`` and the populated payload
                disagree.
        """
        if self.is_success and self.success is None:
            raise ValueError("CleaningResult with is_success=True requires a success payload.")
        if not self.is_success and self.failure is None:
            raise ValueError("CleaningResult with is_success=False requires a failure payload.")
        if self.success is not None and self.failure is not None:
            raise ValueError("CleaningResult cannot have both success and failure populated.")

    @classmethod
    def succeeded(cls, dataframe: pd.DataFrame, metadata: CleaningMetadata) -> "CleaningResult":
        """Build a successful result.

        Args:
            dataframe: The cleaned DataFrame.
            metadata: Statistics describing what changed.

        Returns:
            A ``CleaningResult`` with ``is_success=True``.
        """
        return cls(is_success=True, success=CleaningSuccess(dataframe, metadata))

    @classmethod
    def failed(cls, stage: CleaningStage, reason_code: str, message: str) -> "CleaningResult":
        """Build a failed result.

        Args:
            stage: The stage at which cleaning halted.
            reason_code: A short, stable machine-readable failure code.
            message: A human-readable description of the failure.

        Returns:
            A ``CleaningResult`` with ``is_success=False``.
        """
        return cls(is_success=False, failure=CleaningFailure(stage, reason_code, message))


# --------------------------------------------------------------------------- #
# Module-Level Pure Helpers
# --------------------------------------------------------------------------- #
#
# Small, stateless, independently testable value transforms. Kept as
# free functions (rather than methods) since they operate on a single
# scalar value and need no service state — mirrors the module-level
# helper pattern already used in csv_utils.py / excel_utils.py.


def _is_effectively_empty(value: Any) -> bool:
    """Determine whether a single cell value should count as "empty".

    A cell counts as empty if it is ``None``, ``pd.NA``/``NaN``, or a
    string containing only whitespace (including the empty string).
    Checking for blank strings here — not just ``pd.NA`` — matters
    because control-character removal runs *after* missing-value
    normalization in the pipeline and can itself produce new blank
    strings (e.g. a cell containing only ``"\\n\\t"``).

    Args:
        value: A single cell value from a DataFrame.

    Returns:
        True if the value should be treated as empty.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------- #
# Cleaning Service
# --------------------------------------------------------------------------- #


class CleaningService:
    """Orchestrates a fixed sequence of structural DataFrame cleaning steps.

    Each step is implemented as its own private method with a single
    responsibility, and each returns a *new* DataFrame rather than
    mutating its input, so the caller's original DataFrame is never
    modified and each step remains independently unit-testable.
    """

    def clean_dataframe(self, dataframe: pd.DataFrame) -> CleaningResult:
        """Run the full cleaning pipeline against a DataFrame.

        Pipeline stages, in order:
            1. Validate the input is a usable DataFrame.
            2. Clean column names (strip, lowercase, spaces -> underscores).
            3. Trim whitespace from all string cells.
            4. Normalize known missing-value tokens to ``pd.NA``.
            5. Remove control characters from all string cells.
            6. Remove rows that are completely empty.
            7. Remove duplicate rows.

        Args:
            dataframe: The DataFrame to clean. Never mutated.

        Returns:
            A ``CleaningResult``. On success, contains the cleaned
            DataFrame and statistics about what changed. On failure
            (currently only possible at input validation), contains a
            structured reason without raising.

        Raises:
            InvalidCleaningInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance.
            CleaningOperationError: If a cleaning step fails with an
                unexpected exception.
        """
        failure_reason = self._validate_dataframe(dataframe)
        if failure_reason is not None:
            reason_code, message = failure_reason
            logger.warning("Cleaning halted at input validation: %s", message)
            return CleaningResult.failed(CleaningStage.INPUT_VALIDATION, reason_code, message)

        original_row_count, original_column_count = dataframe.shape

        try:
            cleaned, columns_cleaned = self._clean_column_names(dataframe)
            self._log_stage(CleaningStage.COLUMN_NAME_CLEANING, f"renamed={len(columns_cleaned)}")

            cleaned, cells_trimmed = self._trim_whitespace(cleaned)
            self._log_stage(CleaningStage.WHITESPACE_TRIM, f"cells_trimmed={cells_trimmed}")

            cleaned, missing_values_normalized = self._normalize_missing_values(cleaned)
            self._log_stage(
                CleaningStage.MISSING_VALUE_NORMALIZATION,
                f"normalized={missing_values_normalized}",
            )

            cleaned, control_characters_removed = self._remove_control_characters(cleaned)
            self._log_stage(
                CleaningStage.CONTROL_CHARACTER_REMOVAL,
                f"cells_affected={control_characters_removed}",
            )

            cleaned, empty_rows_removed = self._remove_empty_rows(cleaned)
            self._log_stage(CleaningStage.EMPTY_ROW_REMOVAL, f"rows_removed={empty_rows_removed}")

            cleaned, duplicate_rows_removed = self._remove_duplicate_rows(cleaned)
            self._log_stage(
                CleaningStage.DUPLICATE_REMOVAL, f"rows_removed={duplicate_rows_removed}"
            )
        except CleaningServiceError:
            raise
        except Exception as exc:
            logger.error("Unexpected failure during DataFrame cleaning.", exc_info=True)
            raise CleaningOperationError(
                f"Unexpected failure while cleaning DataFrame: {exc}"
            ) from exc

        metadata = self._build_metadata(
            original_shape=(original_row_count, original_column_count),
            final_shape=cleaned.shape,
            columns_cleaned=columns_cleaned,
            cells_trimmed=cells_trimmed,
            missing_values_normalized=missing_values_normalized,
            control_characters_removed=control_characters_removed,
            empty_rows_removed=empty_rows_removed,
            duplicate_rows_removed=duplicate_rows_removed,
        )
        self._log_stage(
            CleaningStage.COMPLETE,
            f"{original_row_count}x{original_column_count} -> "
            f"{metadata.final_row_count}x{metadata.final_column_count}",
        )
        return CleaningResult.succeeded(cleaned, metadata)

    # ----------------------------------------------------------------- #
    # Step 1: Input Validation
    # ----------------------------------------------------------------- #

    def _validate_dataframe(self, dataframe: pd.DataFrame) -> tuple[str, str] | None:
        """Validate that the input is a usable DataFrame.

        Two distinct failure modes are handled differently, mirroring
        the pattern used throughout this project (e.g.
        ``upload_service.py``): a wrong input *type* is a caller-contract
        violation and is raised immediately, while a structurally
        unusable but correctly-typed DataFrame (no columns) is an
        expected, recoverable condition reported back to the caller
        instead of raised.

        Args:
            dataframe: The value passed to ``clean_dataframe()``.

        Returns:
            None if the DataFrame is usable, otherwise a
            ``(reason_code, message)`` tuple describing why it isn't.

        Raises:
            InvalidCleaningInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance at all.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise InvalidCleaningInputError(
                f"Expected a pandas DataFrame, got {type(dataframe).__name__}."
            )

        if dataframe.shape[1] == 0:
            return "no_columns", "DataFrame has no columns to clean."

        return None

    # ----------------------------------------------------------------- #
    # Step 2: Column Name Cleaning
    # ----------------------------------------------------------------- #

    def _clean_column_names(self, dataframe: pd.DataFrame) -> ColumnRenameResult:
        """Strip, lowercase, and underscore-ify every column name.

        Note:
            If two columns collapse to the same cleaned name (e.g.
            ``"Name"`` and ``"name "`` both become ``"name"``), pandas
            will silently permit the resulting duplicate column labels.
            Detecting or resolving that collision is a validation
            concern, not a cleaning one, and is intentionally left to
            the caller / ``validators.py``.

        Args:
            dataframe: The DataFrame whose columns should be renamed.

        Returns:
            A tuple of (DataFrame with cleaned column names, map of
            original name -> cleaned name for every renamed column).
        """
        cleaned = dataframe.copy()
        renamed: dict[str, str] = {}
        new_columns: list[str] = []

        for column in cleaned.columns:
            original_name = str(column)
            cleaned_name = original_name.strip().lower().replace(" ", "_")
            new_columns.append(cleaned_name)
            if cleaned_name != original_name:
                renamed[original_name] = cleaned_name

        cleaned.columns = pd.Index(new_columns)
        return cleaned, renamed

    # ----------------------------------------------------------------- #
    # Steps 3 & 5: String-to-String Cell Transforms
    # ----------------------------------------------------------------- #

    def _apply_elementwise_string_transform(
        self,
        dataframe: pd.DataFrame,
        transform: Callable[[str], str],
    ) -> CleaningStepResult:
        """Apply a string -> string transform to every string cell.

        Shared by whitespace trimming and control-character removal,
        since both have identical shape: visit every object-dtype
        column, transform string cells only, leave everything else
        untouched, and count how many cells actually changed.

        This helper is only safe for transforms that always map a
        string to another string (never to ``pd.NA``): the change count
        is computed via equality comparison, and comparing against
        ``pd.NA`` does not yield a usable boolean mask. Missing-value
        normalization therefore uses its own logic instead of this
        helper — see :meth:`_normalize_missing_values`.

        Args:
            dataframe: The DataFrame to transform. Not mutated.
            transform: A function applied to each string cell.

        Returns:
            A tuple of (transformed DataFrame, number of cells changed).
        """
        cleaned = dataframe.copy()
        changed_total = 0

        for column in cleaned.select_dtypes(include=_STRING_LIKE_DTYPES).columns:
            original = cleaned[column]
            is_string_mask = original.map(lambda v: isinstance(v, str))
            transformed = original.map(lambda v: transform(v) if isinstance(v, str) else v)
            changed_mask = is_string_mask & (original != transformed)
            changed_total += int(changed_mask.sum())
            cleaned[column] = transformed

        return cleaned, changed_total

    def _trim_whitespace(self, dataframe: pd.DataFrame) -> CleaningStepResult:
        """Strip leading/trailing whitespace from every string cell.

        Args:
            dataframe: The DataFrame to trim. Not mutated.

        Returns:
            A tuple of (trimmed DataFrame, number of cells changed).
        """
        return self._apply_elementwise_string_transform(dataframe, str.strip)

    def _remove_control_characters(self, dataframe: pd.DataFrame) -> CleaningStepResult:
        """Remove control characters (e.g. \\n, \\r, \\t) from every string cell.

        Args:
            dataframe: The DataFrame to clean. Not mutated.

        Returns:
            A tuple of (cleaned DataFrame, number of cells changed).
        """
        return self._apply_elementwise_string_transform(
            dataframe, lambda value: _CONTROL_CHARACTER_PATTERN.sub("", value)
        )

    # ----------------------------------------------------------------- #
    # Step 4: Missing-Value Normalization
    # ----------------------------------------------------------------- #

    def _normalize_missing_values(self, dataframe: pd.DataFrame) -> CleaningStepResult:
        """Convert known missing-value string tokens to ``pd.NA``.

        Implemented separately from
        :meth:`_apply_elementwise_string_transform` because this
        transform maps matching cells to ``pd.NA`` rather than another
        string; the change mask is built from token membership rather
        than an equality comparison against the transformed value; using
        ``!=`` against ``pd.NA`` would not produce a usable boolean mask.

        Args:
            dataframe: The DataFrame to normalize. Not mutated.

        Returns:
            A tuple of (normalized DataFrame, number of cells changed).
        """
        cleaned = dataframe.copy()
        normalized_total = 0

        for column in cleaned.select_dtypes(include=_STRING_LIKE_DTYPES).columns:
            original = cleaned[column]
            is_missing_token = original.map(
                lambda v: isinstance(v, str) and v in _MISSING_VALUE_TOKENS
            )
            normalized_total += int(is_missing_token.sum())
            cleaned[column] = original.where(~is_missing_token, pd.NA)

        return cleaned, normalized_total

    # ----------------------------------------------------------------- #
    # Step 6: Empty Row Removal
    # ----------------------------------------------------------------- #

    def _remove_empty_rows(self, dataframe: pd.DataFrame) -> CleaningStepResult:
        """Remove rows in which every cell is empty.

        A row counts as empty if every cell satisfies
        :func:`_is_effectively_empty` — i.e. ``pd.NA``, ``None``, or a
        whitespace-only string.

        Args:
            dataframe: The DataFrame to filter. Not mutated.

        Returns:
            A tuple of (filtered DataFrame with a reset index, number of
            rows removed).
        """
        if dataframe.empty:
            return dataframe.copy(), 0

        empty_row_mask = dataframe.apply(
            lambda row: all(_is_effectively_empty(value) for value in row), axis=1
        )
        removed = int(empty_row_mask.sum())
        cleaned = dataframe.loc[~empty_row_mask].reset_index(drop=True)
        return cleaned, removed

    # ----------------------------------------------------------------- #
    # Step 7: Duplicate Row Removal
    # ----------------------------------------------------------------- #

    def _remove_duplicate_rows(self, dataframe: pd.DataFrame) -> CleaningStepResult:
        """Remove duplicate rows, keeping the first occurrence of each.

        Args:
            dataframe: The DataFrame to deduplicate. Not mutated.

        Returns:
            A tuple of (deduplicated DataFrame with a reset index,
            number of rows removed).
        """
        row_count_before = len(dataframe)
        cleaned = dataframe.drop_duplicates(keep="first").reset_index(drop=True)
        removed = row_count_before - len(cleaned)
        return cleaned, removed

    # ----------------------------------------------------------------- #
    # Step 8: Metadata Assembly
    # ----------------------------------------------------------------- #

    def _build_metadata(
        self,
        *,
        original_shape: tuple[int, int],
        final_shape: tuple[int, int],
        columns_cleaned: dict[str, str],
        cells_trimmed: int,
        missing_values_normalized: int,
        control_characters_removed: int,
        empty_rows_removed: int,
        duplicate_rows_removed: int,
    ) -> CleaningMetadata:
        """Assemble structural statistics for a completed cleaning run.

        Args:
            original_shape: ``(row_count, column_count)`` of the input
                DataFrame.
            final_shape: ``(row_count, column_count)`` of the cleaned
                DataFrame.
            columns_cleaned: Map of original column name -> cleaned name
                for every column that was renamed.
            cells_trimmed: Number of cells that had whitespace trimmed.
            missing_values_normalized: Number of cells converted to
                ``pd.NA``.
            control_characters_removed: Number of cells that had control
                characters removed.
            empty_rows_removed: Number of completely empty rows removed.
            duplicate_rows_removed: Number of duplicate rows removed.

        Returns:
            A ``CleaningMetadata`` combining every statistic gathered
            during the pipeline run.
        """
        original_row_count, original_column_count = original_shape
        final_row_count, final_column_count = final_shape

        return CleaningMetadata(
            original_row_count=original_row_count,
            original_column_count=original_column_count,
            final_row_count=final_row_count,
            final_column_count=final_column_count,
            rows_removed=original_row_count - final_row_count,
            empty_rows_removed=empty_rows_removed,
            duplicate_rows_removed=duplicate_rows_removed,
            columns_cleaned=columns_cleaned,
            cells_trimmed=cells_trimmed,
            missing_values_normalized=missing_values_normalized,
            control_characters_removed=control_characters_removed,
        )

    # ----------------------------------------------------------------- #
    # Logging
    # ----------------------------------------------------------------- #

    @staticmethod
    def _log_stage(stage: CleaningStage, detail: str) -> None:
        """Emit a consistent, structured log line for a completed stage.

        Args:
            stage: The stage that just completed.
            detail: A short, human-readable summary of what happened.
        """
        logger.info("Cleaning stage complete: %s (%s)", stage.value, detail)