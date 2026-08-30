"""Tests for the deterministic rule engine in src/engine.py.

Two kinds of coverage:
1. Against the real synthetic fixture CSVs in data/synthetic/, confirming each
   of the six seeded exception conditions is actually detected, and that
   prioritization sorts by descending financial exposure.
2. Against small, hand-built "clean" DataFrames with no seeded problems,
   confirming zero exceptions are produced.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src import engine


# ---------------------------------------------------------------------------
# Fixtures: real synthetic data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def synthetic_data():
    return engine.load_data()


@pytest.fixture(scope="module")
def all_exceptions(synthetic_data):
    purchase_orders, suppliers, budgets, invoices = synthetic_data
    return engine.detect_all(purchase_orders, suppliers, budgets, invoices)


# ---------------------------------------------------------------------------
# Rule 1: inactive supplier
# ---------------------------------------------------------------------------

def test_inactive_supplier_detected(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_inactive_supplier(purchase_orders, suppliers)
    po_ids = {r.po_id for r in results}
    assert "PO-3006" in po_ids  # SUP-006 is seeded inactive
    assert all(r.exception_type == "inactive_supplier" for r in results)
    assert all(r.financial_exposure > 0 for r in results)


# ---------------------------------------------------------------------------
# Rule 2: missing documentation
# ---------------------------------------------------------------------------

def test_missing_documentation_detected(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_missing_documentation(purchase_orders, suppliers)
    po_ids = {r.po_id for r in results}
    assert "PO-3004" in po_ids  # SUP-004 is seeded without current documentation
    assert all(r.exception_type == "missing_documentation" for r in results)


# ---------------------------------------------------------------------------
# Rule 3: budget variance
# ---------------------------------------------------------------------------

def test_budget_variance_detected(synthetic_data):
    purchase_orders, _, budgets, _ = synthetic_data
    results = engine.rule_budget_variance(purchase_orders, budgets)
    po_ids = {r.po_id for r in results}
    # BL-OPS-01: allocated 50,000, spent_to_date 42,000; PO-3008 (15,000) tips it over.
    assert "PO-3008" in po_ids
    variance_result = next(r for r in results if r.po_id == "PO-3008")
    assert variance_result.financial_exposure == pytest.approx(11000.0)
    assert variance_result.exception_type == "budget_variance"


# ---------------------------------------------------------------------------
# Rule 4: duplicate invoice
# ---------------------------------------------------------------------------

def test_duplicate_invoice_detected(synthetic_data):
    purchase_orders, _, _, invoices = synthetic_data
    results = engine.rule_duplicate_invoice(invoices, purchase_orders)
    po_ids = {r.po_id for r in results}
    assert "PO-3010" in po_ids  # INV-6009 and INV-6010 are seeded duplicates
    dup_result = next(r for r in results if r.po_id == "PO-3010")
    assert dup_result.financial_exposure == pytest.approx(62000.0)
    assert dup_result.exception_type == "duplicate_invoice"


# ---------------------------------------------------------------------------
# Rule 5: policy threshold
# ---------------------------------------------------------------------------

def test_policy_threshold_detected(synthetic_data):
    purchase_orders, _, _, _ = synthetic_data
    results = engine.rule_policy_threshold(purchase_orders)
    po_ids = {r.po_id for r in results}
    assert "PO-3010" in po_ids  # PO-3010 is seeded at $62,000 > $50,000 threshold
    assert all(r.financial_exposure > engine.POLICY_THRESHOLD_AMOUNT for r in results)


# ---------------------------------------------------------------------------
# Rule 6: upcoming renewal
# ---------------------------------------------------------------------------

def test_upcoming_renewal_detected(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_upcoming_renewal(purchase_orders, suppliers)
    po_ids = {r.po_id for r in results}
    # SUP-007 contract_end_date 2026-09-20 is within 60 days of the reference date.
    assert "PO-3007" in po_ids
    assert all(r.exception_type == "upcoming_renewal" for r in results)


# ---------------------------------------------------------------------------
# Prioritization
# ---------------------------------------------------------------------------

def test_prioritize_sorts_descending(all_exceptions):
    exposures = [e.financial_exposure for e in all_exceptions]
    assert exposures == sorted(exposures, reverse=True)


def test_detect_all_produces_all_six_types(all_exceptions):
    types_found = {e.exception_type for e in all_exceptions}
    expected_types = {
        "budget_variance",
        "duplicate_invoice",
        "missing_documentation",
        "inactive_supplier",
        "policy_threshold",
        "upcoming_renewal",
    }
    assert expected_types.issubset(types_found)


# ---------------------------------------------------------------------------
# Clean data: zero exceptions
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_data():
    purchase_orders = pd.DataFrame(
        [
            {
                "po_id": "PO-9001",
                "supplier_id": "SUP-900",
                "department": "Facilities",
                "amount": 1000,
                "budget_line": "BL-CLEAN-01",
                "order_date": pd.Timestamp("2026-06-01"),
                "status": "approved",
            }
        ]
    )
    suppliers = pd.DataFrame(
        [
            {
                "supplier_id": "SUP-900",
                "name": "Clean & Co Testing Supply",
                "active": True,
                "last_transaction_date": pd.Timestamp("2026-06-01"),
                "has_current_documentation": True,
                "contract_end_date": pd.Timestamp("2030-01-01"),  # far in the future
            }
        ]
    )
    budgets = pd.DataFrame(
        [
            {
                "budget_line": "BL-CLEAN-01",
                "department": "Facilities",
                "fiscal_year": 2026,
                "allocated_amount": 100000,
                "spent_to_date": 1000,
            }
        ]
    )
    invoices = pd.DataFrame(
        [
            {
                "invoice_id": "INV-9001",
                "po_id": "PO-9001",
                "amount": 1000,
                "invoice_date": pd.Timestamp("2026-06-05"),
                "duplicate_check_hash": "H-CLEAN-01",
            }
        ]
    )
    return purchase_orders, suppliers, budgets, invoices


def test_clean_data_produces_zero_exceptions(clean_data):
    purchase_orders, suppliers, budgets, invoices = clean_data
    results = engine.detect_all(
        purchase_orders,
        suppliers,
        budgets,
        invoices,
        reference_date=date(2026, 6, 1),
    )
    assert results == []
