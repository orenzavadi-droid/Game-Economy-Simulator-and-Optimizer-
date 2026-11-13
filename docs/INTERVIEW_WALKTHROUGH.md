# Interview preparation — deferred walkthrough

This is the outline for a separate teaching session, not a claim that the author already learned every technical step.

1. Define the business problem: too much currency vs friction preventing upgrades.
2. Explain why a fixed original cohort and persona segmentation were chosen.
3. Trace a single coin from quest/source into wallet and out through progression/sink.
4. Derive currency conservation and explain why churn does not destroy coins.
5. Explain the retention denominator and all economy-health metrics.
6. Walk through an event record and three SQLite queries.
7. Show baseline versus scenarios and interpret differences.
8. Explain decision score, guardrails, Pareto frontier and train/holdout split.
9. Explain the selected scenario's upside and **its explicit tradeoff**.
10. Critique the model: synthetic behavior, uncalibrated choices, survivor bias, no real-money monetization.
11. Practice an interviewer case: player complaints about progression plus rising coin inventories.
12. Reconstruct results from scratch using Python and the HTML dashboard.

Expected outcome: the candidate can explain **why** each engineering and modeling choice was made, defend a tradeoff, and clearly separate simulated evidence from real causal validation.
