# Production Path

Expanded version of the README's Roadmap section: what changes at each stage
between this prototype and a real production procurement control.

## Prototype (this repo)

- Deterministic rule engine (`src/engine.py`, six rule types) over static
  synthetic CSVs (48 purchase orders, 15 suppliers, 9 budget lines, 45
  invoices).
- Single-session Streamlit review UI (`app.py`) with an explicit
  approve/hold/escalate action per exception, recorded in in-memory session
  state only, plus a "Reset State" control.
- Illustrative, non-predictive forecast chart (`src/forecast.py`) built from
  the same detected exceptions.
- Optional LIVE-mode narration via Claude (`src/llm.py`) that only rewrites
  the explanation text for an already-detected exception -- never detection
  or dollar amounts.
- No authentication, no persistence, no audit log, no real data source.

## Pilot

- Replace the static CSVs with a scheduled, read-only export from a real
  (sandboxed, non-production) ERP/AP system -- still batch, not real-time.
- Add reviewer accounts (even a simple allowlist) so approve/hold/escalate
  decisions persist across sessions in a real database instead of
  `st.session_state`.
- Add a minimal audit log table: who took which action, on which exception,
  when, and what the prior status was.
- Keep the same six deterministic rules; make thresholds
  (`POLICY_THRESHOLD_AMOUNT`, `RENEWAL_WINDOW_DAYS`) configurable per
  business unit instead of hardcoded module constants.
- Validate the rule engine's output against a sample of real (anonymized or
  synthetic-but-representative) historical procurement data with known
  outcomes, to sanity-check exposure math and severity bands before any
  real reviewer relies on it.

## Production controls

- Full audit log of every detection run and every reviewer decision,
  immutable and exportable for compliance review.
- Role-based access control: who can view which department's exceptions,
  who can approve vs. only escalate.
- Configurable, versioned rule thresholds per business unit or region, with
  change history.
- Alerting (email/Slack/ticketing) on newly detected high-severity
  exceptions instead of requiring a reviewer to open the dashboard.
- A real connection to the AP/payment system so an "Approve" decision can
  actually clear a hold, and an "Escalate" decision can actually open a
  ticket -- with appropriate safeguards so the agent still never
  autonomously releases a payment.
- Formal validation/monitoring of rule performance over time (false-positive
  rate, time-to-decision) with a documented process for adjusting
  thresholds.

## Rollout & adoption measurement

- Reviewer time-to-decision per exception, before and after adoption.
- Dollar exposure caught before payment vs. exposure that would have been
  caught only after payment under the prior (manual/spreadsheet) process.
- False-positive rate as reported back by reviewers, tracked per rule type,
  to identify which thresholds need tuning first.
- Reviewer-reported trust/usability feedback on the explanation quality
  (mock template vs. LIVE Claude narration, if enabled).
