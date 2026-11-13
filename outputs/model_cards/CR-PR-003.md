# Model card: Risk-Based Pricing Gradient Boosting Model (CR-PR-003)

> **DRAFT - requires human review** - generated 2026-11-13T11:47:33Z by the Document agent.

## Facts (extracted from source code)

| Field | Value |
|---|---|
| Owner | Pricing & Product Analytics |
| Language | Python |
| Methodology detected | Gradient boosting (scikit-learn) |
| Target variable | default_flag |
| Target definition | 1 = bad risk (credit contract not complied with), 0 = good risk |
| Data source | data/train.csv and data/test.csv via core.data.load_split() |
| Risk tier | Tier 1 - material (customer decisions / financial reporting) |
| Executable in factory | True |
| Source file | legacy_models/pricing_gbm.py |

### Input variables

| Variable | Type | Protected / proxy |
|---|---|---|
| duration | numeric |  |
| amount | numeric |  |
| age | numeric | YES |
| status | categorical |  |
| credit_history | categorical |  |
| purpose | categorical |  |
| savings | categorical |  |
| employment_duration | categorical |  |
| installment_rate | categorical |  |
| personal_status_sex | categorical | YES |
| other_debtors | categorical |  |
| present_residence | categorical |  |
| property | categorical |  |
| other_installment_plans | categorical |  |
| housing | categorical |  |
| number_credits | categorical |  |
| job | categorical |  |
| people_liable | categorical |  |
| telephone | categorical |  |
| foreign_worker | categorical | YES |

### Settings found in code

- `n_estimators` = 150
- `learning_rate` = 0.05
- `max_depth` = 3
- `subsample` = 0.8
- `random_state` = 42

## Narrative (source: rule_based)

### Purpose

Estimate default risk to set the interest-rate band offered to applicants. Business use: Risk-based pricing of personal loans.

### Methodology

Gradient-boosted ensemble of shallow decision trees; each tree corrects the errors of the previous ones. Output is a PD estimate.

### Assumptions

- Development sample is representative.
- Hyperparameters chosen on the development data generalise.

### Limitations

- Low intrinsic interpretability: individual decisions need explanation tools (e.g. SHAP).
- Higher risk of overfitting on a small sample (700 training rows).
- Developed on 1,000 historical German loans from 1973-1975: a small, old, non-UK sample used here as a stand-in for bank data.

### Risks

- Uses age (protected characteristic under the Equality Act 2010); personal status and sex (sex is a protected characteristic); foreign-worker status (potential proxy for nationality / race) as a direct input. Requires a documented justification and fairness testing before use in customer decisions.
- Documentation last reviewed 2022-11 (4.0 years ago): out of date.
- Explainability risk: adverse-action reasons are hard to give to declined customers.

---
_Facts are extracted deterministically. Narrative text must be checked by a model owner before this card is relied on. Producing this card does not by itself demonstrate compliance with PRA SS1/23._
