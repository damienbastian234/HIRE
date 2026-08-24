"""AI data preparation orchestration service for the H.I.R.E. backend.

This service is the final stage of the Data Ingestion Pipeline, running
immediately after ``preprocessing_service.py`` and handing off to the
(not-yet-implemented) AI engines described in
06_AI_ARCHITECTURE.md / 07_AI_ENGINE_SPECIFICATION.md.

.. IMPORTANT -- DOCUMENTED ASSUMPTIONS ::

    No project documentation defines a concrete "AI Data Processing"
    contract, and this file was written without ever receiving an
    existing skeleton for it (repeated requests across multiple prior
    tasks did not produce one). Rather than invent AI/ML behavior, this
    implementation is limited to a single, narrowly-justified data-shape
    transformation, grounded directly in two facts that ARE documented:

    1. Every AI engine in 07_AI_ENGINE_SPECIFICATION.md and
       12_PROMPT_LIBRARY.md communicates via strict JSON -- e.g. the
       "Standard AI Response Contract"'s ``"data": {}`` field, and every
       prompt template's "Output Format: Strict JSON" section. pandas
       DataFrames are not JSON-serializable as-is (NaN/NaT, Timestamp,
       and numpy scalar types all fail standard ``json.dumps()``).
    2. Every AI engine in 06_AI_ARCHITECTURE.md operates on a single
       candidate/resume at a time (e.g. the Resume Intelligence Engine
       takes one "Structured Resume Object"), not a bulk table.

    Together these justify exactly one operation: converting the
    preprocessed DataFrame into a list of per-row, JSON-safe dicts, so
    that whatever future AI engine implementation exists can iterate
    over candidates and pass each one directly into a JSON-based prompt
    call without needing to know anything about pandas.

    This is also the FIRST type-shape change in the pipeline -- every
    prior stage (Cleaning, Normalization, Preprocessing) is
    DataFrame -> DataFrame; this stage is deliberately DataFrame ->
    list[dict[str, Any]], since a DataFrame is not what a per-candidate
    AI engine call consumes. This is a documented, deliberate departure
    from the DataFrame-in/DataFrame-out convention used elsewhere in
    this pipeline, not an oversight.

    Explicitly NOT implemented, since nothing in the repository specifies
    it: any AI/LLM API call, embeddings, feature vectors for a model,
    scoring, matching, or ranking logic. Those belong to a genuine future
    AI engine layer once one exists.

This module MUST NOT duplicate upload, validation, cleaning,
normalization, or preprocessing responsibilities. It operates purely on
an in-memory DataFrame -- no filesystem access, no database access, no
FastAPI dependency, no external API calls.

Typical usage example:

    service = AIDataService()
    result = service.prepare_for_ai(preprocessed_dataframe)

    if result.is_success:
        for record in result.success.records:
            pass  # hand each record to a future AI engine call
    else:
        print(result.failure.stage, result.failure.message)
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #


class AIDataServiceError(Exception):
    """Base exception for unrecoverable AI-data-preparation failures.

    Reserved for failures that mean the pipeline cannot proceed at all
    (wrong input type, an unexpected exception during conversion).
    Expected, recoverable input problems (e.g. a DataFrame with no
    columns) are represented as an ``AIDataResult`` failure instead of
    being raised.
    """


class InvalidAIDataInputError(AIDataServiceError):
    """Raised when the input to :meth:`AIDataService.prepare_for_ai` is not a DataFrame.

    This is a caller-contract violation rather than a data-quality
    problem, so it is raised immediately instead of being represented as
    a structured, recoverable failure.
    """


class AIDataOperationError(AIDataServiceError):
    """Raised when record conversion fails with an unexpected exception.

    Indicates a bug in this service or a DataFrame shape/value it could
    not handle, as opposed to an expected, recoverable input-quality
    issue.
    """


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class AIDataStage(str, Enum):
    """Identifies a stage of the AI data preparation pipeline.

    Used both for structured failure reporting (currently only
    ``INPUT_VALIDATION`` can produce a recoverable failure) and for
    stage-by-stage logging, so pipeline progress is observable even on
    the success path.
    """

    INPUT_VALIDATION = "input_validation"
    RECORD_CONVERSION = "record_conversion"
    COMPLETE = "complete"


# --------------------------------------------------------------------------- #
# Data Transfer Objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AIDataMetadata:
    """Structural statistics describing a completed AI-data-preparation run.

    Attributes:
        original_row_count: Row count of the input DataFrame.
        original_column_count: Column count of the input DataFrame.
        record_count: Number of records produced (equals
            ``original_row_count``).
        field_names: Column names, in order, present in every record.
        json_unsafe_values_converted: Number of individual cell values
            that were not natively JSON-safe (``pd.NA``/``NaT``,
            ``pd.Timestamp``, numpy scalar types) and were converted.
    """

    original_row_count: int
    original_column_count: int
    record_count: int
    field_names: tuple[str, ...]
    json_unsafe_values_converted: int


@dataclass(frozen=True)
class AIDataSuccess:
    """Payload returned when AI data preparation completes successfully.

    Attributes:
        records: One JSON-safe dict per input row, in row order. Ready
            to be passed directly to a future per-candidate AI engine
            call without further pandas-specific handling.
        metadata: Statistics describing the conversion.
    """

    records: list[dict[str, Any]]
    metadata: AIDataMetadata


@dataclass(frozen=True)
class AIDataFailure:
    """Payload returned when AI data preparation halts before it can run.

    Attributes:
        stage: The stage at which preparation could not proceed.
        reason_code: A short, stable machine-readable failure code.
        message: A human-readable description of the failure.
    """

    stage: AIDataStage
    reason_code: str
    message: str


@dataclass(frozen=True)
class AIDataResult:
    """Discriminated result of an AI-data-preparation run.

    Exactly one of ``success`` or ``failure`` is populated, indicated by
    ``is_success``; this invariant is enforced in ``__post_init__``.

    Attributes:
        is_success: True if preparation completed successfully.
        success: Populated when ``is_success`` is True.
        failure: Populated when ``is_success`` is False.
    """

    is_success: bool
    success: AIDataSuccess | None = None
    failure: AIDataFailure | None = None

    def __post_init__(self) -> None:
        """Validate that exactly one of success/failure is populated.

        Raises:
            ValueError: If ``is_success`` and the populated payload
                disagree.
        """
        if self.is_success and self.success is None:
            raise ValueError("AIDataResult with is_success=True requires a success payload.")
        if not self.is_success and self.failure is None:
            raise ValueError("AIDataResult with is_success=False requires a failure payload.")
        if self.success is not None and self.failure is not None:
            raise ValueError("AIDataResult cannot have both success and failure populated.")

    @classmethod
    def succeeded(
        cls, records: list[dict[str, Any]], metadata: AIDataMetadata
    ) -> "AIDataResult":
        """Build a successful result.

        Args:
            records: The JSON-safe records produced.
            metadata: Statistics describing the conversion.

        Returns:
            An ``AIDataResult`` with ``is_success=True``.
        """
        return cls(is_success=True, success=AIDataSuccess(records, metadata))

    @classmethod
    def failed(cls, stage: AIDataStage, reason_code: str, message: str) -> "AIDataResult":
        """Build a failed result.

        Args:
            stage: The stage at which preparation halted.
            reason_code: A short, stable machine-readable failure code.
            message: A human-readable description of the failure.

        Returns:
            An ``AIDataResult`` with ``is_success=False``.
        """
        return cls(is_success=False, failure=AIDataFailure(stage, reason_code, message))


# --------------------------------------------------------------------------- #
# AI Data Service
# --------------------------------------------------------------------------- #


class AIDataService:
    """Converts a preprocessed DataFrame into JSON-safe, per-record data.

    See the module docstring for why this is the only operation
    implemented. Does not mutate its input DataFrame.
    """

    def prepare_for_ai(self, dataframe: pd.DataFrame) -> AIDataResult:
        """Convert an already-preprocessed DataFrame into JSON-safe records.

        Pipeline stages, in order:
            1. Validate the input is a usable DataFrame.
            2. Convert each row into a JSON-safe dict.

        Args:
            dataframe: The preprocessed DataFrame to convert (expected
                to be the output of
                ``PreprocessingService.preprocess_dataframe()``). Never
                mutated.

        Returns:
            An ``AIDataResult``. On success, contains the list of
            JSON-safe records and conversion statistics. On failure
            (currently only possible at input validation), contains a
            structured reason without raising.

        Raises:
            InvalidAIDataInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance.
            AIDataOperationError: If record conversion fails with an
                unexpected exception.
        """
        failure_reason = self._validate_dataframe(dataframe)
        if failure_reason is not None:
            reason_code, message = failure_reason
            logger.warning("AI data preparation halted at input validation: %s", message)
            return AIDataResult.failed(AIDataStage.INPUT_VALIDATION, reason_code, message)

        original_row_count, original_column_count = dataframe.shape

        try:
            records, json_unsafe_values_converted = self._convert_to_json_safe_records(dataframe)
            self._log_stage(
                AIDataStage.RECORD_CONVERSION,
                f"records={len(records)} values_converted={json_unsafe_values_converted}",
            )
        except AIDataServiceError:
            raise
        except Exception as exc:
            logger.error("Unexpected failure during AI data preparation.", exc_info=True)
            raise AIDataOperationError(
                f"Unexpected failure while preparing records: {exc}"
            ) from exc

        metadata = self._build_metadata(
            original_row_count=original_row_count,
            original_column_count=original_column_count,
            records=records,
            field_names=tuple(str(column) for column in dataframe.columns),
            json_unsafe_values_converted=json_unsafe_values_converted,
        )
        self._log_stage(AIDataStage.COMPLETE, f"record_count={metadata.record_count}")
        return AIDataResult.succeeded(records, metadata)

    # ----------------------------------------------------------------- #
    # Step 1: Input Validation
    # ----------------------------------------------------------------- #

    def _validate_dataframe(self, dataframe: pd.DataFrame) -> tuple[str, str] | None:
        """Validate that the input is a usable DataFrame.

        Mirrors the ``_validate_dataframe()`` pattern established by
        ``CleaningService`` / ``NormalizationService`` /
        ``PreprocessingService``: a wrong input type is a
        caller-contract violation and is raised immediately, while a
        structurally unusable but correctly-typed DataFrame (no columns)
        is an expected, recoverable condition reported back to the
        caller instead of raised.

        Args:
            dataframe: The value passed to ``prepare_for_ai()``.

        Returns:
            None if the DataFrame is usable, otherwise a
            ``(reason_code, message)`` tuple describing why it isn't.

        Raises:
            InvalidAIDataInputError: If ``dataframe`` is not a
                ``pd.DataFrame`` instance at all.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise InvalidAIDataInputError(
                f"Expected a pandas DataFrame, got {type(dataframe).__name__}."
            )

        if dataframe.shape[1] == 0:
            return "no_columns", "DataFrame has no columns to prepare."

        return None

    # ----------------------------------------------------------------- #
    # Step 2: Record Conversion
    # ----------------------------------------------------------------- #

    def _convert_to_json_safe_records(
        self, dataframe: pd.DataFrame
    ) -> tuple[list[dict[str, Any]], int]:
        """Convert a DataFrame into a list of JSON-safe per-row dicts.

        Args:
            dataframe: The DataFrame to convert. Not mutated.

        Returns:
            A tuple of (list of JSON-safe records, number of individual
            cell values that required conversion).
        """
        raw_records = dataframe.to_dict(orient="records")
        safe_records: list[dict[str, Any]] = []
        converted_total = 0

        for raw_record in raw_records:
            safe_record: dict[str, Any] = {}
            for key, value in raw_record.items():
                safe_value, was_converted = self._to_json_safe_value(value)
                safe_record[str(key)] = safe_value
                if was_converted:
                    converted_total += 1
            safe_records.append(safe_record)

        return safe_records, converted_total

    @staticmethod
    def _to_json_safe_value(value: Any) -> tuple[Any, bool]:
        """Convert a single cell value into a JSON-safe equivalent.

        Handles every value category ``json.dumps()`` cannot serialize
        natively:

        - ``pd.NA``, ``NaN`` (Python float, numpy float), and ``pd.NaT``
          all convert to ``None``. These are checked first via
          ``pd.isna()`` rather than type-specific branches, since
          ``pd.NaT`` is *not* a ``pd.Timestamp`` instance (it has its
          own distinct type) and would otherwise slip past a
          Timestamp-only check.
        - ``pd.Timestamp``, native ``datetime.datetime``, and native
          ``datetime.date`` all convert to an ISO 8601 string via a
          single ``datetime.date`` check, since ``pd.Timestamp`` is
          itself a subclass of ``datetime.datetime`` (which is in turn a
          subclass of ``datetime.date``). Native ``datetime``/``date``
          objects can appear in object-dtype columns depending on how a
          source file was parsed (e.g. openpyxl commonly yields native
          ``datetime`` objects for date cells rather than pandas
          converting them to ``Timestamp``), so a Timestamp-only check
          would miss them.
        - numpy integer/floating/bool scalar types convert to their
          native Python equivalents.
        - Values already JSON-safe (``str``, native ``int``/``float``/
          ``bool``, ``None``) pass through unchanged.

        Args:
            value: A single cell value from a DataFrame row.

        Returns:
            A tuple of (JSON-safe value, whether it was converted).
        """
        if value is None:
            return None, False

        try:
            if pd.isna(value):
                return None, True
        except (TypeError, ValueError):
            pass

        if isinstance(value, datetime.date):
            return value.isoformat(), True

        if isinstance(value, np.bool_):
            return bool(value), True
        if isinstance(value, np.integer):
            return int(value), True
        if isinstance(value, np.floating):
            return float(value), True

        return value, False

    # ----------------------------------------------------------------- #
    # Metadata Assembly
    # ----------------------------------------------------------------- #

    def _build_metadata(
        self,
        *,
        original_row_count: int,
        original_column_count: int,
        records: list[dict[str, Any]],
        field_names: tuple[str, ...],
        json_unsafe_values_converted: int,
    ) -> AIDataMetadata:
        """Assemble structural statistics for a completed preparation run.

        Args:
            original_row_count: Row count of the input DataFrame.
            original_column_count: Column count of the input DataFrame.
            records: The records produced.
            field_names: Column names present in every record.
            json_unsafe_values_converted: Number of cell values that
                required conversion.

        Returns:
            An ``AIDataMetadata`` combining every statistic gathered
            during the pipeline run.
        """
        return AIDataMetadata(
            original_row_count=original_row_count,
            original_column_count=original_column_count,
            record_count=len(records),
            field_names=field_names,
            json_unsafe_values_converted=json_unsafe_values_converted,
        )

    # ----------------------------------------------------------------- #
    # Logging
    # ----------------------------------------------------------------- #

    @staticmethod
    def _log_stage(stage: AIDataStage, detail: str) -> None:
        """Emit a consistent, structured log line for a completed stage.

        Args:
            stage: The stage that just completed.
            detail: A short, human-readable summary of what happened.
        """
        logger.info("AI data preparation stage complete: %s (%s)", stage.value, detail)