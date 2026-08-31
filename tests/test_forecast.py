"""Tests for the illustrative forecast aggregation in src/forecast.py.

Confirms the monthly cumulative-exposure chart and the exception-count-by-type
table are computed correctly from Exception records -- both from small
hand-built fixtures (exact arithmetic) and from the real seeded dataset
(consistency checks against the rule engine's own totals).
"""
from __future__ import annotations

import pandas as pd
import pytest

from src import engine, forecast
from src.models import Exception as ExceptionRecord


def _make_exception(po_id: str, exception_type: str, exposure: float) -> ExceptionRecord:
    return ExceptionRecord(
        po_id=po_id,
        exception_type=exception_type,
        description="test fixture",
        financial_exposure=exposure,
        recommended_action="test action",
        department="Test",
        supplier_id="SUP-TEST",
    )


@pytest.fixture
def small_purchase_orders() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"po_id": "PO-A", "order_date": pd.Timestamp("2026-06-05")},
            {"po_id": "PO-B", "order_date": pd.Timestamp("2026-06-20")},
            {"po_id": "PO-C", "order_date": pd.Timestamp("2026-07-10")},
        ]
    )


def test_monthly_forecast_groups_by_calendar_month(small_purchase_orders):
    exceptions = [
        _make_exception("PO-A", "policy_threshold", 1000.0),
        _make_exception("PO-B", "budget_variance", 2000.0),
        _make_exception("PO-C", "duplicate_invoice", 500.0),
    ]
    result = forecast.build_monthly_exposure_forecast(exceptions, small_purchase_orders)
    assert list(result["month"]) == [pd.Timestamp("2026-06-01"), pd.Timestamp("2026-07-01")]
    # June: PO-A (1000) + PO-B (2000) = 3000
    assert result.loc[0, "monthly_exposure"] == pytest.approx(3000.0)
    # July: PO-C (500)
    assert result.loc[1, "monthly_exposure"] == pytest.approx(500.0)


def test_monthly_forecast_cumulative_sum_is_correct(small_purchase_orders):
    exceptions = [
        _make_exception("PO-A", "policy_threshold", 1000.0),
        _make_exception("PO-B", "budget_variance", 2000.0),
        _make_exception("PO-C", "duplicate_invoice", 500.0),
    ]
    result = forecast.build_monthly_exposure_forecast(exceptions, small_purchase_orders)
    # Cumulative must be monotonically non-decreasing and end at the grand total.
    assert list(result["cumulative_exposure"]) == [3000.0, 3500.0]
    assert result["cumulative_exposure"].iloc[-1] == pytest.approx(
        sum(e.financial_exposure for e in exceptions)
    )


def test_monthly_forecast_handles_multiple_exceptions_same_po_same_month(small_purchase_orders):
    # A PO can carry more than one exception type (e.g. PO-3010 in the real
    # dataset); both must contribute to that month's exposure.
    exceptions = [
        _make_exception("PO-A", "policy_threshold", 1000.0),
        _make_exception("PO-A", "duplicate_invoice", 1000.0),
    ]
    result = forecast.build_monthly_exposure_forecast(exceptions, small_purchase_orders)
    assert len(result) == 1
    assert result.loc[0, "monthly_exposure"] == pytest.approx(2000.0)


def test_monthly_forecast_empty_input_returns_empty_frame():
    result = forecast.build_monthly_exposure_forecast([], pd.DataFrame(columns=["po_id", "order_date"]))
    assert result.empty
    assert list(result.columns) == forecast.MONTHLY_FORECAST_COLUMNS


def test_exception_counts_by_type_tally_is_correct():
    exceptions = [
        _make_exception("PO-A", "policy_threshold", 1000.0),
        _make_exception("PO-B", "policy_threshold", 2000.0),
        _make_exception("PO-C", "budget_variance", 500.0),
    ]
    result = forecast.build_exception_counts_by_type(exceptions)
    counts = dict(zip(result["exception_type"], result["count"]))
    assert counts == {"policy_threshold": 2, "budget_variance": 1}
    assert list(result.columns) == forecast.TYPE_COUNT_COLUMNS


def test_exception_counts_by_type_empty_input_returns_empty_frame():
    result = forecast.build_exception_counts_by_type([])
    assert result.empty
    assert list(result.columns) == forecast.TYPE_COUNT_COLUMNS


# ---------------------------------------------------------------------------
# Consistency against the real seeded 48-PO dataset
# ---------------------------------------------------------------------------

def test_monthly_forecast_total_matches_engine_total_on_real_data():
    purchase_orders, suppliers, budgets, invoices = engine.load_data()
    exceptions = engine.detect_all(purchase_orders, suppliers, budgets, invoices)
    monthly = forecast.build_monthly_exposure_forecast(exceptions, purchase_orders)

    expected_total = sum(e.financial_exposure for e in exceptions)
    assert monthly["monthly_exposure"].sum() == pytest.approx(expected_total)
    assert monthly["cumulative_exposure"].iloc[-1] == pytest.approx(expected_total)


def test_exception_counts_by_type_sum_matches_total_exceptions_on_real_data():
    purchase_orders, suppliers, budgets, invoices = engine.load_data()
    exceptions = engine.detect_all(purchase_orders, suppliers, budgets, invoices)
    counts = forecast.build_exception_counts_by_type(exceptions)
    assert counts["count"].sum() == len(exceptions)
    assert set(counts["exception_type"]) == {e.exception_type for e in exceptions}
