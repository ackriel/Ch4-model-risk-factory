# Business impact

## The problem in numbers (from the challenge brief)
- About **250** production models (credit, fraud, pricing) in SAS, R and Python.
- **8-12 weeks** per independent validation, so roughly **40-60 working days** of expert time per model.
- Under PRA SS1/23, each model needs current documentation and independent validation. At that pace, the estate needs about **40-60 person-years** for one validation cycle.

## What the prototype measured
| Measured | Result |
|---|---|
| Models discovered and inventoried | 4 of 4 (R, Python ×2, SAS), in about 0.01 s |
| Draft model cards | 4 of 4 |
| R → Python migration with parity proof | 1 of 1; largest prediction difference 1.2e-15 (tolerance 1e-6) |
| Full validation packs (performance, stability, fairness, findings, HTML report) | 3 of 3 executable models |
| Total machine time, all five stages | about 2-3 seconds |
| Issues the automated checks surfaced | Overfitting (GBM: train AUC 0.965 vs test 0.791), miscalibration (tree: mean PD 1.56× observed), age disparities in all 3 models, stale documentation (4.0-9.5 years), 1 model that cannot be independently re-run (SAS) |

## Estimated effect (assumptions stated)
| | Today | With factory |
|---|---|---|
| Effort per model | 40-60 days | **5 days**: an expert reviews the automated evidence pack (ASSUMPTION) |
| Estate of 250 models | 40-60 person-years | about 5 person-years |
| Effort reduction | - | **about 88-92%** |

The factory automates evidence gathering (inventory, documentation drafts, re-implementation, metric calculation, report writing). It does **not** automate judgement. The 5-day review figure is an assumption to be tested in a pilot, not a measurement.

## Value of the models themselves (cost matrix from the dataset)
Approving a defaulter costs 5 units; rejecting a good customer costs 1 unit. On the 300-loan test set, approving everyone costs 450 units:

| Model | Cost at the cost-optimal cut-off | Saving vs no model |
|---|---|---|
| CR-PD-001 (redeveloped scorecard) | 186 | 264 (59%) |
| CR-EW-002 (tree) | 189 | 261 (58%) |
| CR-PR-003 (GBM) | 153 | 297 (66%) |

This is why model risk matters: the models drive real money, and the validation findings (overfitting, miscalibration, fairness) put that value at risk.

## How a bank would measure success in a pilot
1. Elapsed time from "model selected" to "validation pack ready for review".
2. Reviewer hours per model, compared with the historical 8-12 weeks.
3. Share of automated findings that reviewers accept (precision), and issues reviewers find that the factory missed (recall).
4. Inventory coverage: share of models with current documentation, and its age.
5. Monitoring: time from drift to re-validation trigger.
