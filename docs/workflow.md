# Workflow

Step-by-step user flow through `app.py`, matching the actual UI (not an
aspirational version of it).

## 1. Load and detect (automatic, on page load)

`app.py` calls `engine.load_data()` to read the four synthetic CSVs, then
`engine.detect_all(...)` to run all six rule checks and return every
detected `Exception`, already sorted by `financial_exposure` descending
(`engine.prioritize`). This happens once per session via `st.cache_data`.

## 2. Orientation

The reviewer sees, top to bottom:

1. The page title and the required disclosure line: **"Public portfolio
   prototype · Synthetic data."**
2. A mode banner: MOCK_MODE (default, no API key) or LIVE mode (Claude
   narration only -- detection is unaffected either way).
3. The **3-metric panel**: synthetic PO count (48), exception rule count (6),
   and verified automated-test count -- each a literal count from code or a
   pytest run, never invented (see `docs/evaluation-plan.md`).
4. A **Reset State** button that clears every recorded reviewer decision
   for the session back to the implicit `pending` state
   (`review.reset_all`).

## 3. Summary

- Total exceptions detected and total dollar exposure across all of them.
- Count of exceptions by type (`forecast.build_exception_counts_by_type`).
- A one-line breakdown of how many exceptions are currently pending,
  approved, held, or escalated for this session.

## 4. Illustrative forecast

A line chart of cumulative financial exposure by the month each underlying
PO was ordered (`forecast.build_monthly_exposure_forecast`), plus the
backing table. Clearly labeled **"Illustrative / synthetic demo data"** --
this is a transparent aggregation of already-detected exceptions, not a
predictive model of future spend.

## 5. Prioritized, filterable table

Every detected exception, sorted by financial exposure descending, with
filters for exception type and department. This is the reviewer's queue --
the exceptions most likely to cost money or create compliance risk are
always at the top.

## 6. Detail view and human review action

The reviewer selects one exception from the filtered list and sees:

- The full plain-language explanation (`llm.generate_explanation` -- a
  deterministic template in MOCK_MODE, or a Claude-narrated version of the
  same structured fields in LIVE mode).
- Financial exposure, severity, department, and supplier.
- Three explicit action buttons: **Approve**, **Hold**, **Escalate**
  (`review.apply_action`). Whichever is clicked overwrites the exception's
  status in session state; nothing is released or blocked in any real
  payment or workflow system.
- Any exception with no recorded action shows status **pending** -- the
  implicit fourth state.

## 7. Reset

Clicking **Reset State** at the top clears the entire `review_status` dict
(`review.reset_all`), returning every exception to `pending` so a visitor
can replay the demo from a clean slate without reloading the page.

## What this workflow is not

There is no persistence across sessions, no multi-user concurrency handling,
no audit log, and no connection to a real ERP, AP, or payment system at any
step. See `docs/limitations.md`.
