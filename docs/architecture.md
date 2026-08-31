# Architecture

## Overview

The agent reads four synthetic CSVs (48 purchase orders, 15 suppliers, 9
budget lines, 45 invoices), runs them through six independent deterministic
rule checks, prioritizes whatever those checks find by financial exposure,
optionally narrates each finding in plain English, aggregates the results
into an illustrative forecast chart, and surfaces everything in a Streamlit
dashboard where a human reviewer explicitly approves, holds, or escalates
each item before payment would proceed.

```mermaid
flowchart TD
    subgraph Data["Synthetic data (data/synthetic/)"]
        PO[purchase_orders.csv]
        SUP[suppliers.csv]
        BUD[budgets.csv]
        INV[invoices.csv]
    end

    subgraph Rules["Deterministic rule checks (src/engine.py)"]
        R1[inactive_supplier]
        R2[missing_documentation]
        R3[budget_variance]
        R4[duplicate_invoice]
        R5[policy_threshold]
        R6[upcoming_renewal]
    end

    PO --> R1
    SUP --> R1
    PO --> R2
    SUP --> R2
    PO --> R3
    BUD --> R3
    INV --> R4
    PO --> R4
    PO --> R5
    PO --> R6
    SUP --> R6

    R1 --> P[Prioritize by financial_exposure\n(src/engine.py: prioritize)]
    R2 --> P
    R3 --> P
    R4 --> P
    R5 --> P
    R6 --> P

    P --> L[Explanation layer\n(src/llm.py)\nTemplate in MOCK_MODE\nor live Claude call]
    P --> F[Illustrative forecast\n(src/forecast.py)\nMonthly cumulative exposure,\ncounts by type]

    L --> D[Streamlit dashboard\n(app.py)]
    F --> D
    D --> H[Human review:\nApprove / Hold / Escalate\n(src/review.py)]
    H --> D
```

## Components

- **`data/synthetic/`** -- fictional purchase orders, suppliers, budgets, and
  invoices with deliberately seeded exception conditions (inactive supplier,
  missing documentation, budget overage, duplicate invoice, policy-threshold
  PO, upcoming contract renewal), now at a 48-PO scale with multiple seeded
  cases per rule type. See `docs/data-model.md` for exact schemas and row
  counts.
- **`src/models.py`** -- the `Exception` dataclass shared by every layer:
  `po_id`, `exception_type`, `description`, `financial_exposure`,
  `recommended_action`, and a `severity` derived from the exposure amount.
- **`src/engine.py`** -- one pure function per exception type, each
  evaluated deterministically over the CSVs with pandas, plus a
  `prioritize()` function that sorts everything by `financial_exposure`
  descending. This is the only place detection logic or exposure math lives,
  and it is unmodified from the independently audited build pass.
- **`src/llm.py`** -- takes an already-detected `Exception` and produces a
  human-readable explanation. In `MOCK_MODE` (default) this is a
  deterministic template built from the structured fields. When
  `MOCK_MODE=false` and `ANTHROPIC_API_KEY` is set, it asks Claude
  (`claude-sonnet-5`) to write the explanation instead -- the detection and
  dollar figures are never touched by the LLM either way.
- **`src/forecast.py`** -- pure aggregation over an already-detected list of
  `Exception` records: cumulative financial exposure by PO order-month, and
  counts by exception type. Not a predictive model; always labeled
  "Illustrative / synthetic demo data" in the UI.
- **`src/review.py`** -- the four-state human review workflow (pending /
  approved / held / escalated) as pure functions operating on a plain dict,
  independent of Streamlit so it is directly unit-testable
  (`tests/test_review.py`).
- **`app.py`** -- Streamlit dashboard: the required public-prototype
  disclosure, a 3-metric panel (PO count / rule count / verified test
  count), summary metrics, the illustrative forecast chart, a filterable
  prioritized table, a detail view with the explanation and recommended
  action, explicit Approve/Hold/Escalate controls per exception, and a
  Reset State control that clears all review decisions back to pending.
