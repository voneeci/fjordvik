# Phase 2 forecast: how the evaluation was set

Synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional, and nothing
here describes real pumps or a real warehouse.

`evaluation.json` fixes the test before any forecast code exists (GUARDRAILS.md A9 and E1,
phase rules F1 and F2). It was written on 3 November 2026 from Reece's phase 2 prompt and
his answers in the question boxes, and committed before the first code commit. It is never
changed to make a result pass.

What it fixes:

- **The demand.** Monthly units per warehouse (Oulu FI03, Tartu EE02) and part family, from
  every order line, service technician lines included, so the forecast matches what the
  warehouse ships and what finance reports.
- **The dates.** Training only to March 2024; validation scores April to November 2024;
  December 2024 is a gap month scored in neither period (E1); test scores January to
  December 2025. Origins step a month at a time, each with at least 15 months of training.
- **The minimum.** A warehouse needs 6 test origins for a forecast length to count. Tartu
  opened in July 2024, so it has too few and is reported apart.
- **The settings that may be chosen**, and how: the moving-average window (3, 6 or 12) and
  whether the driver model has a season term, on validation origins only. The choice goes
  into `split_lock.json`, committed before the test run.
- **The pass marks**, Reece's: the driver model's mean MASE (mean absolute scaled error)
  below seasonal naive's and below the best benchmark's, and 80% intervals that hold 70 to
  90% of actuals, for both the 3-month and the 6-month forecast.

The builder chat wrote these rules, as phase 2 has no question set for a second chat to
write (that applies from phase 6).
