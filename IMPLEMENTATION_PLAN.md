# RevPulse BI â€” Implementation Plan

Status: File implementation delivered; native Excel/Power BI acceptance deferred by user. See reports/DELIVERY_REPORT.md for current verification evidence.
Prepared: 6 November 2026
Purpose: Build a reproducible data analyst portfolio project demonstrating reliable SaaS revenue reporting, billing quality checks, and customer retention analysis.

## 1. Scope and delivery strategy

Deliver the project in two releases:

- **Release 1 â€” Analytics MVP:** synthetic source data, validated pipeline, PostgreSQL marts, six analytical SQL queries, Excel reconciliation workbook, and two Power BI pages.
- **Release 2 â€” Advanced analytics:** statistical anomaly investigation, point-in-time churn features, evaluated prediction models, and dashboard risk integration.

Planning estimate: six weeks at approximately 15â€“20 focused hours per week. This is an estimate, not a deadline; progress depends on the acceptance gates below.

Assumptions:

- One developer; local development on Windows.
- INR-only reporting; no currency conversion.
- Synthetic B2B SaaS accounts across Indian regions; no personal or confidential customer data.
- Monthly and annual fixed-price subscriptions, with recurring discounts and plan changes. Usage-based pricing is out of scope.
- Invoice tax fields are simulated; this project does not implement tax compliance or accounting revenue recognition.
- No outreach automation, live payment integration, deployment platform, or real-time pipeline in the initial scope.

## 2. Technology and development setup

| Area | Choice | Implementation decision |
|---|---|---|
| Processing | Python, pandas, NumPy | Reusable modules for transformations; notebooks for explanation |
| Database | PostgreSQL | Versioned schema and SQL migrations; fixed-precision monetary columns |
| Validation | Python assertions and pytest | Focus on financial identities, keys, temporal logic, and regressions |
| Analysis | matplotlib/seaborn, scikit-learn | Baselines before more complex models |
| Audit | Microsoft Excel | XLOOKUP, validation rules, PivotTables, reconciliation sheet |
| Dashboard | Power BI Desktop | Semantic model, explicit measures, two report pages |
| Reproducibility | Git, dependency lock, configuration file | Seeded data generation and explicit reporting cutoff |

Setup tasks:

- [ ] Create a Python environment and pin a compatible dependency set when implementation starts.
- [ ] Configure PostgreSQL locally; optionally provide Docker Compose for reproducibility.
- [ ] Add `.env.example`; keep credentials and local environment files out of Git.
- [ ] Define configuration for random seed, reporting cutoff, source paths, database connection, and quality thresholds.
- [ ] Confirm Excel and Power BI Desktop availability before their delivery phases.
- [ ] Establish CLI commands: `generate`, `ingest`, `validate`, `build-marts`, `export`, `train`, and `score`.

## 3. Repository structure

```text
revpulse-saas-analytics/
â”œâ”€â”€ IMPLEMENTATION_PLAN.md
â”œâ”€â”€ README.md
â”œâ”€â”€ pyproject.toml
â”œâ”€â”€ .env.example
â”œâ”€â”€ config/project.yml
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/                     # Immutable generated source exports
â”‚   â”œâ”€â”€ reference/               # Generator truth and defect manifest; never model inputs
â”‚   â”œâ”€â”€ processed/
â”‚   â””â”€â”€ quarantine/
â”œâ”€â”€ src/revpulse/
â”‚   â”œâ”€â”€ cli.py
â”‚   â”œâ”€â”€ generate.py
â”‚   â”œâ”€â”€ ingest.py
â”‚   â”œâ”€â”€ clean.py
â”‚   â”œâ”€â”€ validate.py
â”‚   â”œâ”€â”€ reconcile.py
â”‚   â”œâ”€â”€ anomalies.py
â”‚   â”œâ”€â”€ features.py
â”‚   â”œâ”€â”€ train.py
â”‚   â””â”€â”€ score.py
â”œâ”€â”€ sql/
â”‚   â”œâ”€â”€ migrations/
â”‚   â”œâ”€â”€ marts/
â”‚   â””â”€â”€ analytical_queries.sql
â”œâ”€â”€ notebooks/
â”‚   â”œâ”€â”€ 01_data_quality_and_eda.ipynb
â”‚   â””â”€â”€ 02_churn_evaluation.ipynb
â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ fixtures/
â”‚   â”œâ”€â”€ test_financial_reconciliation.py
â”‚   â”œâ”€â”€ test_temporal_features.py
â”‚   â””â”€â”€ test_pipeline_integrity.py
â”œâ”€â”€ excel/RevPulse_Validation_Audit.xlsx
â”œâ”€â”€ dashboard/
â”‚   â”œâ”€â”€ RevPulse_BI_Dashboard.pbix
â”‚   â”œâ”€â”€ measures.md
â”‚   â””â”€â”€ screenshots/
â”œâ”€â”€ reports/
â”‚   â”œâ”€â”€ data_quality/
â”‚   â”œâ”€â”€ model_evaluation/
â”‚   â””â”€â”€ executive_summary.md
â””â”€â”€ docs/
    â”œâ”€â”€ data_dictionary.md
    â”œâ”€â”€ metric_dictionary.md
    â”œâ”€â”€ source_contracts.md
    â”œâ”€â”€ DATA_CLEANING_LOG.md
    â”œâ”€â”€ model_card.md
    â””â”€â”€ runbook.md
```

Large generated files and model binaries should be ignored by default. Commit small synthetic examples and instructions to regenerate full artifacts.

## 4. Phase 1 â€” Business definitions and data design

Target: Week 1. Dependency: none.

### Tasks

- [ ] Define reporting dates in the business timezone and store event timestamps consistently.
- [ ] Document entity relationships, field types, nullability, keys, and source date formats.
- [ ] Use half-open effective intervals `[effective_from, effective_to)` for subscription history; prohibit overlapping periods for the same subscription.
- [ ] Distinguish customer signup, first paid activation, subscription cancellation, and account churn.
- [ ] Define the exact extraction cutoff and when each source field becomes available.
- [ ] Write metric definitions and small manually calculated examples before building dashboards.

### Core tables

| Table | Grain | Required information |
|---|---|---|
| `customers` | One account | Customer ID, company name, signup date, region, acquisition channel |
| `subscription_periods` | One interval of unchanged subscription terms | Period ID, subscription ID, customer ID, effective dates, plan, billing interval, recurring amount, recurring discount |
| `invoices` | One invoice | Invoice ID, customer/subscription IDs, issue/due dates, service dates, recurring subtotal, one-time subtotal, tax, total |
| `payment_events` | One payment/refund/reversal event | Unique event ID, invoice ID, timestamp, type, signed amount or documented sign convention, status |
| `customer_monthly_activity` | One account-month | Customer ID, month, entitled/active users, tickets opened/resolved, unresolved tickets, CSAT and response count |

Include source filename, source row identifier, ingestion timestamp, and run ID in staging/audit records. Model source availability explicitly: if month-end activity is only published later, use the last available month or move the scoring date.

### Metric decisions

- **MRR:** recurring charges active at month-end, after recurring discounts; annual charges divided by 12; exclude taxes and one-time fees. Preserve sufficient precision before rounding presentation values.
- **Cash collections:** successful payment events minus successful refunds/reversals in the reporting period.
- **ARPA:** month-end MRR divided by active paying accounts at month-end.
- **Customer churn:** opening active accounts that lose their final subscription during the month divided by opening active accounts. Document treatment of within-month reactivations separately from end-state retention.
- **NRR:** closing MRR from the opening account cohort divided by its opening MRR; new accounts excluded.
- **MoM growth:** `(current MRR - previous MRR) / previous MRR`; return undefined when previous MRR is zero.
- **Overdue balance:** outstanding invoice balance as of the cutoff, aged from due date; future payment events cannot reduce historical balances.
- **High-risk MRR:** current MRR for accounts above a validation-selected risk threshold; not a forecast of guaranteed loss.

For the MRR bridge, classify customer-level opening versus closing MRR changes into new, reactivation, expansion, contraction, churn, or unchanged. Document that intra-month churn/reactivation can appear in event metrics without being an endpoint bridge movement.

### Acceptance gate

Every metric can be calculated from the proposed fields. A worked example covering monthly billing, annual billing, upgrade, cancellation, partial payment, and refund has agreed expected outputs.

## 5. Phase 2 â€” Synthetic dataset and source controls

Target: Week 1â€“2. Dependency: Phase 1 definitions.

### Tasks

- [ ] Generate approximately 1,000 accounts over 36 months, with staggered signups and realistic relationships between subscription, invoice, and activity records.
- [ ] Include monthly/annual contracts, upgrades, downgrades, multiple subscriptions, cancellations, reactivations, early/late payments, partial payments, and refunds.
- [ ] Generate complete clean truth first, then inject controlled defects into separate source exports.
- [ ] Inject exact duplicates, conflicting duplicate IDs, missing financial values, invalid keys, inconsistent regions, ambiguous dates, and invalid activity values.
- [ ] Save a defect manifest with row IDs, original values, changed values, and expected handling.
- [ ] Include a small deterministic fixture dataset for hand-checkable correctness.
- [ ] Make churn probabilistic; do not define it as a deterministic copy of one feature or use future outcomes to generate available-at-score fields.

The truth dataset and defect manifest are evaluation references only. They must never feed production transformations or model features.

### Deliverables and acceptance gate

Seeded generator, source exports, manifest, and provenance documentation. Identical seed/configuration produces identical business records. Clean truth satisfies referential integrity and financial identities before defect injection.

## 6. Phase 3 â€” Cleaning, validation, and database loading

Target: Week 2. Dependency: source contracts and generated inputs.

### Tasks

- [ ] Load immutable raw exports into staging with lineage metadata.
- [ ] Normalize documented region/channel/plan variants using explicit mappings.
- [ ] Parse source-specific dates; quarantine ambiguous dates rather than guessing.
- [ ] Separate exact duplicate events from conflicting records and legitimate event updates.
- [ ] Recover missing financial amounts only from valid authoritative components; never use statistical imputation for reported revenue.
- [ ] Derive days overdue as `max(0, cutoff - due_date)` only for unpaid overdue balances; retain signed payment delay separately so early payment is meaningful.
- [ ] Validate active users against entitled users and investigate invalid ratios instead of clipping them.
- [ ] Enforce keys, foreign keys, non-overlapping subscription periods, valid event types, and invoice identities.
- [ ] Route unresolved records to quarantine with reason codes and impact summaries.
- [ ] Load validated tables transactionally and make reruns idempotent.
- [ ] Export a run summary and cleaning log.

### Acceptance gate

- Every input row is accounted for as accepted, superseded, duplicate, or quarantined under mutually exclusive disposition rules.
- No unresolved duplicate primary keys, orphan references, or overlapping subscription intervals reach reporting tables.
- Financial transformations have exact reconciliation or explicitly documented rounding adjustments.
- Quarantined financial records are disclosed in reporting coverage; unknown missing amounts are not falsely quantified.
- A second run on unchanged inputs produces unchanged business outputs.

## 7. Phase 4 â€” SQL marts and business analysis

Target: Week 3. Dependency: validated core tables.

### Build marts

- [ ] `mart_customer_month`: account-month spine, subscription status, MRR, usage, payment/support features.
- [ ] `mart_revenue_month`: MRR totals and mutually exclusive customer-level bridge movements.
- [ ] `mart_invoice_aging`: invoice-level outstanding amount and age at a configurable cutoff.
- [ ] `mart_billing_exceptions`: record ID, rule, observed/expected values, severity, review status.
- [ ] Add date and customer dimensions; keep fact-table grains explicit in the BI model.

### Implement six core queries

1. Customer 360: pre-aggregate billing and activity separately before joining; distinguish cumulative totals from current snapshot values.
2. Region/channel performance: show MRR, ARPA, invoiced amounts, cash collections, and a separately defined payment-attempt failure rate.
3. Monthly MRR and MoM growth: complete month spine, `LAG`, and zero-denominator handling.
4. Top five accounts per region: `ROW_NUMBER` with a deterministic tie-breaker for exactly five; optionally show `DENSE_RANK` when ties should expand the result.
5. Invoice aging: current/not due, 1â€“15, 16â€“30, 31â€“60, and 61+ days; avoid overlapping bucket boundaries.
6. Retention cohorts: first paid activation month, month 0â€“12 retention, explicit denominator, and null future periods with insufficient observation.

### Acceptance gate

Queries match the small fixtureâ€™s expected answers. MRR bridge balances to closing MRR. Customer/region/channel totals reconcile. Joining additional facts does not inflate amounts. Historical aging ignores payments made after the selected cutoff.

## 8. Phase 5 â€” Excel audit and Power BI MVP

Target: Week 4. Dependency: stable SQL marts.

### Excel workbook

- [ ] Include `Customers`, `Invoices`, `Cleaned_Master`, `Validation_Rules`, `Audit_Pivots`, and `Reconciliation` sheets.
- [ ] Use XLOOKUP to enrich invoice records with account attributes.
- [ ] Apply plan dropdowns, appropriate numeric validation, and overdue formatting.
- [ ] Build actual PivotTables for invoiced amount by region and payment delay by plan.
- [ ] Reconcile independent Excel calculations against exported SQL results using identical filters and cutoffs.
- [ ] Disclose that Excel input validation does not replace validation of imported records.

### Dashboard pages

**Page 1 â€” Revenue & Retention:** MRR, NRR, active accounts, churn, monthly trend, MRR bridge, region/channel comparisons, and plan filters.

**Page 2 â€” Collections & Account Actions:** overdue balance, aging distribution, billing exception count, exception detail, and an account review table. Before the model release, label any prioritization as rule-based; do not invent probabilities.

Add an audit/definitions view or tooltip with refresh timestamp, reporting cutoff, coverage, exclusions, and metric definitions.

### Implementation rules

- Use one-to-many dimension-to-fact relationships with deliberate filter directions.
- Do not join facts directly at incompatible grains.
- Treat MRR as a snapshot: a multi-month selection must not sum month-end balances and call the result MRR.
- Define whether each card shows latest selected month, period activity, or period-end balance.
- Distinguish current customer attributes from historical subscription attributes.

### Acceptance gate â€” Release 1

Excel opens with working formulas and PivotTables. Power BI opens and refreshes using documented local configuration. Verify default totals, one region, one plan, and a bounded date range against SQL. Inspect screenshots for readability, labels, units, and empty-filter states.

## 9. Phase 6 â€” Anomaly investigation and churn modeling

Target: Week 5. Dependency: reconciled marts and historical snapshots.

### Billing anomaly tasks

- [ ] Implement rule checks for duplicated business invoices, component-total mismatches, and contract-charge differences where timing/proration rules permit comparison.
- [ ] Apply IQR within comparable plan/billing-interval groups with minimum sample-size handling.
- [ ] Compare account support volume to its historical baseline; treat a Z-score as exploratory and disclose sparse/skewed-count limitations.
- [ ] Evaluate injected-defect detection against the manifest, reporting false positives and missed cases by rule.
- [ ] Keep anomalies in financial reporting unless a separate validity rule excludes them.

### Churn tasks

- [ ] Define eligible snapshots: paying accounts active at score time, with a complete next-month outcome window for training/evaluation.
- [ ] Label whether the account loses its final subscription during the following calendar month; document reactivation treatment and distinguish event churn from month-end inactivity.
- [ ] Build point-in-time features: recent usage and trend, tenure, plan, current MRR, past payment delays, overdue balances, support counts, and CSAT availability.
- [ ] Use chronological splits, for example months 1â€“24 training, 25â€“30 validation, and 31â€“35 test, with month 36 supplying final labels. Enforce actual label-availability cutoffs and remove boundary rows where needed.
- [ ] Allow an existing account in multiple time splits because the intended use is rescoring existing accounts; exclude account IDs from predictors. State that this does not measure generalization to entirely unseen accounts.
- [ ] Fit preprocessing only on training data in a scikit-learn pipeline.
- [ ] Compare prevalence/no-skill and rule-based baselines, Logistic Regression, and Random Forest.
- [ ] Select model/thresholds on validation data; evaluate the final test set once.
- [ ] Report PR-AUC, precision, recall, F1, confusion matrix, calibration, and precision/recall at a configurable outreach capacity K.
- [ ] Export current eligible-account scores with customer ID, score date, model version, probability, risk band, current MRR, and explanatory indicators.
- [ ] Save a model card with synthetic-data limitations, features, exclusions, cutoff policy, evaluation, and intended use.

### Acceptance gate

Feature tests prove that changing future events cannot change past features. Unobserved outcomes are not labeled retained. Scores are unique per account/scoring date and bounded between 0 and 1. Performance is reported honestly even if the complex model fails to beat the baseline. No arbitrary accuracy target or unsupported retention/revenue impact claim is required.

## 10. Phase 7 â€” Integration and portfolio delivery

Target: Week 6. Dependency: Release 1 and evaluated advanced analytics.

- [ ] Add score date, model version, risk filters, and high-risk MRR to the account-actions page.
- [ ] Show usage/payment/support indicators alongside scores without presenting them as causal explanations.
- [ ] Write an executive brief with three to five findings supported by generated results, recommended investigations, and limitations.
- [ ] Document commands, configuration, execution order, troubleshooting, and refresh steps in the runbook.
- [ ] Add schema diagram, dashboard screenshots, metric definitions, validation evidence, and synthetic-data disclosure to README.
- [ ] Run the project from a fresh environment using the documented commands.
- [ ] Check committed files for secrets, private data, machine-specific absolute paths, and unnecessary large artifacts.

### Acceptance gate â€” Release 2

A reviewer can regenerate data, build the database/marts, inspect validation results, reproduce evaluation, and open the BI/Excel deliverables. Published findings link to reproducible calculations. Documentation distinguishes demonstrated analytical capability from unproven business outcomes.

## 11. Focused verification scenarios

| Scenario | Required result |
|---|---|
| Annual recurring charge of INR 12,000 | MRR is INR 1,000 while active; invoicing and collections retain their own dates |
| Duplicate payment event ID | Counted once; duplicate recorded in audit |
| Same event ID with conflicting amounts | Quarantined or resolved by an explicit source policy, never silently selected |
| Invoice INR 1,000, payment INR 400 before cutoff | Outstanding balance INR 600 |
| Payment after historical cutoff | Does not reduce the historical outstanding balance |
| Missing amount without authoritative recovery | Excluded from financial aggregation and disclosed |
| Two invoices plus three activity records | Aggregation does not multiply invoice totals sixfold |
| One of two subscriptions cancelled | Account remains active; MRR may contract |
| Final subscription ends | Account lifecycle and churn follow the documented effective-time rule |
| Future activity or payment changes | Earlier prediction features remain unchanged |
| Prior-month MRR is zero | MoM percentage is undefined rather than infinite |
| Cohort has not reached month 12 | Month-12 retention is unavailable rather than zero |

## 12. Priority and deferral rules

**Must deliver:** definitions, source contracts, lineage, quarantine, reliable financial logic, SQL marts, reconciliation, Excel workbook, dashboard, reproducible instructions.

**Then deliver:** explainable anomaly flags, chronological churn evaluation, operational score exports, and model documentation.

**Defer:** cloud infrastructure, orchestration platforms, real-time ingestion, advanced explainability libraries, causal inference, estimated LTV, and automated customer outreach.

If time is constrained, ship Release 1 with complete validation before starting model integration. Do not sacrifice metric correctness to add another chart or algorithm.

## 13. First implementation session

1. Initialize the project skeleton and environment configuration.
2. Write the metric dictionary and five source contracts.
3. Build a small fixture with 10 accounts covering the financial and lifecycle edge cases above.
4. Calculate expected MRR, cash, overdue balances, and churn by hand.
5. Implement schema constraints and validate the fixture.
6. Only then scale the generator and begin the full pipeline.

This document specifies planned work. No dataset, dashboard, workbook, or model is represented as already implemented.
