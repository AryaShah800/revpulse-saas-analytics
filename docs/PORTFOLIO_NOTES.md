# RevPulse BI | SaaS Revenue and Customer Retention Analytics

**Repository** · https://github.com/AryaShah800/revpulse-saas-analytics
**Stack** · Python, pandas, PostgreSQL, SQL, Excel, Power BI, scikit-learn, pytest

## Resume entry

Pick two or three bullets that match the role.

- Built a reproducible PostgreSQL and Python analytics pipeline for 1,000 synthetic B2B SaaS accounts, with source validation, record quarantine, and six SQL analyses covering recurring revenue, collections, and retention.
- Reconciled invoice and cash totals, month-end MRR, and account counts across SQL and an Excel audit workbook with two PivotTables. Built a Power BI project for revenue trends, overdue balances, and account risk.
- Evaluated Logistic Regression and Random Forest on chronological churn splits using features available at each scoring date. The selected model achieved 0.139 held-out average precision against a 0.024 churn prevalence baseline.

## Thirty-second walkthrough

RevPulse BI answers three questions for a SaaS business. How is recurring revenue changing, which invoices need attention, and which accounts might churn next month? I generated a synthetic dataset, cleaned it with auditable rules, and built PostgreSQL tables and reporting marts. I reconciled the financial results in Excel, created a Power BI report project, and evaluated churn models on later months than the ones used for training.

## Architecture and decisions

- **Source data.** Five tables cover customers, subscription periods, invoices, payment events, and monthly activity. The seeded generator includes annual billing, upgrades, cancellations, reactivation, partial payments, and refunds.
- **Quality controls.** Source hashes detect changed inputs. Exact duplicates are removed, conflicting records and invalid references are quarantined, and invoice totals are recovered only when authoritative components are available. Source lineage and rejection reasons remain available for audit.
- **Financial modeling.** MRR uses active subscription terms at month-end and normalizes annual charges. Invoices and cash collections use their own event dates. Facts are aggregated before joining to prevent duplicate totals. Aging excludes payments after the cutoff.
- **Reporting.** Six SQL analyses cover customer profiles, regional and channel performance, monthly growth, top accounts, invoice aging, and cohort retention. The Excel workbook has lookup formulas, validation, conditional formatting, two PivotTables, and SQL controls. The Power BI project has revenue, account actions, and audit pages.
- **Advanced analytics.** Contract rules identify billing discrepancies. IQR and support spikes provide investigation leads. Churn features use activity and payments available at the score cutoff. Training, threshold selection, and testing use separate chronological periods.

## Demonstrated results

| Measure | Result |
|---|---:|
| Synthetic customer accounts | 1,000 |
| Observation window | 36 months |
| December 2025 month-end MRR | ₹36,22,900 |
| December 2025 active accounts | 651 |
| December 2025 net revenue retention | 95.88% |
| December 2025 customer churn | 1.82% |
| Held-out average precision | 0.139 |
| Held-out churn prevalence | 2.4% |
| Recall at the selected threshold | 14.3% |
| Automated tests | 12 passed |

These are synthetic results. The model's low recall limits its use to prioritizing a review queue. The portfolio includes a schema-validated Power BI project and a verified Excel workbook file. Native application refresh checks and final PBIX export were deferred.

## Interview questions

**How did you prevent leakage?** I filtered features by observation and availability dates, derived the label from the following month, excluded rows without complete outcomes, and fit preprocessing on the training split.

**How did you verify the money?** I compared the SQL outputs with hand-calculated fixtures and independent totals. Cases included annual billing, concurrent subscriptions, refunds, partial payment, and post-cutoff payment. The MRR bridge ties opening MRR and changes to closing MRR.

**Why use average precision?** Churn was uncommon, so I compared ranking quality against the observed prevalence and reported recall separately. I chose the threshold using validation data and measured performance on a later holdout.

**What would you improve with real data?** Check billing and event contracts with source owners, monitor data drift and missingness, and evaluate whether the top-ranked accounts are useful at the retention team's actual review capacity.

For a demo, start with the executive findings, show the SQL reconciliation and Excel audit, then walk through the churn evaluation notebook.
