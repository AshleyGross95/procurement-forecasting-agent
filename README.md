# Procurement Forecasting Agent

**Surfaces the pre-payment exceptions most likely to cost money or trigger compliance risk, ranked by financial exposure, before an invoice is ever paid.**

## What this demonstrates

- Rule-based exception detection over messy, multi-source operational data (POs, suppliers, budgets, invoices) -- the kind of AP/procurement control most enterprises run manually in spreadsheets.
- Prioritization by financial impact rather than by date or department, so a reviewer's limited time goes to the exceptions that matter most.
- A clear human-in-the-loop checkpoint (acknowledge/escalate) that keeps an AI-assisted review process auditable rather than autonomous.

## Demo moment

A reviewer opens the dashboard and immediately sees, at the top of the prioritized table, **PO-3010 -- a $62,000 purchase order flagged for two reasons at once**: it exceeds the $50,000 policy threshold requiring extra approval, and its invoice was submitted twice (two invoices, same PO, same amount, same hash) for a duplicate-payment exposure of $62,000. The detail panel explains both findings in plain language and recommends holding the duplicate for AP confirmation before any payment goes out. The reviewer clicks **Escalate**, and that decision is recorded for the session.

## Architecture

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

See [`docs/architecture.md`](docs/architecture.md) for a component-by-component description.

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app.py
```

Runs in mock mode by default with zero API keys required -- all detection, exposure math, and recommended actions come from the deterministic rule engine in `src/engine.py` over the synthetic CSVs in `data/synthetic/`.

## Switching to live mode

Copy `.env.example` to `.env`, then set:

```
MOCK_MODE=false
ANTHROPIC_API_KEY=your-key-here
```

In live mode, `src/llm.py` calls Claude (`claude-sonnet-5`) to write a more natural explanation of each already-detected exception. Detection and financial exposure numbers are unaffected -- they remain 100% rule-based in both modes.

## Human review, escalation & exceptions

This agent never releases or blocks a payment. Every detected exception is presented to a human AP reviewer in the dashboard with its recommended action; the reviewer explicitly clicks **Acknowledge** (reviewed, no further action needed) or **Escalate** (needs a second set of eyes / budget owner / supplier follow-up) for each item. That decision is recorded in Streamlit session state as a stand-in for a real approval workflow (e.g. routing into an AP or procurement system) -- it is not wired to any payment system.

## Evaluation

"Correct" for this agent means:

- Every seeded exception condition in `data/synthetic/` (inactive supplier, missing documentation, budget variance, duplicate invoice, policy threshold, upcoming renewal) is detected by its corresponding rule.
- The prioritized list is always sorted by `financial_exposure` descending.
- A clean PO/supplier/budget/invoice combination with none of the seeded problems produces zero exceptions -- the engine never flags without cause.

Run the test suite with:

```bash
pytest
```

## Roadmap

- **Prototype (this repo):** deterministic rule engine over static synthetic CSVs, single-session Streamlit review UI.
- **Pilot:** connect to a real (sandboxed) ERP/AP export on a schedule, add reviewer accounts so acknowledge/escalate persists across sessions instead of session state.
- **Production controls:** audit log of every detection and reviewer decision, role-based access, configurable thresholds per business unit, alerting on high-severity exceptions.
- **Rollout & adoption measurement:** track reviewer time-to-decision per exception, dollar exposure caught before payment vs. after, and false-positive rate reported back by reviewers.

## Disclaimer

All data in this repository is synthetic and fictional -- no real companies, suppliers, or individuals are represented. The exception logic here is an illustrative rule design for a portfolio demo, not a certified audit, compliance, or financial control, and should not be used as-is to make real payment decisions.

## License

MIT -- see [LICENSE](LICENSE).
