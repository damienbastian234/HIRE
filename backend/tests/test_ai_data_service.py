"""Unit tests for app.services.ai_data_service.

Written strictly against the actual AIDataService implementation.
Pure pandas/numpy/datetime + the service itself -- no filesystem,
database, or FastAPI dependency, matching ai_data_service.py's own
zero-I/O design. No pytest plugins beyond bare pytest are required.
"""

from __future__ import annotations

import datetime
import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from app.services.ai_data_service import (
    AIDataFailure,
    AIDataMetadata,
    AIDataOperationError,
    AIDataResult,
    AIDataService,
    AIDataStage,
    AIDataSuccess,
    InvalidAIDataInputError,
)


def _service() -> AIDataService:
    return AIDataService()


# --------------------------------------------------------------------------- #
# 1-3: Basic conversion, row order, field names
# --------------------------------------------------------------------------- #


def test_prepare_for_ai_converts_normal_dataframe_to_records() -> None:
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})

    result = _service().prepare_for_ai(df)

    assert result.is_success
    assert result.success.records == [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]


def test_prepare_for_ai_preserves_row_order() -> None:
    df = pd.DataFrame({"id": [3, 1, 2]})

    result = _service().prepare_for_ai(df)

    assert [record["id"] for record in result.success.records] == [3, 1, 2]


def test_prepare_for_ai_preserves_field_names() -> None:
    df = pd.DataFrame({"first_name": ["Alice"], "last_name": ["Smith"]})

    result = _service().prepare_for_ai(df)

    assert set(result.success.records[0].keys()) == {"first_name", "last_name"}


# --------------------------------------------------------------------------- #
# 4: Metadata correctness
# --------------------------------------------------------------------------- #


def test_metadata_reports_correct_statistics() -> None:
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob"],
            "age": [30, 25],
            "score": [95.5, None],
        }
    )

    result = _service().prepare_for_ai(df)

    metadata = result.success.metadata
    assert metadata.original_row_count == 2
    assert metadata.original_column_count == 3
    assert metadata.record_count == 2
    assert metadata.field_names == ("name", "age", "score")
    assert metadata.json_unsafe_values_converted == 1  # the None score


# --------------------------------------------------------------------------- #
# 5: Missing-value conversion (NaN, pd.NA, NaT)
# --------------------------------------------------------------------------- #


def test_python_nan_converts_to_none() -> None:
    df = pd.DataFrame({"value": [1.0, float("nan")]})

    result = _service().prepare_for_ai(df)

    assert result.success.records[1]["value"] is None


def test_pd_na_converts_to_none() -> None:
    df = pd.DataFrame({"notes": pd.array(["hello", pd.NA], dtype="string")})

    result = _service().prepare_for_ai(df)

    assert result.success.records[1]["notes"] is None


def test_pandas_nat_converts_to_none() -> None:
    df = pd.DataFrame({"joined": pd.to_datetime(["2023-01-01", None])})

    result = _service().prepare_for_ai(df)

    assert result.success.records[1]["joined"] is None


# --------------------------------------------------------------------------- #
# 6: numpy scalar -> native Python conversion
# --------------------------------------------------------------------------- #


def test_numpy_integer_becomes_native_python_int() -> None:
    df = pd.DataFrame({"count": pd.array([np.int64(10)])})

    result = _service().prepare_for_ai(df)

    value = result.success.records[0]["count"]
    assert isinstance(value, int)
    assert not isinstance(value, np.integer)


def test_numpy_floating_becomes_native_python_float() -> None:
    df = pd.DataFrame({"score": pd.array([np.float64(1.1)])})

    result = _service().prepare_for_ai(df)

    value = result.success.records[0]["score"]
    assert isinstance(value, float)
    assert not isinstance(value, np.floating)


def test_numpy_boolean_becomes_native_python_bool() -> None:
    df = pd.DataFrame({"active": [np.bool_(True)]})

    result = _service().prepare_for_ai(df)

    value = result.success.records[0]["active"]
    assert isinstance(value, bool)
    assert not isinstance(value, np.bool_)


# --------------------------------------------------------------------------- #
# 7: Timestamp / native datetime / native date -> ISO string
# --------------------------------------------------------------------------- #


def test_pandas_timestamp_converts_to_iso_string() -> None:
    df = pd.DataFrame({"joined": pd.to_datetime(["2023-06-15 10:30:00"])})

    result = _service().prepare_for_ai(df)

    assert result.success.records[0]["joined"] == "2023-06-15T10:30:00"


def test_native_datetime_converts_to_iso_string() -> None:
    df = pd.DataFrame(
        {"created": pd.Series([datetime.datetime(2023, 3, 1, 9, 0)], dtype="object")}
    )

    result = _service().prepare_for_ai(df)

    assert result.success.records[0]["created"] == "2023-03-01T09:00:00"


def test_native_date_converts_to_iso_string() -> None:
    df = pd.DataFrame({"birthday": pd.Series([datetime.date(2023, 5, 1)], dtype="object")})

    result = _service().prepare_for_ai(df)

    assert result.success.records[0]["birthday"] == "2023-05-01"


# --------------------------------------------------------------------------- #
# 8: Already-JSON-safe values pass through unchanged
# --------------------------------------------------------------------------- #


def test_already_safe_values_remain_unchanged() -> None:
    df = pd.DataFrame(
        {
            "name": ["Alice"],
            "age": [30],
            "score": [95.5],
            "active": [True],
            "notes": [None],
        }
    )

    result = _service().prepare_for_ai(df)

    record = result.success.records[0]
    assert record == {"name": "Alice", "age": 30, "score": 95.5, "active": True, "notes": None}
    # none of these should have been counted as "converted"
    assert result.success.metadata.json_unsafe_values_converted == 0


# --------------------------------------------------------------------------- #
# 9-11: Empty/zero-column/non-DataFrame input handling
# --------------------------------------------------------------------------- #


def test_prepare_for_ai_succeeds_on_empty_dataframe_with_columns() -> None:
    df = pd.DataFrame({"name": [], "age": []})

    result = _service().prepare_for_ai(df)

    assert result.is_success
    assert result.success.records == []
    assert result.success.metadata.record_count == 0


def test_zero_column_dataframe_returns_structured_failure() -> None:
    df = pd.DataFrame(index=[0, 1])

    result = _service().prepare_for_ai(df)

    assert not result.is_success
    assert result.failure.stage == AIDataStage.INPUT_VALIDATION
    assert result.failure.reason_code == "no_columns"


def test_non_dataframe_input_raises_invalid_input_error() -> None:
    with pytest.raises(InvalidAIDataInputError):
        _service().prepare_for_ai("not a dataframe")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 12: AIDataResult success/failure invariant
# --------------------------------------------------------------------------- #


def test_result_succeeded_factory_builds_valid_success_result() -> None:
    metadata = AIDataMetadata(
        original_row_count=1,
        original_column_count=1,
        record_count=1,
        field_names=("x",),
        json_unsafe_values_converted=0,
    )

    result = AIDataResult.succeeded([{"x": 1}], metadata)

    assert result.is_success
    assert isinstance(result.success, AIDataSuccess)
    assert result.success.records == [{"x": 1}]
    assert result.failure is None


def test_result_failed_factory_builds_valid_failure_result() -> None:
    result = AIDataResult.failed(AIDataStage.INPUT_VALIDATION, "no_columns", "no columns")

    assert not result.is_success
    assert isinstance(result.failure, AIDataFailure)
    assert result.failure.stage == AIDataStage.INPUT_VALIDATION
    assert result.success is None


def test_result_invariant_raises_when_success_true_but_success_none() -> None:
    with pytest.raises(ValueError):
        AIDataResult(is_success=True, success=None)


def test_result_invariant_raises_when_success_false_but_failure_none() -> None:
    with pytest.raises(ValueError):
        AIDataResult(is_success=False, failure=None)


def test_result_invariant_raises_when_both_success_and_failure_populated() -> None:
    metadata = AIDataMetadata(
        original_row_count=1,
        original_column_count=1,
        record_count=1,
        field_names=("x",),
        json_unsafe_values_converted=0,
    )
    success = AIDataSuccess([{"x": 1}], metadata)
    failure = AIDataFailure(AIDataStage.INPUT_VALIDATION, "no_columns", "no columns")

    with pytest.raises(ValueError):
        AIDataResult(is_success=True, success=success, failure=failure)


# --------------------------------------------------------------------------- #
# 13: Input immutability
# --------------------------------------------------------------------------- #


def test_prepare_for_ai_does_not_mutate_input_dataframe() -> None:
    df = pd.DataFrame({"age": [30, 25]})
    original_dtype = df["age"].dtype
    original_values = df["age"].tolist()

    _service().prepare_for_ai(df)

    assert df["age"].dtype == original_dtype
    assert df["age"].tolist() == original_values


# --------------------------------------------------------------------------- #
# 14: Unexpected conversion errors are wrapped as AIDataOperationError
# --------------------------------------------------------------------------- #


def test_unexpected_conversion_error_is_wrapped_and_chained() -> None:
    df = pd.DataFrame({"name": ["Alice"]})

    with patch.object(
        AIDataService,
        "_convert_to_json_safe_records",
        side_effect=RuntimeError("simulated conversion failure"),
    ):
        with pytest.raises(AIDataOperationError) as exc_info:
            _service().prepare_for_ai(df)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


# --------------------------------------------------------------------------- #
# 15: Real json.dumps() proof
# --------------------------------------------------------------------------- #


def test_records_are_actually_json_serializable() -> None:
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob"],
            "age": pd.array([np.int64(30), np.int64(25)]),
            "score": pd.array([np.float64(95.5), np.float64(88.2)]),
            "active": [np.bool_(True), np.bool_(False)],
            "notes": pd.array(["ok", pd.NA], dtype="string"),
            "joined": pd.to_datetime(["2023-01-15", None]),
            "created": pd.Series(
                [datetime.datetime(2023, 3, 1, 9, 0), datetime.datetime(2023, 3, 2, 10, 0)],
                dtype="object",
            ),
            "birthday": pd.Series(
                [datetime.date(2023, 5, 1), datetime.date(2023, 5, 2)], dtype="object"
            ),
        }
    )

    result = _service().prepare_for_ai(df)

    assert result.is_success
    json.dumps(result.success.records)  # raises if not truly JSON-safe