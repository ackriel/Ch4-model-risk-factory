# Responsible AI note - Model Risk Factory (Challenge 04)

**Data used.** We use only public data: the corrected *South German Credit* dataset (UCI, CC BY 4.0, Grömping 2019), with 1,000 anonymised loans from 1973-1975. It contains no personal data and nothing from EXL or any client. The "legacy models" are our own code, written to resemble a bank's model estate.

**Where AI is used, and where it is not.**

| Component | Method | AI? |
|---|---|---|
| Model discovery (inventory) | Regex and Python `ast` static analysis; scanned code is never executed | No |
| Model-card facts (inputs, target, settings) | Extracted from code | No |
| Model-card narrative and report commentary | Rule-based templates by default; optionally Claude (temperature 0, cached) | Optional, labelled |
| R→Python migration | Template-based code generation from the R model's exported spec; refit by maximum likelihood | No |
| All metrics (AUC, KS, PSI, fairness, parity, cost) | Deterministic Python (`validation/`), unit-tested against known answers | No |
| Findings and RAG rating | Explicit rules with thresholds listed in `core/config.py` | No |

When Claude is enabled, it receives only facts and numbers already computed, and is told not to invent or recalculate them. Every text block shows its source (`extracted`, `rule_based`, `ai_generated (model)`), so a reviewer can always tell AI-written prose from calculated results.

**Human oversight.** Five approval gates: no stage can run until a named reviewer approves the previous one. Re-running a stage resets later approvals, so an approval never covers outputs it didn't see. All model cards are marked *DRAFT - requires human review*. Automated approvals (used only in tests) are recorded as `automated: true`.

**Reproducibility and audit trail.** Fixed random seeds; a fixed, committed train/test split; source-file SHA-256 hashes in the inventory; R version and run time recorded with the legacy outputs; LLM responses cached. Every run, approval, rejection and invalidation is appended to `outputs/audit_log.jsonl`, with who, when and what.

**Fairness.** We checked which demographic fields exist before testing anything.

- **Age:** all three models approve under-25s far less often (approval-rate ratios of 0.19-0.55 against the "25 and over" group), and all three use age directly as an input. We flag this for justification instead of "fixing" it automatically: age can be a legitimate credit factor, but it's a protected characteristic under the Equality Act 2010, and its use needs a documented rationale.

- **Sex:** the dataset can't separate sex from marital status, so we **do not claim** a sex fairness test. We report by the combined field, with that caveat.

- **Foreign worker:** only 9 people in the test set, so results are marked low-confidence.

- The metrics used (approval-rate ratio with a 0.8 screen, equal-opportunity gap) are screening heuristics, not legal determinations.

**Limitations.**

- The data is small, old, non-UK and oversampled for defaults (30% default rate). Results show the method, not a real portfolio.

- Stability between train and test comes from the same period. Drift over time is simulated in the Monitor stage, and outcomes are only known because it's a simulation.

- The SAS model can't be executed, so it is documented but not validated (shown as "NOT VALIDATED", not silently skipped).

- The rule-based narrative is generic. The Claude narrative can be wrong and must be reviewed.

- The business-impact figures rely on an assumed 5-day human review time.

**Safeguards and what we do not claim.** The factory produces evidence for an independent validator; it does not replace one. Producing documentation or a validation report **does not demonstrate compliance with PRA SS1/23**. Thresholds are configurable and visible. The prototype runs locally, with no cloud services and no data leaving the machine (except optional Claude API calls, which contain only aggregate results and code).

**AI tools declaration.** Claude (Anthropic) was used as a coding assistant to write the code, tests and documentation, which team members reviewed and ran. At run time, Claude is optional and used only for labelled prose.
