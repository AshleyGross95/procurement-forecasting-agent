"""Deterministic rule engine for pre-payment procurement exception review.

Every function here is pure, rule-based pandas logic evaluated over the
synthetic CSVs in data/synthetic/. There is no LLM involvement anywhere in
this module: detection and financial exposure numbers are always 100%
rule-based. src/llm.py may later add a natural-language narration on top of
an already-detected Exception, but it never changes what gets detected or
how much money is at stake.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.models import Exception as ExceptionRecord

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

#: PO amount above which extra approval is required per procurement policy.
POLICY_THRESHOLD_AMOUNT = 50_000

#: How many days out a supplier contract renewal counts as "upcoming".
RENEWAL_WINDOW_DAYS = 60

#: Fixed "as of" date for the renewal-window check, so the bundled synthetic
#: data always produces the same, reviewable result regardless of the actual
#: wall-clock date the demo happens to be run on.
REFERENCE_DATE = date(2026, 8, 30)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(data_dir: Optional[Path] = None):
    """Load the four synthetic source tables as pandas DataFrames."""
    directory = Path(data_dir) if data_dir is not None else DATA_DIR

    purchase_orders = pd.read_csv(directory / "purchase_orders.csv", parse_dates=["order_date"])
    suppliers = pd.read_csv(
        directory / "suppliers.csv",
        parse_dates=["last_transaction_date", "contract_end_date"],
    )
    budgets = pd.read_csv(directory / "budgets.csv")
    invoices = pd.read_csv(directory / "invoices.csv", parse_dates=["invoice_date"])

    # Normalize boolean columns that may arrive as strings ("True"/"False") from CSV.
    for col in ("active", "has_current_documentation"):
        if suppliers[col].dtype != bool:
            suppliers[col] = suppliers[col].astype(str).str.strip().str.lower() == "true"

    return purchase_orders, suppliers, budgets, invoices


def _supplier_lookup(suppliers: pd.DataFrame) -> pd.DataFrame:
    return suppliers.set_index("supplier_id")


# ---------------------------------------------------------------------------
# Rule 1: inactive supplier
# ---------------------------------------------------------------------------

def rule_inactive_supplier(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame) -> List[ExceptionRecord]:
    """Flag any PO placed against a supplier that is no longer marked active."""
    exceptions: List[ExceptionRecord] = []
    sup = _supplier_lookup(suppliers)

    for _, po in purchase_orders.iterrows():
        supplier_id = po["supplier_id"]
        if supplier_id not in sup.index:
            continue
        supplier = sup.loc[supplier_id]
        if not bool(supplier["active"]):
            exceptions.append(
                ExceptionRecord(
                    po_id=po["po_id"],
                    exception_type="inactive_supplier",
                    description=(
                        f"PO {po['po_id']} (${po['amount']:,.2f}) was placed against "
                        f"{supplier['name']} ({supplier_id}), which is marked inactive as of "
                        f"its last transaction on {pd.Timestamp(supplier['last_transaction_date']).date()}."
                    ),
                    financial_exposure=float(po["amount"]),
                    recommended_action="Verify supplier status before releasing payment; confirm reinstatement or reroute the order to an active vendor.",
                    department=po["department"],
                    supplier_id=supplier_id,
                    supplier_name=supplier["name"],
                )
            )
    return exceptions


# ---------------------------------------------------------------------------
# Rule 2: missing documentation
# ---------------------------------------------------------------------------

def rule_missing_documentation(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame) -> List[ExceptionRecord]:
    """Flag any PO placed against a supplier lacking current documentation on file."""
    exceptions: List[ExceptionRecord] = []
    sup = _supplier_lookup(suppliers)

    for _, po in purchase_orders.iterrows():
        supplier_id = po["supplier_id"]
        if supplier_id not in sup.index:
            continue
        supplier = sup.loc[supplier_id]
        if not bool(supplier["has_current_documentation"]):
            exceptions.append(
                ExceptionRecord(
                    po_id=po["po_id"],
                    exception_type="missing_documentation",
                    description=(
                        f"PO {po['po_id']} (${po['amount']:,.2f}) is against {supplier['name']} "
                        f"({supplier_id}), which does not have current compliance documentation on file."
                    ),
                    financial_exposure=float(po["amount"]),
                    recommended_action="Collect current tax, insurance, and compliance documentation before releasing payment.",
                    department=po["department"],
                    supplier_id=supplier_id,
                    supplier_name=supplier["name"],
                )
            )
    return exceptions


# ---------------------------------------------------------------------------
# Rule 3: budget variance
# ---------------------------------------------------------------------------

def rule_budget_variance(purchase_orders: pd.DataFrame, budgets: pd.DataFrame) -> List[ExceptionRecord]:
    """Flag POs that push a budget line's cumulative spend past its allocation.

    POs on each budget line are applied in order_date order on top of
    spent_to_date. The first (and any subsequent) PO whose addition pushes the
    running total past allocated_amount is flagged, with financial_exposure
    equal to the cumulative overage at that point.
    """
    exceptions: List[ExceptionRecord] = []
    budget_lookup = budgets.set_index("budget_line")

    for budget_line, group in purchase_orders.sort_values("order_date").groupby("budget_line"):
        if budget_line not in budget_lookup.index:
            continue
        row = budget_lookup.loc[budget_line]
        allocated = float(row["allocated_amount"])
        department = row["department"]
        running_total = float(row["spent_to_date"])

        for _, po in group.iterrows():
            running_total += float(po["amount"])
            if running_total > allocated:
                overage = round(running_total - allocated, 2)
                exceptions.append(
                    ExceptionRecord(
                        po_id=po["po_id"],
                        exception_type="budget_variance",
                        description=(
                            f"Budget line {budget_line} ({department}) reaches "
                            f"${running_total:,.2f} in committed spend against a "
                            f"${allocated:,.2f} allocation once PO {po['po_id']} is included, "
                            f"an overage of ${overage:,.2f}."
                        ),
                        financial_exposure=overage,
                        recommended_action="Hold PO for budget owner sign-off or secure a reallocation before approving spend.",
                        department=department,
                        supplier_id=po["supplier_id"],
                    )
                )
    return exceptions


# ---------------------------------------------------------------------------
# Rule 4: duplicate invoice
# ---------------------------------------------------------------------------

def rule_duplicate_invoice(invoices: pd.DataFrame, purchase_orders: pd.DataFrame) -> List[ExceptionRecord]:
    """Flag groups of invoices against the same PO with the same amount.

    Matching on (po_id, amount) catches duplicates whether or not the
    duplicate_check_hash also matches; the hash is included in the
    description for additional context when it does.
    """
    exceptions: List[ExceptionRecord] = []
    po_lookup = purchase_orders.set_index("po_id")

    for (po_id, amount), group in invoices.groupby(["po_id", "amount"]):
        if len(group) <= 1:
            continue

        invoice_ids = ", ".join(group["invoice_id"].tolist())
        hashes = sorted(set(group["duplicate_check_hash"].astype(str)))
        hash_note = hashes[0] if len(hashes) == 1 else "/".join(hashes)
        duplicate_count = len(group) - 1
        exposure = round(float(amount) * duplicate_count, 2)

        department = ""
        supplier_id = ""
        if po_id in po_lookup.index:
            po_row = po_lookup.loc[po_id]
            department = po_row["department"]
            supplier_id = po_row["supplier_id"]

        exceptions.append(
            ExceptionRecord(
                po_id=po_id,
                exception_type="duplicate_invoice",
                description=(
                    f"{len(group)} invoices ({invoice_ids}) were submitted against PO {po_id} "
                    f"for the same amount of ${float(amount):,.2f} (hash {hash_note}), indicating "
                    f"a likely duplicate submission."
                ),
                financial_exposure=exposure,
                recommended_action="Place the duplicate invoice(s) on hold and confirm with AP and the supplier before releasing a second payment.",
                department=department,
                supplier_id=supplier_id,
            )
        )
    return exceptions


# ---------------------------------------------------------------------------
# Rule 5: policy threshold
# ---------------------------------------------------------------------------

def rule_policy_threshold(
    purchase_orders: pd.DataFrame, threshold: float = POLICY_THRESHOLD_AMOUNT
) -> List[ExceptionRecord]:
    """Flag any PO above the policy dollar threshold that requires extra approval."""
    exceptions: List[ExceptionRecord] = []

    for _, po in purchase_orders.iterrows():
        amount = float(po["amount"])
        if amount > threshold:
            exceptions.append(
                ExceptionRecord(
                    po_id=po["po_id"],
                    exception_type="policy_threshold",
                    description=(
                        f"PO {po['po_id']} (${amount:,.2f}) exceeds the ${threshold:,.2f} "
                        f"procurement policy threshold requiring an additional approval step."
                    ),
                    financial_exposure=amount,
                    recommended_action="Route to secondary approver / procurement leadership before payment release per policy.",
                    department=po["department"],
                    supplier_id=po["supplier_id"],
                )
            )
    return exceptions


# ---------------------------------------------------------------------------
# Rule 6: upcoming renewal
# ---------------------------------------------------------------------------

def rule_upcoming_renewal(
    purchase_orders: pd.DataFrame,
    suppliers: pd.DataFrame,
    reference_date: date = REFERENCE_DATE,
    window_days: int = RENEWAL_WINDOW_DAYS,
) -> List[ExceptionRecord]:
    """Flag POs against suppliers whose contract is expiring within the window."""
    exceptions: List[ExceptionRecord] = []
    sup = _supplier_lookup(suppliers)
    window_end = reference_date + timedelta(days=window_days)

    for _, po in purchase_orders.iterrows():
        supplier_id = po["supplier_id"]
        if supplier_id not in sup.index:
            continue
        supplier = sup.loc[supplier_id]
        contract_end = pd.Timestamp(supplier["contract_end_date"]).date()
        if reference_date <= contract_end <= window_end:
            days_left = (contract_end - reference_date).days
            exceptions.append(
                ExceptionRecord(
                    po_id=po["po_id"],
                    exception_type="upcoming_renewal",
                    description=(
                        f"PO {po['po_id']} (${po['amount']:,.2f}) is against {supplier['name']} "
                        f"({supplier_id}), whose contract ends {contract_end} "
                        f"({days_left} days from the {reference_date} review date)."
                    ),
                    financial_exposure=float(po["amount"]),
                    recommended_action="Confirm contract renewal status with the supplier before committing further spend.",
                    department=po["department"],
                    supplier_id=supplier_id,
                    supplier_name=supplier["name"],
                )
            )
    return exceptions


# ---------------------------------------------------------------------------
# Prioritization
# ---------------------------------------------------------------------------

def prioritize(exceptions: List[ExceptionRecord]) -> List[ExceptionRecord]:
    """Sort exceptions by financial_exposure, largest first."""
    return sorted(exceptions, key=lambda e: e.financial_exposure, reverse=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def detect_all(
    purchase_orders: pd.DataFrame,
    suppliers: pd.DataFrame,
    budgets: pd.DataFrame,
    invoices: pd.DataFrame,
    threshold: float = POLICY_THRESHOLD_AMOUNT,
    reference_date: date = REFERENCE_DATE,
    window_days: int = RENEWAL_WINDOW_DAYS,
) -> List[ExceptionRecord]:
    """Run all six rule checks and return exceptions sorted by financial exposure."""
    exceptions: List[ExceptionRecord] = []
    exceptions += rule_inactive_supplier(purchase_orders, suppliers)
    exceptions += rule_missing_documentation(purchase_orders, suppliers)
    exceptions += rule_budget_variance(purchase_orders, budgets)
    exceptions += rule_duplicate_invoice(invoices, purchase_orders)
    exceptions += rule_policy_threshold(purchase_orders, threshold=threshold)
    exceptions += rule_upcoming_renewal(purchase_orders, suppliers, reference_date=reference_date, window_days=window_days)
    return prioritize(exceptions)


def run_detection(data_dir: Optional[Path] = None) -> List[ExceptionRecord]:
    """Convenience entry point: load the synthetic CSVs and run full detection."""
    purchase_orders, suppliers, budgets, invoices = load_data(data_dir)
    return detect_all(purchase_orders, suppliers, budgets, invoices)
