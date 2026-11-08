# RevPulse BI â€” Completion Implementation Plan

Prepared 6 November 2026. This backlog follows an inspection of the current README and executable CLI. It supplements IMPLEMENTATION_PLAN.md and defines the work remaining; it does not claim that work is complete.

## Original implementation and correction priorities (historical baseline)

The repository currently generates fixed-price monthly subscriptions, invoice/payment/activity CSVs, exact-row deduplication, a SQLite database, monthly MRR/collections, and two assertions. This is a prototype rather than Release 1.

Specific gaps found in the code:

- Duplicate detection compares entire rows, so conflicting records with the same business ID survive.
- Database tables have no primary keys, foreign keys, or check constraints.
- Every build drops tables; no validated staging-to-reporting transaction exists.
- Active accounts are counted as subscription rows, which breaks with multiple subscriptions.
- Month indexes replace real lifecycle dates; invoice due dates and payment event dates are absent.
- Generation overwrites raw exports; runs have no immutable source manifest.
- CSV writing assumes at least one row and fails on empty outputs.
- Checks use Python assertions, which can be disabled; failures need explicit exceptions and a nonzero exit code.
- The current random usage and churn generation does not support a convincing prediction exercise.
- There are no tests, PostgreSQL migrations, analytical SQL files, audit workbook, Power BI report, or trained model.

## Delivery sequence

Complete work packages in order. Each package ends with saved evidence and an updated status table. Do not mark a package complete merely because its files exist.

### WP1 â€” Runtime and contracts

Deliver:

- Refactor CLI into configuration, generation, ingestion, cleaning, validation, database, marts, export, and model modules.
- Add configurable workspace/output paths, seed, reporting cutoff, date range, and account count.
- Add commands `generate`, `ingest`, `validate`, `build-marts`, `export`, `train`, `score`, and `all`.
- Make empty datasets valid, report clear errors, and create required directories automatically.
- Add `.env.example`, a dependency lock, data dictionary, metric dictionary, and source contracts.
- Archive the prototype output under a run identifier before producing the new schema.

Gate: commands work outside the repository directory; empty exports keep their headers; invalid configuration fails before outputs are changed.

### WP2 â€” Complete source model and generator

Replace prototype source tables with customers, subscription periods, invoices, payment events, and monthly activity, using the schemas in the original plan.

Deliver:

- Real dates, company names, signup dates, contract intervals, recurring discounts, invoice components, due dates, payment statuses, and availability timestamps.
- Annual and monthly plans, upgrades/downgrades, concurrent subscriptions, churn/reactivation, partial payments, early/late payments, and refunds.
- Immutable run folders with configuration, source hashes, seed, and generation version.
- Separate clean truth and defect manifest, excluded from operational transformations and model features.
- Controlled missing values, conflicting IDs, exact duplicates, invalid foreign keys, ambiguous dates, invalid usage, and invoice discrepancies.
- A small fixture covering each edge case with independently calculated expected answers.

Gate: identical configuration yields identical business records; clean truth obeys financial identities; each defect has a known expected disposition.

### WP3 â€” Quality pipeline and PostgreSQL

Deliver:

- Versioned PostgreSQL migrations with keys, foreign keys, monetary constraints, and non-overlapping subscription periods.
- Local PostgreSQL setup instructions and optional Docker Compose configuration.
- Raw staging with source lineage; validated tables loaded transactionally.
- Exact-duplicate removal; explicit conflict quarantine; documented handling of legitimate event updates.
- Source-format date parsing, controlled string mappings, and authoritative recovery of missing financial components.
- Quarantine records with original values and reason codes; no financial median imputation or silent clipping.
- Run-level row reconciliation and financial coverage report.

Gate: run integration checks against an actual PostgreSQL instance. A failed validation leaves the previously published reporting dataset intact. Reruns are idempotent. Unresolved key conflicts cannot enter reporting tables.

### WP4 â€” Financial marts and six SQL analyses

Deliver customer-month, revenue-month, invoice-aging, and billing-exception marts, plus date/customer dimensions.

Implement:

1. Customer 360 with facts aggregated independently before joins.
2. Region/channel MRR, ARPA, invoicing, collections, and explicitly defined payment failure rate.
3. Monthly MRR, complete month spine, MoM growth, and a reconciled movement bridge.
4. Top five customers per region with deterministic tie handling.
5. Historical aging buckets based on payments known at the reporting cutoff.
6. First-paid-activation retention cohorts with unobserved periods left unavailable.

Gate: fixture results match hand calculations; adding activity records cannot multiply invoice totals; multiple subscriptions count as one active account; annual INR 12,000 becomes INR 1,000 MRR; all bridge components reconcile.

### WP5 â€” Excel audit deliverable

Deliver `excel/RevPulse_Validation_Audit.xlsx` with:

- Source/customer/invoice sheets and an enriched master table.
- XLOOKUP formulas, plan dropdowns, numeric validations, overdue conditional formatting.
- Genuine PivotTables for invoiced amounts by region and payment delays by plan.
- Reconciliation sheet comparing independent Excel results to SQL exports for an identical cutoff and scope.
- Refresh instructions, units, data coverage, and source timestamps.

Gate: open and recalculate the workbook; inspect layout and formula results; verify PivotTables and totals. A static summary sheet does not satisfy the PivotTable requirement.

### WP6 â€” Power BI analytics release

Deliver `dashboard/RevPulse_BI_Dashboard.pbix`, documented measures, a refresh guide, and screenshots.

- Revenue page: MRR, NRR, active accounts, customer churn, monthly trend, movement waterfall, region/channel comparison.
- Action page: overdue balance, aging distribution, billing exceptions, and account investigation table.
- Audit view/tooltips: refresh time, reporting cutoff, exclusions, definitions, and quality status.
- Explicit snapshot measures so selecting several months does not sum MRR balances.
- One-to-many dimension relationships; avoid joins between incompatible fact grains.

Gate: open and refresh in Power BI Desktop; reconcile default, region, plan, and date-filter results against SQL. Save readable screenshots. A CSV or HTML substitute does not complete the native Power BI requirement.

Release 1 is complete only after WP1â€“WP6 pass.

### WP7 â€” Explainable anomaly investigation

Deliver business-rule exceptions and grouped IQR/support-baseline flags with record IDs, reasons, observed/expected values, severity, and review status.

- Compare charges only within compatible contract/billing groups.
- Handle sparse groups explicitly.
- Evaluate injected-error detection against the held-out defect manifest.
- Report false positives and misses by rule.
- Preserve statistically unusual but valid transactions in financial reporting.

Gate: a valid large enterprise invoice is not automatically labeled erroneous; detected known defects can be traced to the source record and rule.

### WP8 â€” Point-in-time churn modeling

Deliver feature generation, training/evaluation, saved model/preprocessing, score exports, evaluation notebook, and model card.

- Score paying accounts active at a documented cutoff for next-calendar-month loss of their final subscription.
- Derive labels from subscription history, including a documented reactivation policy.
- Features use only data available by scoring time; exclude customer IDs and future cancellation fields.
- Exclude snapshots whose next-month outcome is not yet fully observed.
- Use chronological train/validation/test periods with label-availability boundaries.
- Compare prevalence and operational baselines, Logistic Regression, and Random Forest.
- Select thresholds on validation data; report held-out precision, recall, F1, PR-AUC, calibration, and precision/recall at operational capacity K.
- Export customer ID, scoring date, model version, probability, risk band, MRR, and supporting indicators.

Gate: modifying future events cannot change historical features. Model inputs do not read generator truth. Scores are unique and bounded. Report results honestly if a model fails to beat the baseline; no invented accuracy target.

### WP9 â€” Integration and final delivery

- Add current risk scores and high-risk MRR to the Power BI action page with score-date visibility.
- Produce an executive brief with three to five findings calculated from the final outputs.
- Provide data provenance, limitations, architecture diagram, screenshots, and reproducible commands in README.
- Update the original implementation checklist with evidence for completed requirements.
- Perform a fresh-environment run, refresh Excel and Power BI, and archive verification results.

Gate: all artifacts open, refresh, and reproduce documented results; README contains no obsolete pending list or unsupported impact claims.

## Required verification suite

| Area | Minimum evidence |
|---|---|
| Data quality | Every input row has one disposition; no unresolved keys enter validated tables |
| Money | Integer paise or decimal arithmetic; component totals and transformations reconcile |
| Historical accuracy | Payments after the cutoff do not change historical balances |
| Subscription lifecycle | Concurrent subscriptions, annual normalization, upgrades, cancellation, and reactivation fixtures |
| SQL | Six query results verified on fixtures and PostgreSQL |
| Pipeline | Unchanged inputs yield unchanged business results; failed publication preserves prior outputs |
| Excel | Recalculated formulas, functioning PivotTables, matching totals, visual inspection |
| Power BI | Successful refresh, correct filtering, snapshot behavior, readable screenshots |
| Churn | Feature availability, observed labels, chronological evaluation, future-event invariance |
| Reproducibility | Clean installation and documented end-to-end execution |

## Execution policy

Inspect PostgreSQL, Excel, and Power BI availability early. If an application is unavailable, complete all independent implementation work and record the precise unverified artifact or step. Never mark native application validation complete using a substitute format.

No further approval is needed for ordinary local implementation within the already authorized project. Publishing to GitHub, sending messages, and deploying external services are outside this completion backlog unless separately requested.

Suggested effort: 80â€“120 focused hours, adjusted after environment inspection. This estimate covers implementation and validation, not just file generation.

## Completion tracker

Updated after implementation: see reports/DELIVERY_REPORT.md and reports/implementation_status.json for requirement-level evidence. Native Excel and Power BI validation is deferred by user agreement.

| Package | Status | Evidence required |
|---|---|---|
| WP1 Runtime/contracts | Verified | CLI checks and contract documents |
| WP2 Source generation | Verified | Fixture results and defect manifest |
| WP3 PostgreSQL/quality | Verified | Integration report and audit outputs |
| WP4 SQL/marts | Verified | Query checks and financial reconciliation |
| WP5 Excel | File verified; native refresh deferred | Recalculated workbook and audit evidence |
| WP6 Power BI | Source/schema verified; native acceptance deferred | Refresh/filter checks and screenshots |
| WP7 Anomalies | Verified | Rule evaluation report |
| WP8 Churn | Verified | Temporal tests, model card, held-out evaluation |
| WP9 Final delivery | Code/docs/reproduction verified; native acceptance deferred | Fresh-environment verification report |
