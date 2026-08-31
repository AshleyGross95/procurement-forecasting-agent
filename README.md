# Procurement Forecasting Agent

**Maturity:** Live public demo · Synthetic data · Explainable rules workflow

**Live demo:** https://procurement-forecasting-agent.streamlit.app/ (verified 2026-08-31 — confirmed real detection output: 26 exceptions / $500,900 total exposure across all 6 rule types, review-status tracking and Reset State visible)

## 1. Business problem

Procurement and finance teams manually comb through purchase orders,
supplier records, budgets, and invoices in spreadsheets to catch
pre-payment problems -- duplicate invoices, over-budget spend, inactive
suppliers -- and by the time someone notices, the payment has often already
gone out.

## 2. What the agent does

Runs six deterministic rule checks over purchase orders, suppliers,
budgets, and invoices to surface pre-payment exceptions, prioritizes them by
financial exposure (largest dollar risk first), generates a plain-language
explanation and recommended action for each one, shows an illustrative
forecast of exposure over time, and routes every exception to a human
reviewer for an explicit approve / hold / escalate decision before any
payment would proceed.

## 3. What this demo is

- A deterministic, rule-based exception engine (`src/engine.py`, six rule
  types) evaluated over 48 fictional purchase orders, 15 suppliers, 9
  budget lines, and 45 invoices in `data/synthetic/`.
- A working Streamlit review UI (`app.py`) with a real human-in-the-loop
  approve/hold/escalate step, backed by actual rule output, plus a
  "Reset State" control.
- An illustrative, non-predictive forecast chart built from the same
  detected exceptions (`src/forecast.py`), clearly labeled as such.
- An optional live narration call to Claude (`src/llm.py`) that only
  rewrites the explanation text -- detection and dollar amounts are
  unaffected.

## 4. What this demo is not

- Not real authentication or authorization -- there are no user accounts,
  roles, or access control of any kind.
- Not a live integration with any real ERP, AP, or payment system -- the
  only optional live call is the Claude narration described above.
- Not a hosted deployment yet -- see the Maturity line above; deployment to
  Streamlit Community Cloud happens as a separate step after this release
  pass.
- Not real data -- every PO, supplier, budget, and invoice in
  `data/synthetic/` is fictional. No real companies or individuals are
  represented.
- Not a predictive forecasting model -- the "illustrative forecast" is a
  transparent sum/cumulative-sum of already-detected exceptions, not a
  prediction of future purchase orders.

## 5. Key workflow

1. Load the four synthetic CSVs and run all six rule checks
   (`engine.detect_all`).
2. Prioritize every detected exception by financial exposure, descending.
3. Generate a plain-language explanation and recommended action per
   exception (mock template by default, optional live Claude narration).
4. Display the required disclosure line, the 3-metric panel, the
   illustrative forecast chart, and the filterable prioritized table.
5. A human reviewer selects an exception and explicitly clicks **Approve**,
   **Hold**, or **Escalate**; any untouched exception shows **pending**.
6. **Reset State** clears every decision for the session back to pending.

Full step-by-step detail: [`docs/workflow.md`](docs/workflow.md).

## 6. Demo metrics and how each is calculated

Displayed live in the app's 3-metric panel and restated here:

| Metric | Value | How it's calculated |
|---|---|---|
| Synthetic Purchase Orders | 48 | `len(purchase_orders)` where `purchase_orders = engine.load_data()[0]`, reading `data/synthetic/purchase_orders.csv`. Verified by `tests/test_data_integrity.py::test_purchase_orders_row_count_is_exactly_48`. |
| Exception Rules | 6 | Literal count of `rule_*` functions in `src/engine.py`, matching the 6 values of `ExceptionType` in `src/models.py`. Verified by `tests/test_engine_scale.py::test_exactly_six_rule_functions_exist`. |
| Automated Tests (verified) | 53 | Exact count from running `pytest -v` against this repo at release time -- see section 12. Hardcoded in `app.py::NUM_VERIFIED_TESTS` with a comment to re-verify before changing it. |

No metric anywhere in this app or README is invented -- each is a literal
seeded-record count, a literal count of implemented rules/states, or a
verified test count, per the portfolio's truthfulness standard.

## 7. Architecture overview

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
    P --> F[Illustrative forecast\n(src/forecast.py)]

    L --> D[Streamlit dashboard\n(app.py)]
    F --> D
    D --> H[Human review:\nApprove / Hold / Escalate\n(src/review.py)]
    H --> D
```

Component-by-component description: [`docs/architecture.md`](docs/architecture.md).
Data schemas and row counts: [`docs/data-model.md`](docs/data-model.md).

## 8. Integration matrix

| Integration | Status | Notes |
|---|---|---|
| LLM narration (Claude, `src/llm.py`) | `mock` by default / `live` when `MOCK_MODE=false` + a valid `ANTHROPIC_API_KEY` | Only rewrites the explanation text for an already-detected exception; never changes detection or financial exposure numbers. This is the only integration point with a live option. |
| ERP / AP source data | `mock` | Synthetic CSVs in `data/synthetic/`; no live connection to any ERP or AP system exists or is built. |
| Approval / workflow routing (Approve / Hold / Escalate) | `mock` | Recorded in Streamlit session state only (`src/review.py`); not wired to any real approval, ticketing, or payment system. |
| Payment system | `none` / planned | This agent never releases or blocks a payment in any real system; see `docs/production-path.md` for what a real connection would require. |

## 9. Local setup

```bash
git clone <this-repo-url>
cd procurement-forecasting-agent
pip install -r requirements.txt
streamlit run app.py
```

Runs in mock mode by default with zero API keys required -- all detection,
exposure math, and recommended actions come from the deterministic rule
engine in `src/engine.py` over the synthetic CSVs in `data/synthetic/`.

## 10. Environment variables

Copy `.env.example` to `.env` to configure locally:

| Variable | Default | Purpose |
|---|---|---|
| `MOCK_MODE` | `true` | `true`: fully deterministic, no API key needed. `false`: enables LIVE-mode Claude narration (still requires `ANTHROPIC_API_KEY`). |
| `ANTHROPIC_API_KEY` | (empty) | Only read when `MOCK_MODE=false`; used solely by `src/llm.py` to narrate an already-detected exception. |

## 11. Deployment instructions (Streamlit Community Cloud)

1. Push this repo to GitHub (already done for this portfolio).
2. In Streamlit Community Cloud, create a new app pointing at:
   - **Repository:** this repo
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. No secrets are required for the default mock-mode deploy.
4. To enable LIVE-mode narration instead, add these two entries in the
   app's **Secrets** panel in Streamlit Cloud:
   ```
   MOCK_MODE = "false"
   ANTHROPIC_API_KEY = "your-key-here"
   ```
5. This release pass does not perform deployment -- see the Maturity line
   at the top of this README, which will be updated to "Live public demo"
   once a real URL is verified.

## 12. Test and evaluation approach

Full evaluation methodology: [`docs/evaluation-plan.md`](docs/evaluation-plan.md).

```bash
pytest -v
```

Exact verified result at release time: **53 passed, 0 failed** (53 tests
total). Coverage includes: every seeded exception case for all six rule
types at both the original and expanded (48-PO) dataset scale,
prioritization ordering at both scales, referential integrity and row
counts of the synthetic data, the four-state approve/hold/escalate review
workflow, and the illustrative forecast's aggregation correctness.

## 13. Accessibility and privacy notes

- Built entirely from Streamlit's native widgets (`st.button`, `st.metric`,
  `st.selectbox`, `st.multiselect`, `st.dataframe`, `st.line_chart`), all of
  which are keyboard-operable and screen-reader-labeled by Streamlit itself.
- Streamlit does not expose fine-grained custom focus-order control; this
  app does not attempt to override Streamlit's default tab order.
- No PII is collected, stored, or displayed anywhere -- every record in
  `data/synthetic/` is fictional, and the only user input is UI interaction
  (filters, button clicks), none of which is persisted beyond the session.

## 14. Known limitations

See [`docs/limitations.md`](docs/limitations.md) for the full list
(no auth, no persistence, no audit trail, static synthetic data, no real
ERP/AP/payment integration). No detection-logic defects were found in the
prior audit or in this release pass.

## 15. Production-readiness roadmap

See [`docs/production-path.md`](docs/production-path.md) for the full
prototype -> pilot -> production plan, including authentication,
persistence, an audit log, configurable thresholds, alerting, and adoption
metrics.

## 16. Screenshot

Screenshot pending first Streamlit Cloud deploy.

---

## Human review, approval & exceptions

This agent never releases or blocks a payment. Every detected exception is
presented to a human AP reviewer in the dashboard with its recommended
action; the reviewer explicitly clicks **Approve**, **Hold**, or
**Escalate** for each item, or leaves it **pending**. That decision is
recorded in Streamlit session state as a stand-in for a real approval
workflow -- it is not wired to any payment system. **Reset State** clears
every decision back to pending. See [`docs/workflow.md`](docs/workflow.md).

## Disclaimer

All data in this repository is synthetic and fictional -- no real
companies, suppliers, or individuals are represented. The exception logic
here is an illustrative rule design for a portfolio demo, not a certified
audit, compliance, or financial control, and should not be used as-is to
make real payment decisions.

## License

MIT -- see [LICENSE](LICENSE).
