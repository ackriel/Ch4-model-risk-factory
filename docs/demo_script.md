# 3-minute demo script

**Before recording:** `python main.py reset`, then double-click `start_dashboard.command`. Type a reviewer name in the sidebar. Use a screen recorder (on a Mac: QuickTime → File → New Screen Recording, or Cmd+Shift+5).

| Time | Who | Screen | Say |
|---|---|---|---|
| 0:00-0:20 | IE | Overview (all stages not started) | "A UK bank runs around 250 credit, fraud and pricing models in SAS, R and Python. SS1/23 requires each one to be documented and independently validated, and a single validation takes 8-12 weeks. At that pace the bank can never keep up." |
| 0:20-0:35 | IE | Overview, point at the 5 stages | "Our Model Risk Factory has five agents that discover, document, redevelop, validate and monitor a model estate, with a human approving every step. Every number is calculated by tested code, never by AI." |
| 0:35-0:55 | SE | **Model inventory** → Run → table → Approve | "The Discover agent reads the bank's legacy code without running it: an R scorecard, two Python models and a SAS program. It finds each model's method, inputs, owner and risk tier, and spots that all four sets of documentation are out of date, the oldest by nine years." |
| 0:55-1:10 | SE | **Documentation** → Run → click CR-PD-001 → source labels → Approve | "The Document agent drafts a model card for every model, and each section shows its source. It already flags a risk: this scorecard uses age directly." |
| 1:10-1:35 | SE | **Redevelopment** → Run → PASS and "Genuine - R executed now" → scatter → generated code → Approve | "The Redevelop agent runs the legacy R model live, generates the Python replacement, refits it independently and compares every coefficient and all 1,000 predictions. The largest difference is around 1e-15, against a tolerance of 1e-6." |
| 1:35-2:05 | CE | **Validation** → Run → CR-PR-003 → AUC → Fairness tab → Full HTML report → Approve | "The pricing model has a test AUC of 0.79, but its training AUC is 0.97: it's overfitting. All three models approve under-25s far less often; the pricing model's ratio is 0.42 against a 0.8 screen. Everything lands in a report a validator can sign off." |
| 2:05-2:25 | CE | **Monitoring** → drift, 0.6 → Run → alerts → Approve | "In production, the Monitor agent scores new applications. We simulate younger applicants with bigger loans: stability jumps past its alert threshold, and all three models are flagged for re-validation." |
| 2:25-2:45 | IE | **Estate health** → counts → by-language table → model list | "One verdict per model, with the reasons. Three models need re-validation, and the SAS model is blocked because no one can re-run it. You see at a glance which R, Python or SAS model needs attention." |
| 2:45-3:00 | IE | **Approvals & audit trail** | "Every run and decision is logged. If expert review drops from 40-60 days per model to around five, the bank saves roughly 90% of validation effort, with humans still making every call." |

Roles: SE = software engineer (drives the screen), CE = chemical engineer, IE = industrial engineer. If running long, skip the generated-code peek and the HTML report scroll.

## Backup lines for Q&A
- *"How do you stop the AI making up numbers?"* It never computes them: `validation/` does, with unit tests against known answers. The language model gets the numbers as input, and its text is labelled.
- *"What if R isn't installed?"* The agent uses recorded outputs from a genuine R run and says so. If neither exists, parity is marked SIMULATED and never presented as a real migration.
- *"Is this SS1/23 compliant?"* No such claim. It produces evidence that supports SS1/23 activities such as inventory, documentation, independent validation and monitoring. Humans remain accountable.
- *"Why not fix the age bias automatically?"* Whether age is a justified credit factor is a business and legal decision. The factory surfaces it with evidence; humans decide.
- *"What would you do next?"* Add the Taiwan credit dataset (30,000 customers, with a real sex field), use time-stamped data for genuine drift, and use an AI translator for messy legacy code, with the parity test as the safety net.
