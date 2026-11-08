# Executive summary

Synthetic reporting cutoff: **2025-12-31**. All amounts below are INR. These findings describe the generated dataset.

1. Month-end MRR is **₹3,622,900.00** across **651 active accounts**, a **-3.41%** change from the preceding month. Review the SQL MRR bridge to separate expansion, contraction, acquisition and churn.
2. Latest-month NRR is **95.88%** and customer churn is **1.82%**. Compare cohort retention before interpreting acquisition-led growth as retention improvement.
3. Overdue balances total **₹9,523,419.20** at cutoff. Prioritize the oldest balances and review disputed/returned payments before collection outreach.
4. **11 accounts** exceed the validation-selected churn threshold, representing **₹60,800.00** of MRR exposure. This is not a prediction that the whole amount will be lost. Review usage decline and payment/support context before acting.
5. The selected churn model achieves held-out PR-AUC **0.139** versus a churn prevalence of **0.024**. Recall at its selected threshold is **14.3%**, so the model misses substantial churn and must not be treated as a complete retention strategy.

Validation: invoice totals, net collections, MRR, distinct accounts, balances and the MRR bridge reconcile. The Excel annual invoicing/delay audit has zero differences against matching SQL totals. Quarantined rows and transformations are itemized in DATA_CLEANING_LOG.md.

Native Excel refresh/editing and Power BI refresh/render/save-to-PBIX are deferred at the user's request. The XLSX structure/formulas/cached totals and PBIP JSON definitions have been checked independently.
