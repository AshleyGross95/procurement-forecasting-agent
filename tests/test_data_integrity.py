"""Referential-integrity and row-count checks for the synthetic data files.

These tests protect the expanded dataset (27 -> 48 purchase orders) from
silent regressions: exact row counts, uniqueness of primary keys, and every
foreign-key-style reference (po.supplier_id, po.budget_line, invoice.po_id)
resolving to a real row in the referenced table.
"""
from __future__ import annotations

from src import engine


def test_purchase_orders_row_count_is_exactly_48():
    purchase_orders, _, _, _ = engine.load_data()
    assert len(purchase_orders) == 48


def test_suppliers_expanded_to_support_new_pos():
    _, suppliers, _, _ = engine.load_data()
    assert len(suppliers) == 15


def test_budgets_expanded_to_support_new_pos():
    _, _, budgets, _ = engine.load_data()
    assert len(budgets) == 9


def test_invoices_expanded_to_support_new_pos():
    _, _, _, invoices = engine.load_data()
    assert len(invoices) == 45


def test_po_ids_are_unique():
    purchase_orders, _, _, _ = engine.load_data()
    assert purchase_orders["po_id"].is_unique


def test_supplier_ids_are_unique():
    _, suppliers, _, _ = engine.load_data()
    assert suppliers["supplier_id"].is_unique


def test_budget_lines_are_unique():
    _, _, budgets, _ = engine.load_data()
    assert budgets["budget_line"].is_unique


def test_every_po_supplier_id_resolves_to_a_real_supplier():
    purchase_orders, suppliers, _, _ = engine.load_data()
    known_suppliers = set(suppliers["supplier_id"])
    assert set(purchase_orders["supplier_id"]).issubset(known_suppliers)


def test_every_po_budget_line_resolves_to_a_real_budget():
    purchase_orders, _, budgets, _ = engine.load_data()
    known_budget_lines = set(budgets["budget_line"])
    assert set(purchase_orders["budget_line"]).issubset(known_budget_lines)


def test_every_invoice_po_id_resolves_to_a_real_po():
    purchase_orders, _, _, invoices = engine.load_data()
    known_pos = set(purchase_orders["po_id"])
    assert set(invoices["po_id"]).issubset(known_pos)


def test_dataset_spans_multiple_suppliers_and_cost_centers():
    purchase_orders, suppliers, budgets, _ = engine.load_data()
    # "Multiple suppliers and cost centers" per the release brief -- confirm
    # the expanded dataset actually spreads across more than a token few.
    assert purchase_orders["supplier_id"].nunique() >= 10
    assert purchase_orders["department"].nunique() >= 8
    assert budgets["department"].nunique() >= 8


def test_original_seeded_exception_pos_are_still_present_unchanged():
    """Guards the exact original seeded rows the pre-existing test suite depends on."""
    purchase_orders, _, _, _ = engine.load_data()
    by_id = purchase_orders.set_index("po_id")

    assert by_id.loc["PO-3006", "supplier_id"] == "SUP-006"
    assert float(by_id.loc["PO-3006", "amount"]) == 9000.0

    assert by_id.loc["PO-3004", "supplier_id"] == "SUP-004"
    assert float(by_id.loc["PO-3004", "amount"]) == 8000.0

    assert by_id.loc["PO-3008", "budget_line"] == "BL-OPS-01"
    assert float(by_id.loc["PO-3008", "amount"]) == 15000.0

    assert by_id.loc["PO-3010", "supplier_id"] == "SUP-010"
    assert float(by_id.loc["PO-3010", "amount"]) == 62000.0

    assert by_id.loc["PO-3007", "supplier_id"] == "SUP-007"
    assert float(by_id.loc["PO-3007", "amount"]) == 7000.0
