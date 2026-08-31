# Data Model

This document describes the synthetic source tables in `data/synthetic/`, the
shared `Exception` schema in `src/models.py`, and the derived shapes used by
the review workflow (`src/review.py`) and the illustrative forecast
(`src/forecast.py`). Nothing in this document is live data -- every row is
fictional, generated for this portfolio demo.

## Source tables (`data/synthetic/`)

### `purchase_orders.csv` -- 48 rows

| Column | Type | Notes |
|---|---|---|
| `po_id` | string, unique | e.g. `PO-3001` |
| `supplier_id` | string, FK -> `suppliers.supplier_id` | |
| `department` | string | cost center label, e.g. `Facilities`, `Finance` |
| `amount` | float | PO dollar amount |
| `budget_line` | string, FK -> `budgets.budget_line` | |
| `order_date` | date (`YYYY-MM-DD`) | parsed by `engine.load_data()` |
| `status` | string | `approved` / `pending_approval` / `open` (informational; not read by any rule) |

### `suppliers.csv` -- 15 rows

| Column | Type | Notes |
|---|---|---|
| `supplier_id` | string, unique | e.g. `SUP-001` |
| `name` | string | fictional supplier name |
| `active` | bool | drives `rule_inactive_supplier` |
| `last_transaction_date` | date | context only |
| `has_current_documentation` | bool | drives `rule_missing_documentation` |
| `contract_end_date` | date | drives `rule_upcoming_renewal` |

### `budgets.csv` -- 9 rows

| Column | Type | Notes |
|---|---|---|
| `budget_line` | string, unique | e.g. `BL-FAC-01` |
| `department` | string | cost center this budget line belongs to |
| `fiscal_year` | int | |
| `allocated_amount` | float | ceiling for the fiscal year |
| `spent_to_date` | float | baseline spend before the seeded POs are applied |

### `invoices.csv` -- 45 rows

| Column | Type | Notes |
|---|---|---|
| `invoice_id` | string, unique | e.g. `INV-6001` |
| `po_id` | string, FK -> `purchase_orders.po_id` | more than one invoice can share a `po_id` |
| `amount` | float | drives `rule_duplicate_invoice` when it repeats for the same `po_id` |
| `invoice_date` | date | |
| `duplicate_check_hash` | string | included in the exception description for context; matching on `(po_id, amount)` is what actually triggers the rule |

Referential integrity (every `supplier_id`, `budget_line`, and invoice
`po_id` resolves to a real row in its referenced table) is enforced by
`tests/test_data_integrity.py`, not by any runtime constraint -- these are
flat CSVs, not a database.

## `Exception` (`src/models.py`)

The one schema every layer (`src/engine.py`, `src/llm.py`, `src/forecast.py`,
`app.py`) shares:

```python
@dataclass
class Exception:
    po_id: str
    exception_type: str        # one of the 6 values below
    description: str           # human-readable, rule-generated
    financial_exposure: float  # always rule-computed, never LLM-generated
    recommended_action: str
    department: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    severity: str = field(init=False)  # derived from financial_exposure
```

`exception_type` is one of exactly six values (`ExceptionType` enum):
`budget_variance`, `duplicate_invoice`, `missing_documentation`,
`inactive_supplier`, `policy_threshold`, `upcoming_renewal`.

`severity` is derived, not stored input, via `severity_from_exposure()`:

| Exposure | Severity |
|---|---|
| >= $50,000 | critical |
| >= $20,000 | high |
| >= $5,000 | medium |
| < $5,000 | low |

`unique_id` (a property, `f"{po_id}::{exception_type}"`) is the stable key
used everywhere a single PO carries more than one exception type at once
(e.g. `PO-3010` is both `duplicate_invoice` and `policy_threshold`).

## Review state (`src/review.py`)

Not a table -- an in-memory `dict[str, str]` keyed by `Exception.unique_id`,
held in `st.session_state["review_status"]`. Only three values are ever
written to it (the fourth, `pending`, is the default returned for any key
not present):

```
pending (implicit default) -> approved | held | escalated
```

See `docs/workflow.md` for the full review flow and `docs/limitations.md`
for what this state machine intentionally does not do (persistence, audit
trail, multi-user).

## Forecast aggregates (`src/forecast.py`)

Two derived, illustrative-only shapes built from an already-detected list of
`Exception` records -- no new data, no prediction model:

- `build_monthly_exposure_forecast(exceptions, purchase_orders)` -> DataFrame
  with columns `month`, `monthly_exposure`, `cumulative_exposure`, one row
  per calendar month that has at least one exception (joined back to the
  PO's `order_date`).
- `build_exception_counts_by_type(exceptions)` -> DataFrame with columns
  `exception_type`, `count`, sorted descending by count.
