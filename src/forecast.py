"""Illustrative forecast helpers built from the seeded synthetic data.

Nothing here is a predictive model or a real financial forecast -- it is
simple, transparent aggregation (cumulative exposure by month, counts by
exception type) over the same ``Exception`` records ``src/engine.py``
already detected. It exists to give a reviewer an at-a-glance illustrative
view of how exposure is distributed, not to predict future spend. The UI
labels every chart built from these functions "Illustrative / synthetic
demo data".

Detection and financial-exposure math are untouched here and remain 100%
the responsibility of src/engine.py -- this module only aggregates
already-detected results for display.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from src.models import Exception as ExceptionRecord

MONTHLY_FORECAST_COLUMNS = ["month", "monthly_exposure", "cumulative_exposure"]
TYPE_COUNT_COLUMNS = ["exception_type", "count"]


def build_monthly_exposure_forecast(
    exceptions: List[ExceptionRecord], purchase_orders: pd.DataFrame
) -> pd.DataFrame:
    """Cumulative financial exposure by PO order-month, sorted chronologically.

    An ``Exception`` record has no date of its own, so each one is joined
    back to its PO's ``order_date`` to bucket by calendar month. The result
    is a running cumulative total -- an illustrative "exposure builds up
    over time" view, not a prediction of future exceptions.
    """
    if not exceptions:
        return pd.DataFrame(columns=MONTHLY_FORECAST_COLUMNS)

    po_dates = purchase_orders.set_index("po_id")["order_date"]
    rows = []
    for exc in exceptions:
        order_date = po_dates.get(exc.po_id)
        if order_date is None or pd.isna(order_date):
            continue
        month = pd.Timestamp(order_date).to_period("M").to_timestamp()
        rows.append({"month": month, "financial_exposure": exc.financial_exposure})

    if not rows:
        return pd.DataFrame(columns=MONTHLY_FORECAST_COLUMNS)

    frame = pd.DataFrame(rows)
    monthly = (
        frame.groupby("month")["financial_exposure"]
        .sum()
        .reset_index()
        .sort_values("month")
        .rename(columns={"financial_exposure": "monthly_exposure"})
        .reset_index(drop=True)
    )
    monthly["cumulative_exposure"] = monthly["monthly_exposure"].cumsum()
    return monthly[MONTHLY_FORECAST_COLUMNS]


def build_exception_counts_by_type(exceptions: List[ExceptionRecord]) -> pd.DataFrame:
    """Count of detected exceptions per exception_type, sorted descending by count."""
    if not exceptions:
        return pd.DataFrame(columns=TYPE_COUNT_COLUMNS)
    counts = (
        pd.Series([e.exception_type for e in exceptions])
        .value_counts()
        .rename_axis("exception_type")
        .reset_index(name="count")
    )
    return counts[TYPE_COUNT_COLUMNS]
