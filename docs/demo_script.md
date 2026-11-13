# 3-minute demo script

**Before recording:** `python main.py reset`, then `streamlit run app.py`. Type a reviewer name in the sidebar. Use a screen recorder (on a Mac: QuickTime → File → New Screen Recording, or Cmd+Shift+5).

| Time | Screen | Say |
|---|---|---|
| 0:00-0:20 | Overview page | "A UK bank runs about 250 models, and each independent validation takes 8-12 weeks. Our Model Risk Factory automates the evidence gathering across five stages, with a human approving every step. All numbers come from tested Python code; AI only writes clearly labelled text." |
| 0:20-0:45 | **Model inventory** → Run → table → Approve | "The Discover agent scans the bank's legacy code without running it: one R scorecard, two Python models and a SAS program. It finds the methodology, inputs, owner and documentation age; all four sets of documents are out of date. I approve the inventory." |
| 0:45-1:05 | **Documentation** → Run → open CR-PD-001 card | "The Document agent drafts a model card for each model. Facts are extracted from the code, and each section shows its source. It already raises a risk: this scorecard uses age directly." Approve. |
| 1:05-1:40 | **Redevelopment** → Run → metrics, scatter, generated code | "The Redevelop agent runs the legacy R model, generates Python code from its specification, refits it independently and compares all 1,000 predictions and every coefficient. The largest difference is 1e-15, against a tolerance of 1e-6. That's genuine R-to-Python parity." Approve. |
| 1:40-2:20 | **Validation** → Run → CR-PR-003 → findings → Fairness tab → Full HTML report | "Validation computes discrimination, calibration, stability and fairness for every model, then applies explicit rules to produce findings and a RAG rating. The pricing model has a strong test AUC of 0.79, but the train AUC is 0.97: it's overfitting. All three models approve under-25s much less often. Everything goes into an HTML report a validator can sign off." Approve. |
| 2:20-2:45 | **Monitoring** → drift, severity 0.6 → Run → alerts | "In production, the Monitor agent scores new applications. Here we simulate a shift towards younger applicants with bigger loans. PSI jumps above 0.25 and all three models are flagged for re-validation." |
| 2:45-3:00 | **Approvals & audit trail** | "Every run and every decision is logged with who, what and when. With 5 days of expert review instead of 40-60, we estimate an 88-92% effort reduction across the estate, with humans still making every call." |

## Backup lines for Q&A
- *"How do you stop the AI making up numbers?"* It never computes them: `validation/` does, with unit tests against known answers. The language model gets the numbers as input, and its text is labelled.
- *"What if R isn't installed?"* The agent uses recorded outputs from a genuine R run and says so. If neither exists, parity is marked SIMULATED and never presented as a real migration.
- *"Is this SS1/23 compliant?"* No such claim. It produces evidence that supports SS1/23 activities such as inventory, documentation, independent validation and monitoring. Humans remain accountable.
- *"Why not fix the age bias automatically?"* Whether age is a justified credit factor is a business and legal decision. The factory surfaces it with evidence; humans decide.
