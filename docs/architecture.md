# Architecture

## Overview

The agent reads four synthetic CSVs, runs them through six independent
deterministic rule checks, prioritizes whatever those checks find by
financial exposure, optionally narrates each finding in plain English, and
surfaces everything in a Streamlit dashboard where a human reviewer
acknowledges or escalates each item before payment would proceed.

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

    L --> D[Streamlit dashboard\n(app.py)]
    D --> H[Human review:\nAcknowledge / Escalate]
```

## Components

- **`data/synthetic/`** -- fictional purchase orders, suppliers, budgets, and
  invoices with deliberately seeded exception conditions (inactive supplier,
  missing documentation, budget overage, duplicate invoice, policy-threshold
  PO, upcoming contract renewal).
- **`src/models.py`** -- the `Exception` dataclass shared by every layer:
  `po_id`, `exception_type`, `description`, `financial_exposure`,
  `recommended_action`, and a `severity` derived from the exposure amount.
- **`src/engine.py`** -- one pure function per exception type, each
  evaluated deterministically over the CSVs with pandas, plus a
  `prioritize()` function that sorts everything by `financial_exposure`
  descending. This is the only place detection logic or exposure math lives.
- **`src/llm.py`** -- takes an already-detected `Exception` and produces a
  human-readable explanation. In `MOCK_MODE` (default) this is a
  deterministic template built from the structured fields. When
  `MOCK_MODE=false` and `ANTHROPIC_API_KEY` is set, it asks Claude
  (`claude-sonnet-5`) to write the explanation instead -- the detection and
  dollar figures are never touched by the LLM either way.
- **`app.py`** -- Streamlit dashboard: summary metrics, a filterable
  prioritized table, a detail view with the explanation and recommended
  action, and an Acknowledge/Escalate control per exception that records the
  reviewer's decision in session state, standing in for a real human
  approval workflow.
