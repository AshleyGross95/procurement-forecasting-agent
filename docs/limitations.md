# Known Limitations

These are intentional scope boundaries of a portfolio prototype, not
defects. The independent audit that preceded this release pass found no
defects in the rule engine, and this pass did not introduce any -- it only
expanded the seeded dataset, added tests, and extended the UI.

## By design (prototype scope)

- **No real authentication or authorization.** Anyone with the URL sees and
  can click everything; there are no user accounts or roles.
- **No persistence.** Review decisions (`approve` / `hold` / `escalate`)
  live only in Streamlit's in-memory `session_state` and vanish when the
  session ends or "Reset State" is clicked. There is no database.
- **No audit trail.** A reviewer's decision history is not logged anywhere
  beyond the current in-memory status -- there is no record of who acted,
  when, or what the previous status was.
- **No multi-user concurrency handling.** Each Streamlit session has its own
  isolated state; there is no shared queue or locking if multiple reviewers
  were to use the same deployment.
- **Static synthetic CSVs.** `data/synthetic/` is a fixed snapshot with no
  scheduled refresh, upload mechanism, or connection to a live ERP/AP
  source.
- **No real ERP, AP, or payment system integration.** The only optional live
  network call anywhere in this repo is the Claude narration in
  `src/llm.py`, and it only rewrites explanation text -- it never touches
  detection, dollar amounts, or any payment action.
- **The illustrative forecast is not a predictive model.** It is a
  transparent sum/cumulative-sum aggregation of already-detected exceptions
  by month (`src/forecast.py`), clearly labeled "Illustrative / synthetic
  demo data" in the UI. It does not forecast future purchase orders or
  future exceptions.
- **Fixed reference date for renewal detection.** `rule_upcoming_renewal`
  uses a fixed `REFERENCE_DATE` (2026-08-30) rather than the real
  wall-clock date, so the bundled synthetic data always produces the same
  reviewable result regardless of when the demo is actually run.

## Explicitly not found

No detection-logic defects, no incorrect prioritization, and no referential
integrity issues were found in the expanded dataset -- see
`docs/evaluation-plan.md` for the full test suite that checks this and its
exact, verified pass count.

## What would need to change for a real deployment

See `docs/production-path.md` for the prototype -> pilot -> production
roadmap, including authentication, persistence, an audit log, and a real
data source.
