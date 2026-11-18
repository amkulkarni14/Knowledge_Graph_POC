# Sample CSV files

Invented data for trying Stage 2 → **Upload CSV files**.

| Folder | Files | What it shows |
|---|---|---|
| `customer360/` | customers, banks, accounts, loans, payments, credit_score, credit_enquiry | A clean set. Loaded together: 54 nodes and 64 edges, in any order. `Cust ID`-style headers become `cust_id`; `credit_score` has a composite key (`cust_id` + `score_date`); `loans.csv` has amounts like `4,500,000`; payment `P9011` has no account. |
| `customer360_messy/` | customers, loans | Problems real extracts have: repeated rows, `₹ 45,00,000`, `8.5%`, day-first dates. It is **refused on purpose** (the identifiers repeat, so no row can be told apart); Stage 2 lists each reason. Fix the file and it loads. |

Stage 2 has a button for the first set; from a terminal:

```
python scripts/run_pipeline.py --csv-dir data/samples/customer360
python scripts/run_pipeline.py --csv-dir data/samples/customer360_messy     # exits with the reasons
```
