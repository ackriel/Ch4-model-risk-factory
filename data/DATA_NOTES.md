# Data notes

**Source:** South German Credit (UPDATE), UCI Machine Learning Repository (dataset 573), DOI 10.24432/C5QG88, licence CC BY 4.0. It's the corrected version of the widely used Statlog German Credit data. The original coding errors are documented in Grömping (2019). The English labels come from the R package `liver` (dataset `credit`), exported to `south_german_credit.csv`.

| Item | Value |
|---|---|
| Records | 1,000 loans (700 good, 300 bad). Bad loans were heavily oversampled by the original collectors |
| Period | 1973-1975, a bank in southern Germany |
| Inputs | 20: 3 numeric (`duration`, `amount`, `age`), 17 categorical |
| Target | `credit_risk` ("good risk"/"bad risk") → recoded to **`default_flag` = 1 for bad risk** |
| Split | Stratified 70/30, seed 42 → `train.csv` (700 rows), `test.csv` (300 rows), `customer_id` added |

## Demographic fields (checked before any fairness work)
- **`age`** (years): available. Grouped as *under 25* / *25 and over*.
- **`foreign_worker`**: available, but only 37 of 1,000 are "yes" (9 in the test set), so results for that group are flagged as low-confidence.
- **`personal_status_sex`**: combines sex and marital status. The documentation states that *female non-single* and *male single* share one code, so **sex cannot be fully recovered**. Results are reported by this field with that caveat, and are not presented as a sex fairness test.

## Limitations
The data is small, about 50 years old, not from the UK, and oversampled for defaults, so the observed default rate (30%) is far above any real retail portfolio. It's a public stand-in for demonstrating the method; none of the results describe a real bank.
