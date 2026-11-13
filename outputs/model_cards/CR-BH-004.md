# Model card: Behavioural Credit Score (Existing Customers) (CR-BH-004)

> **DRAFT - requires human review** - generated 2026-11-13T14:46:05Z by the Document agent.

## Facts (extracted from source code)

| Field | Value |
|---|---|
| Owner | Retail Credit Risk Analytics |
| Language | SAS |
| Methodology detected | Logistic regression (SAS PROC LOGISTIC) |
| Target variable | default_flag |
| Target definition | 1 = bad risk (credit contract not complied with), 0 = good risk |
| Data source | crd.monthly_accounts, work.beh_base (production SAS library, not available) |
| Risk tier | Tier 1 - material (customer decisions / financial reporting) |
| Executable in factory | False |
| Source file | legacy_models/behavioural_score.sas |

### Input variables

| Variable | Type | Protected / proxy |
|---|---|---|
| util_band | categorical |  |
| max_arrears_6m | categorical |  |
| months_on_book | categorical |  |
| age | numeric | YES |

### Settings found in code

- `variable_selection` = stepwise
- `slentry` = 0.05
- `slstay` = 0.05

## Narrative (source: rule_based)

### Purpose

Monthly re-scoring of existing borrowers' probability of default. Business use: Limit management and provisioning inputs.

### Methodology

Binary logistic regression estimating the probability of default (PD) as a logit-linear function of the inputs. Categorical inputs enter as dummy variables against a reference level.

### Assumptions

- Log-odds of default are linear in each numeric input (no transformation or binning detected).
- Observations are independent; no account-level or time clustering is modelled.
- Effects are additive: no interaction terms are specified.
- The development sample is representative of the population scored today.

### Limitations

- Cannot capture non-linear effects or interactions unless explicitly engineered.
- Developed on 1,000 historical German loans from 1973-1975: a small, old, non-UK sample used here as a stand-in for bank data.

### Risks

- Uses age (protected characteristic under the Equality Act 2010) as a direct input. Requires a documented justification and fairness testing before use in customer decisions.
- Documentation last reviewed 2017-05 (9.5 years ago): out of date.
- Stepwise variable selection is unstable and inflates apparent significance.
- Depends on a SAS licence and a production library not available for independent re-execution: the model cannot be validated as-is.
- Model could not be executed in the factory, so no performance evidence exists.

---
_Facts are extracted deterministically. Narrative text must be checked by a model owner before this card is relied on. Producing this card does not by itself demonstrate compliance with PRA SS1/23._
