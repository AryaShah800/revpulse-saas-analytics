# Executive summary

Synthetic reporting cutoff: **2025-12-31**. All amounts are INR. **All data is simulated** (seed 42, 1,000 accounts, 36 months), so these findings describe the generated dataset, not a real business.

**Snapshot:** month-end MRR is **₹3,622,900.00** across **651 active accounts**, down 3.41% on the preceding month and 16.71% on December 2024 (₹4,349,900.00). Latest-month NRR is 95.88% and customer churn is 1.82%.

## Recommendations

Each recommendation is tied to one of the six SQL analyses in `sql/analytical_queries.sql`.

1. **Work the oldest unpaid invoices first** (`invoice_aging`). Of ₹9,523,419.20 outstanding across 1,119 unpaid invoices, the 61+ day bucket holds 998 invoices worth ₹7,658,901.20 (80.4%). Review disputed and returned payments before outreach. Metric: outstanding balance in the 61+ bucket.
2. **Target collections at Referral-sourced accounts** (`regional_channel_performance`). Referral is the highest-value channel (ARPA ₹6,664, 29.2% of MRR) but collects worst: 92.49% of invoiced value collected vs 94.17% overall. The two weakest region/channel segments are North Organic (91.25%) and West Referral (91.27%). Metric: collection rate by segment. This is descriptive, not tested, and the all-time invoiced total includes recent invoices that may not yet be due.
3. **Put retention ahead of expansion** (`monthly_growth`). Over the last 12 months expansion (₹2,095,700) and contraction (₹2,086,200) almost cancel (net +₹9,500), so the MRR decline comes from churned MRR (₹1,092,700) that reactivation (₹356,200) only partly recovers. Metric: churned MRR per month. **Caveat:** the simulation signs up no new accounts after month 18, so new MRR is zero from July 2024 onward. The size of the decline is partly a property of the simulation and says nothing about acquisition.
4. **Focus retention effort on the first six months** (`cohort_retention`). Across 18 signup cohorts (1,000 accounts), 82.8% are still active at month 12. Of the 17.2 points lost, 11.5 are lost by month 6. Metric: month-6 retention.
5. **Use the churn-risk list as a triage aid, not a strategy** (`customer_360`). 11 accounts exceed the validation-selected threshold, representing ₹60,800.00 of MRR (1.68%). The selected model's held-out PR-AUC is 0.139 against a churn prevalence of 0.024, and its recall is 14.3%, so it misses most churn. Review usage decline, tickets and payment context (from `customer_360`) before acting on any account.

Also checked: the top five accounts in each region (20 accounts) account for 9.07% of invoiced value, so there is no single-account concentration risk in `top_accounts`.

## Validation

Invoice totals, net collections, MRR, distinct accounts, balances and the MRR bridge reconcile. The Excel annual invoicing/delay audit has zero differences against matching SQL totals. Quarantined rows and transformations are itemized in `docs/DATA_CLEANING_LOG.md`.

## Status

Native Excel refresh/editing and Power BI refresh/render/save-to-PBIX have not been done. The XLSX structure/formulas/cached totals and PBIP JSON definitions have been checked independently, but there is no rendered dashboard or `.pbix` yet.
