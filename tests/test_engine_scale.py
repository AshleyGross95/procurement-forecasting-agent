"""Coverage of the expanded 48-PO synthetic dataset.

tests/test_engine.py already covers the original seeded exception cases and
a hand-built clean fixture; this file adds coverage for the additional
exception cases seeded into the expanded dataset (27 -> 48 purchase orders)
and confirms prioritization still holds correctly at the larger scale.

All expected values below were derived by running the unmodified rule
functions in src/engine.py against the checked-in synthetic CSVs and reading
back their output -- src/engine.py itself is not touched by this release
pass.
"""
from __future__ import annotations

import inspect

import pytest

from src import engine


@pytest.fixture(scope="module")
def synthetic_data():
    return engine.load_data()


@pytest.fixture(scope="module")
def all_exceptions(synthetic_data):
    purchase_orders, suppliers, budgets, invoices = synthetic_data
    return engine.detect_all(purchase_orders, suppliers, budgets, invoices)


# ---------------------------------------------------------------------------
# Exactly six rule types -- confirm no seventh rule was ever added.
# ---------------------------------------------------------------------------

def test_exactly_six_rule_functions_exist():
    rule_fns = [
        name for name, _ in inspect.getmembers(engine, inspect.isfunction)
        if name.startswith("rule_")
    ]
    assert len(rule_fns) == 6
    assert sorted(rule_fns) == [
        "rule_budget_variance",
        "rule_duplicate_invoice",
        "rule_inactive_supplier",
        "rule_missing_documentation",
        "rule_policy_threshold",
        "rule_upcoming_renewal",
    ]


def test_exactly_six_exception_types_in_full_detection(all_exceptions):
    types_found = {e.exception_type for e in all_exceptions}
    assert types_found == {
        "budget_variance",
        "duplicate_invoice",
        "missing_documentation",
        "inactive_supplier",
        "policy_threshold",
        "upcoming_renewal",
    }


# ---------------------------------------------------------------------------
# Dataset scale
# ---------------------------------------------------------------------------

def test_dataset_has_exactly_48_purchase_orders(synthetic_data):
    purchase_orders, _, _, _ = synthetic_data
    assert len(purchase_orders) == 48


# ---------------------------------------------------------------------------
# Rule 1: inactive_supplier -- additional seeded cases beyond PO-3006
# ---------------------------------------------------------------------------

def test_inactive_supplier_additional_cases(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_inactive_supplier(purchase_orders, suppliers)
    by_po = {r.po_id: r for r in results}
    # SUP-006 (already inactive) placed a second time on PO-3037.
    assert "PO-3037" in by_po
    assert by_po["PO-3037"].financial_exposure == pytest.approx(4700.0)
    # SUP-012 is a newly seeded inactive supplier for the expanded dataset.
    assert "PO-3032" in by_po
    assert by_po["PO-3032"].financial_exposure == pytest.approx(9000.0)
    assert by_po["PO-3032"].supplier_id == "SUP-012"


# ---------------------------------------------------------------------------
# Rule 2: missing_documentation -- additional seeded cases beyond PO-3004
# ---------------------------------------------------------------------------

def test_missing_documentation_additional_cases(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_missing_documentation(purchase_orders, suppliers)
    by_po = {r.po_id: r for r in results}
    # SUP-013 is a newly seeded supplier without current documentation.
    assert "PO-3035" in by_po
    assert by_po["PO-3035"].supplier_id == "SUP-013"
    assert by_po["PO-3035"].financial_exposure == pytest.approx(6200.0)
    # SUP-004 (already missing docs) placed again on PO-3040.
    assert "PO-3040" in by_po
    assert by_po["PO-3040"].financial_exposure == pytest.approx(5000.0)


# ---------------------------------------------------------------------------
# Rule 3: budget_variance -- new Finance and Customer Success budget lines
# ---------------------------------------------------------------------------

def test_budget_variance_new_finance_line(synthetic_data):
    purchase_orders, _, budgets, _ = synthetic_data
    results = engine.rule_budget_variance(purchase_orders, budgets)
    by_po = {r.po_id: r for r in results}
    # BL-FIN-01: allocated 25,000, spent_to_date 10,000; PO-3028 (4,500) and
    # PO-3032 (9,000) keep it under allocation; PO-3038 (9,000) tips it to
    # 32,500, an overage of 7,500.
    assert "PO-3028" not in by_po
    assert "PO-3038" in by_po
    assert by_po["PO-3038"].financial_exposure == pytest.approx(7500.0)
    assert by_po["PO-3038"].department == "Finance"


def test_budget_variance_new_customer_success_line(synthetic_data):
    purchase_orders, _, budgets, _ = synthetic_data
    results = engine.rule_budget_variance(purchase_orders, budgets)
    by_po = {r.po_id: r for r in results}
    # BL-CS-01: allocated 20,000, spent_to_date 8,000; PO-3041 (5,000) tips
    # cumulative spend to 22,400, an overage of 2,400.
    assert "PO-3041" in by_po
    assert by_po["PO-3041"].financial_exposure == pytest.approx(2400.0)
    assert by_po["PO-3041"].department == "Customer Success"


def test_budget_variance_procurement_line_stacks_with_large_po(synthetic_data):
    purchase_orders, _, budgets, _ = synthetic_data
    results = engine.rule_budget_variance(purchase_orders, budgets)
    by_po = {r.po_id: r for r in results}
    # BL-PROC-01 allocation was raised to 150,000 to absorb the new
    # Procurement POs cleanly, except the large PO-3047 (68,000), which
    # pushes cumulative committed spend to 169,600 -- an overage of 19,600 --
    # stacking with that PO's own policy_threshold exception.
    assert "PO-3047" in by_po
    assert by_po["PO-3047"].financial_exposure == pytest.approx(19600.0)
    assert "PO-3034" not in by_po  # earlier, smaller Procurement PO stays clean


# ---------------------------------------------------------------------------
# Rule 4: duplicate_invoice -- additional seeded cases beyond PO-3010
# ---------------------------------------------------------------------------

def test_duplicate_invoice_additional_cases(synthetic_data):
    purchase_orders, _, _, invoices = synthetic_data
    results = engine.rule_duplicate_invoice(invoices, purchase_orders)
    by_po = {r.po_id: r for r in results}
    assert {"PO-3010", "PO-3043", "PO-3044"}.issubset(by_po.keys())
    assert by_po["PO-3043"].financial_exposure == pytest.approx(4500.0)
    assert by_po["PO-3044"].financial_exposure == pytest.approx(18000.0)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# Rule 5: policy_threshold -- additional seeded cases beyond PO-3010
# ---------------------------------------------------------------------------

def test_policy_threshold_additional_cases(synthetic_data):
    purchase_orders, _, _, _ = synthetic_data
    results = engine.rule_policy_threshold(purchase_orders)
    by_po = {r.po_id: r for r in results}
    assert by_po.keys() == {"PO-3010", "PO-3046", "PO-3047"}
    assert by_po["PO-3046"].financial_exposure == pytest.approx(55000.0)
    assert by_po["PO-3047"].financial_exposure == pytest.approx(68000.0)
    assert all(r.financial_exposure > engine.POLICY_THRESHOLD_AMOUNT for r in results)


# ---------------------------------------------------------------------------
# Rule 6: upcoming_renewal -- additional seeded cases beyond PO-3007
# ---------------------------------------------------------------------------

def test_upcoming_renewal_additional_cases(synthetic_data):
    purchase_orders, suppliers, _, _ = synthetic_data
    results = engine.rule_upcoming_renewal(purchase_orders, suppliers)
    by_po = {r.po_id: r for r in results}
    # SUP-014 is a newly seeded supplier with a contract ending inside the
    # 60-day renewal window from the fixed reference date.
    assert "PO-3048" in by_po
    assert by_po["PO-3048"].supplier_id == "SUP-014"
    # SUP-007's existing near-term renewal also appears on a second PO.
    assert "PO-3042" in by_po
    assert by_po["PO-3042"].supplier_id == "SUP-007"
    # PO-3046 shares SUP-014 with PO-3048 and is also over the policy
    # threshold -- an intentional stacked exception.
    assert "PO-3046" in by_po


# ---------------------------------------------------------------------------
# Prioritization at the larger 48-PO scale
# ---------------------------------------------------------------------------

def test_prioritize_sorts_descending_at_scale(all_exceptions):
    exposures = [e.financial_exposure for e in all_exceptions]
    assert exposures == sorted(exposures, reverse=True)
    assert len(all_exceptions) >= 20  # richer dataset should surface more exceptions


def test_highest_priority_exception_is_the_largest_dollar_exposure(all_exceptions):
    top = all_exceptions[0]
    assert top.financial_exposure == max(e.financial_exposure for e in all_exceptions)
    # PO-3047 ($68,000, over threshold and over its budget line) and PO-3010
    # ($62,000, duplicate + over threshold) are the two largest exposures in
    # the expanded dataset; the top of the list must be one of them.
    assert top.po_id in {"PO-3047", "PO-3010"}


def test_total_exception_count_matches_full_rule_sum(synthetic_data, all_exceptions):
    purchase_orders, suppliers, budgets, invoices = synthetic_data
    expected_total = (
        len(engine.rule_inactive_supplier(purchase_orders, suppliers))
        + len(engine.rule_missing_documentation(purchase_orders, suppliers))
        + len(engine.rule_budget_variance(purchase_orders, budgets))
        + len(engine.rule_duplicate_invoice(invoices, purchase_orders))
        + len(engine.rule_policy_threshold(purchase_orders))
        + len(engine.rule_upcoming_renewal(purchase_orders, suppliers))
    )
    assert len(all_exceptions) == expected_total
