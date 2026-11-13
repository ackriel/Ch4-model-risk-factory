# Model card: Retail Unsecured Loan Application Scorecard (PD) (CR-PD-001)

> **DRAFT - requires human review** - generated 2026-11-13T11:47:33Z by the Document agent.

## Facts (extracted from source code)

| Field | Value |
|---|---|
| Owner | Retail Credit Risk Analytics |
| Language | R |
| Methodology detected | Logistic regression (GLM, binomial/logit) |
| Target variable | default_flag |
| Target definition | 1 = bad risk (credit contract not complied with), 0 = good risk |
| Data source | data/train.csv, data/test.csv |
| Risk tier | Tier 1 - material (customer decisions / financial reporting) |
| Executable in factory | True |
| Source file | legacy_models/scorecard_logit.R |

### Input variables

| Variable | Type | Protected / proxy |
|---|---|---|
| duration | numeric |  |
| amount | numeric |  |
| age | numeric | YES |
| status | categorical |  |
| credit_history | categorical |  |
| savings | categorical |  |

### Settings found in code

- `family` = binomial(link = "logit")

## Narrative (source: rule_based)

### Purpose

Estimate probability of default (PD) for new personal-loan applications. Business use: Credit approval decisions and risk-based pricing.

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
- Documentation last reviewed 2019-03 (7.7 years ago): out of date.

---
_Facts are extracted deterministically. Narrative text must be checked by a model owner before this card is relied on. Producing this card does not by itself demonstrate compliance with PRA SS1/23._
