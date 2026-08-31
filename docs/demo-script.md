# Demo Script (60-90 seconds)

A guided walkthrough a reader can follow verbatim against the running app
(`streamlit run app.py`).

---

**0:00 -- Orientation.**
"This is a procurement pre-payment exception review agent. Everything you're
about to see runs on synthetic data -- notice the disclosure right under the
title: 'Public portfolio prototype · Synthetic data.' We're in MOCK_MODE by
default, so there's no API key and no network call involved in anything
below."

**0:10 -- The numbers panel.**
"These three metrics are all literal counts, not claims: 48 synthetic
purchase orders, 6 exception-detection rules, and 53 automated tests
verified passing by `pytest` at release time. Every one of them traces back
to a file or a test run -- see `docs/evaluation-plan.md`."

**0:20 -- The illustrative forecast.**
"This chart shows cumulative financial exposure by month, built from the
same exceptions the rule engine just detected -- it's clearly labeled
'Illustrative / synthetic demo data' because it's a transparent sum, not a
prediction of future purchase orders."

**0:35 -- The prioritized queue.**
"Below that is every detected exception, sorted by dollar exposure, largest
first. At the top: PO-3047, a $68,000 purchase order that's both over the
$50,000 policy threshold and has pushed its Procurement budget line over
allocation -- two reasons to look at it before any payment goes out."

**0:55 -- The detail view and the human-in-the-loop action.**
"Selecting an exception shows the full plain-language explanation and the
recommended action. This agent never approves or blocks a payment itself --
a human reviewer has to explicitly choose Approve, Hold, or Escalate. Any
exception nobody has touched yet just shows 'pending.'"

**1:10 -- Reset.**
"Reset State clears every decision I just made back to pending, so the next
person can run through the same demo from a clean slate."

**1:20 -- Close.**
"That's the whole loop: deterministic detection, transparent prioritization,
a plain-language explanation for every alert, and a human checkpoint before
anything gets paid. No real companies, suppliers, or individuals are
represented anywhere in this dataset."

---

## Notes for whoever gives this demo

- If MOCK_MODE is off and `ANTHROPIC_API_KEY` is set, mention the LIVE-mode
  banner instead and clarify: only the explanation text changes; detection
  and dollar amounts are identical either way.
- Don't claim a hosted URL unless one has actually been verified live on
  Streamlit Community Cloud -- see the Maturity line at the top of
  `README.md`.
