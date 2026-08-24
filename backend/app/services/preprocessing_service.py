"""DataFrame preprocessing orchestration service for the H.I.R.E. backend.

This service runs as the pipeline stage immediately after
``normalization_service.py`` and before AI/data processing
(``ai_data_service.py``). It prepares an already-normalized
``pd.DataFrame`` for downstream numeric/analytical consumption without
performing any AI or business-specific transformation itself.

.. IMPORTANT -- DOCUMENTED ASSUMPTIONS ::

    No project documentation defines a concrete "Preprocessing" contract
    for this pipeline (the only mention anywhere is a single unlabeled
    box in 07_AI_ENGINE_SPECIFICATION.md's generic LLM request flow, with
    zero elaboration), and ``ai_data_service.py`` -- which would clarify
    what shape this stage's output actually needs to be in -- was not
    available at the time this file was written despite repeated
    requests. Rather than invent broad business logic, this
    implementation is intentionally narrow and limited to two operations
    that are safe and useful regardless of what AI/data processing turns
    out to need:

    1. Dtype inference: CSV-sourced columns arrive as strings even after
       cleaning and normalization (neither of those stages touches
       dtypes). Any downstream numeric or date-based operation needs
       real dtypes, not strings, so this stage attempts a safe cast --
       only applied to a column when *every* non-null value converts
       cleanly, never a partial/lossy coercion.
    2. Index reset: trivial structural hygiene, ensuring a clean
       contiguous index for whatever consumes this DataFrame next.

    Explicitly NOT implemented, since no specification exists to justify
    it: column selection/dropping, feature construction, encoding
    (one-hot, ordinal, etc.), scaling/normalization of numeric ranges,
    or any AI-specific reshaping. Those belong to ``ai_data_service.py``
    (feature engineering / AI data prep), once its real contract is
    available. If ``ai_data_service.py``'s actual requirements differ
    from what's implemented here, this file will need to be revised.

This module MUST NOT duplicate upload, validation, cleaning, or
normalization responsibilities, and MUST NOT implement AI/model logic.
It operates purely on an in-memory DataFrame -- no filesystem access, no
database access, no FastAPI dependency.

Typical usage example:

    service = PreprocessingService()
    result = service.preprocess_dataframe(normalized_dataframe)

    if result.is_success:
        ready_df = result.success.dataframe
        stats = result.success.metadata
    else:
        print(result.failure.stage, result.failure.message)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Final

import pandas as pd

logger = logging.getLogger(__name__)

#: Dtypes treated as "string-like" columns for dtype-inference scanning.
#: Mirrors the identically-justified constant in cleaning_service.py /
#: normalization_service.py (pandas >= 3.0's dedicated ``str`` dtype vs.
#: the legacy ``object`` dtype). Duplicated locally rather than shared
#: since no common utils module exists yet for this.
_STRING_LIKE_DTYPES: Final[list[str]] = ["object", "str"]


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class PreprocessingServiceError(Exception):
    """Base exception for unrecoverable preprocessing-pipeline failures.

    Reserved for failures that mean the pipeline cannot proceed at all
    (wrong input type, an unexpected exception from within a
    preprocessing step). Expected, recoverable input problems (e.g. a
    DataFrame with no columns) are represented as a
    ``PreprocessingResult`` failure instead of being raised.
    """


class InvalidPreprocessingInputError(PreprocessingServiceError):
    """Raised when the input to :meth:`PreprocessingService.preprocess_dataframe` is not a DataFrame.

    This is a caller-contract violation rather than a data-quality
    problem, so it is raised immediately instead of being represented as
    a structured, recoverable failure.
    """


class PreprocessingOperationError(PreprocessingServiceError):
    """Raised when a preprocessing step fails with an unexpected exception.

    Indicates a bug in this service or a DataFrame shape it could not
    handle, as opposed to an expected, recoverable input-quality issue.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class PreprocessingStage(str, Enum):
    """Identifies a stage of the preprocessing pipeline.

    Used both for structured failure reporting (currently only
    ``INPUT_VALIDATION`` can produce a recoverable failure) and for
    stage-by-stage logging, so pipeline progress is observable even on
    the success path.
    """

    INPUT_VALIDATION = "input_validation"
    DTYPE_INFERENCE = "dtype_inference"
    INDEX_RESET = "index_reset"
    COMPLETE = "complete"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PreprocessingMetadata:
    """Structural statistics describing what a preprocessing run changed.

    Attributes:
        original_row_count: Row count of the input DataFrame.
        original_column_count: Column count of the input DataFrame.
        final_row_count: Row count of the output DataFrame.
        final_column_count: Column count of the output DataFrame.
        inferred_dtypes: Map of column name -> newly inferred dtype
            name, containing only columns whose dtype actually changed.
    """

    original_row_count: int
    original_column_count: int
    final_row_count: int
    final_column_count: int
    inferred_dtypes: dict[str, str]


@dataclass(frozen=True)
class PreprocessingSuccess:
    """Payload returned when the preprocessing pipeline completes successfully.

    Attributes:
        dataframe: The preprocessed DataFrame. The input DataFrame
            passed to ``preprocess_dataframe()`` is never mutated; this
            is always a new object.
        metadata: Statistics describing what changed during preprocessing.
    """

    dataframe: pd.DataFrame
    metadata: PreprocessingMetadata


@dataclass(frozen=True)
class PreprocessingFailure:
    """Payload returned when the preprocessing pipeline halts before it can run.

    Attributes:
        stage: The stage at which preprocessing could not proceed.
        reason_code: A short, stable machine-readable failure code.
        message: A human-readable description of the failure.
    """

    stage: PreprocessingStage
    reason_code: str
    message: str


@dataclass(frozen=True)
class PreprocessingResult:
    """Discriminated result of a preprocessing pipeline run.

    Exactly one of ``success`` or ``failure`` is populated, indicated by
    ``is_success``; this invariant is enforced in ``__post_init__``.

    Attributes:
        is_success: True if preprocessing completed successfully.
        success: Populated when ``is_success`` is True.
        failure: Populated when ``is_success`` is False.
    """

    is_success: bool
    success: PreprocessingSuccess | None = None
    failure: PreprocessingFailure | None = None

    def __post_init__(self) -> None:
        """Validate that exactly one of success/failure is populated.

        Raises:
            ValueError: If ``is_success`` and the populated payload
                disagree.
        """
        if self.is_success and self.success is None:
            raise ValueError(
                "PreprocessingResult with is_success=True requires a success payload."
            )
        if not self.is_success and self.failure is None:
            raise ValueError(
                "PreprocessingResult with is_success=False requires a failure payload."
            )
        if self.success is not None and self.failure is not None:
            raise ValueError(
                "PreprocessingResult cannot have both success and failure populated."
            )

    @classmethod
    def succeeded(
        cls, dataframe: pd.DataFrame, metadata: PreprocessingMetadata
    ) -> "PreprocessingResult":
        """Build a successful result.

        Args:
            dataframe: The preprocessed DataFrame.
            metadata: Statistics describing what changed.

        Returns:
            A ``PreprocessingResult`` with ``is_success=True``.
        """
        return cls(is_success=True, success=PreprocessingSuccess(dataframe, metadata))

    @classmethod
    def failed(
        cls, stage: PreprocessingStage, reason_code: str, message: str
    ) -> "PreprocessingResult":
        """Build a failed result.

        Args:
            stage: The stage at which preprocessing halted.
            reason_code: A short, stable machine-readable failure code.
            message: A human-readable description of the failure.

        Returns:
            A ``PreprocessingResult`` with ``is_success=False``.
        """
        return cls(is_success=False, failure=PreprocessingFailure(stage, reason_code, message))


# --------------------------------------------------------------------------- #
# Preprocessing Service
# --------------------------------------------------------------------------- #


class PreprocessingService:
    """Orchestrates a small, deliberately narrow set of preprocessing steps.

    See the module docstring for why this implementation is limited to
    dtype inference and index reset rather than a broader set of
    operations (e.g. feature engineering, which belongs to
    ``ai_data_service.py``). Each step returns a *new* DataFrame rather
    than mutating its input, matching ``CleaningService`` and
    ``NormalizationService``'s pattern.
    """

    def preprocess_dataframe(self, dataframe: pd.DataFrame) -> PreprocessingResult:
        """Run the preprocessing pipeline against an already-normalized DataFrame.

        Pipeline stages, in order:
            1. Validate the input is a usable DataFrame.
            2. Infer and cast more specific dtypes for string columns.
            3. Reset the DataFrame index.

        Args:
            dataframe: The normalized DataFrame to preprocess (expected
                to be the output of
                ``NormalizationService.normalize_dataframe()``). Never
                mutated.

        Returns:
            A ``PreprocessingResult``. On success, contains the
            preprocessed DataFrame and statistics about what changed. On
            failure (currently only possible at input validation),
            contains a structured reason without raising.

        Raises:
            InvalidPreprocessingInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance.
            PreprocessingOperationError: If a preprocessing step fails
                with an unexpected exception.
        """
        failure_reason = self._validate_dataframe(dataframe)
        if failure_reason is not None:
            reason_code, message = failure_reason
            logger.warning("Preprocessing halted at input validation: %s", message)
            return PreprocessingResult.failed(
                PreprocessingStage.INPUT_VALIDATION, reason_code, message
            )

        original_row_count, original_column_count = dataframe.shape

        try:
            processed, inferred_dtypes = self._infer_dtypes(dataframe)
            self._log_stage(PreprocessingStage.DTYPE_INFERENCE, f"inferred={len(inferred_dtypes)}")

            processed = self._reset_index(processed)
            self._log_stage(PreprocessingStage.INDEX_RESET, f"rows={len(processed)}")
        except PreprocessingServiceError:
            raise
        except Exception as exc:
            logger.error("Unexpected failure during DataFrame preprocessing.", exc_info=True)
            raise PreprocessingOperationError(
                f"Unexpected failure while preprocessing DataFrame: {exc}"
            ) from exc

        metadata = self._build_metadata(
            original_shape=(original_row_count, original_column_count),
            final_shape=processed.shape,
            inferred_dtypes=inferred_dtypes,
        )
        self._log_stage(
            PreprocessingStage.COMPLETE,
            f"{original_row_count}x{original_column_count} -> "
            f"{metadata.final_row_count}x{metadata.final_column_count}",
        )
        return PreprocessingResult.succeeded(processed, metadata)

    # ----------------------------------------------------------------- #
    # Step 1: Input Validation
    # ----------------------------------------------------------------- #

    def _validate_dataframe(self, dataframe: pd.DataFrame) -> tuple[str, str] | None:
        """Validate that the input is a usable DataFrame.

        Mirrors ``CleaningService`` / ``NormalizationService``'s
        ``_validate_dataframe()`` exactly: a wrong input type is a
        caller-contract violation and is raised immediately, while a
        structurally unusable but correctly-typed DataFrame (no columns)
        is an expected, recoverable condition reported back to the
        caller instead of raised.

        Args:
            dataframe: The value passed to ``preprocess_dataframe()``.

        Returns:
            None if the DataFrame is usable, otherwise a
            ``(reason_code, message)`` tuple describing why it isn't.

        Raises:
            InvalidPreprocessingInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance at all.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise InvalidPreprocessingInputError(
                f"Expected a pandas DataFrame, got {type(dataframe).__name__}."
            )

        if dataframe.shape[1] == 0:
            return "no_columns", "DataFrame has no columns to preprocess."

        return None

    # ----------------------------------------------------------------- #
    # Step 2: Dtype Inference
    # ----------------------------------------------------------------- #

    def _infer_dtypes(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        """Attempt to infer and cast a more specific dtype for each string column.

        For each string-like column, tries numeric conversion, then
        datetime conversion; a column is only cast if every non-null
        value converts successfully. Columns that fail both, or that are
        already non-string dtypes (e.g. Excel-sourced numeric/bool/date
        columns, which cleaning and normalization never touch), are left
        unchanged.

        Args:
            dataframe: The DataFrame whose columns should be
                type-inferred. Not mutated.

        Returns:
            A tuple of (DataFrame with inferred dtypes applied, a map of
            column name -> new dtype name for every column that was
            actually cast).
        """
        processed = dataframe.copy()
        changed: dict[str, str] = {}

        for column in processed.select_dtypes(include=_STRING_LIKE_DTYPES).columns:
            series = processed[column]
            non_null = series.dropna()
            if non_null.empty:
                continue

            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().sum() == non_null.shape[0]:
                processed[column] = numeric
                changed[str(column)] = str(numeric.dtype)
                continue

            datetime_series = pd.to_datetime(series, errors="coerce", format="mixed")
            if datetime_series.notna().sum() == non_null.shape[0]:
                processed[column] = datetime_series
                changed[str(column)] = str(datetime_series.dtype)

        return processed, changed

    # ----------------------------------------------------------------- #
    # Step 3: Index Reset
    # ----------------------------------------------------------------- #

    def _reset_index(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Reset the DataFrame's index to a clean 0..n-1 range.

        Args:
            dataframe: The DataFrame to reindex. Not mutated.

        Returns:
            A new DataFrame with a fresh, contiguous integer index.
        """
        return dataframe.reset_index(drop=True)

    # ----------------------------------------------------------------- #
    # Metadata Assembly
    # ----------------------------------------------------------------- #

    def _build_metadata(
        self,
        *,
        original_shape: tuple[int, int],
        final_shape: tuple[int, int],
        inferred_dtypes: dict[str, str],
    ) -> PreprocessingMetadata:
        """Assemble structural statistics for a completed preprocessing run.

        Args:
            original_shape: ``(row_count, column_count)`` of the input
                DataFrame.
            final_shape: ``(row_count, column_count)`` of the
                preprocessed DataFrame.
            inferred_dtypes: Map of column name -> newly inferred dtype
                name for every column whose dtype changed.

        Returns:
            A ``PreprocessingMetadata`` combining every statistic
            gathered during the pipeline run.
        """
        original_row_count, original_column_count = original_shape
        final_row_count, final_column_count = final_shape

        return PreprocessingMetadata(
            original_row_count=original_row_count,
            original_column_count=original_column_count,
            final_row_count=final_row_count,
            final_column_count=final_column_count,
            inferred_dtypes=inferred_dtypes,
        )

    # ----------------------------------------------------------------- #
    # Logging
    # ----------------------------------------------------------------- #

    @staticmethod
    def _log_stage(stage: PreprocessingStage, detail: str) -> None:
        """Emit a consistent, structured log line for a completed stage.

        Args:
            stage: The stage that just completed.
            detail: A short, human-readable summary of what happened.
        """
        logger.info("Preprocessing stage complete: %s (%s)", stage.value, detail)