# Model card: Early-Warning Default Decision Tree (CR-EW-002)

> **DRAFT - requires human review** - generated 2026-11-13T11:47:33Z by the Document agent.

## Facts (extracted from source code)

| Field | Value |
|---|---|
| Owner | Collections Strategy |
| Language | Python |
| Methodology detected | Decision tree (scikit-learn) |
| Target variable | default_flag |
| Target definition | 1 = bad risk (credit contract not complied with), 0 = good risk |
| Data source | data/train.csv and data/test.csv via core.data.load_split() |
| Risk tier | Tier 2 - moderate |
| Executable in factory | True |
| Source file | legacy_models/early_warning_tree.py |

### Input variables

| Variable | Type | Protected / proxy |
|---|---|---|
| status | categorical |  |
| duration | numeric |  |
| credit_history | categorical |  |
| amount | numeric |  |
| savings | categorical |  |
| employment_duration | categorical |  |
| age | numeric | YES |
| property | categorical |  |
| housing | categorical |  |

### Settings found in code

- `max_depth` = 4
- `min_samples_leaf` = 25
- `class_weight` = balanced
- `random_state` = 42

## Narrative (source: rule_based)

### Purpose

Flag existing borrowers at elevated risk of default for early outreach. Business use: Prioritising collections contact lists.

### Methodology

Single classification tree (CART) that splits applicants into a small number of leaves; the PD is the (re-weighted) default share in the leaf.

### Assumptions

- Risk is constant within each leaf.
- The tree structure found on the development sample is stable.

### Limitations

- Produces a handful of distinct scores, so ranking within a leaf is impossible.
- Class weighting ('balanced') inflates PDs: scores are rankings, not calibrated probabilities.
- Developed on 1,000 historical German loans from 1973-1975: a small, old, non-UK sample used here as a stand-in for bank data.

### Risks

- Uses age (protected characteristic under the Equality Act 2010) as a direct input. Requires a documented justification and fairness testing before use in customer decisions.
- Documentation last reviewed 2021-07 (5.4 years ago): out of date.
- Coarse scores may produce cliff-edge decisions for similar customers.

---
_Facts are extracted deterministically. Narrative text must be checked by a model owner before this card is relied on. Producing this card does not by itself demonstrate compliance with PRA SS1/23._
