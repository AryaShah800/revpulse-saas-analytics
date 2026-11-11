# Delivery verification

Automated tests: **12 passed**. Independent-environment reproduction passed.

**Portfolio delivery complete. Native Excel and Power BI acceptance remains deferred.**

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| R01 | Configurable CLI, empty exports, explicit errors | verified | reports/test_results.xml |
| R02 | Pinned dependencies and independent environment reproduction | verified | reports/reproducibility.json, reports/fresh_environment_tests.xml |
| R03 | Dated five-table generator with annual/monthly contracts and lifecycle changes | verified | reports/test_results.xml, docs/source_contracts.md |
| R04 | Isolated truth, defect manifest and immutable source hashes | verified | reports/test_results.xml, reports/defect_evaluation.json |
| R05 | Hand-calculated ten-account financial fixture | verified | reports/test_results.xml |
| R06 | Strict parsing, missing-amount recovery and quarantine | verified | reports/test_results.xml, docs/DATA_CLEANING_LOG.md |
| R07 | Exact duplicates, conflicting keys, overlapping periods and parent integrity | verified | reports/test_results.xml |
| R08 | Lineage, dispositions, row reconciliation and exclusion disclosure | verified | reports/quality.json, docs/DATA_CLEANING_LOG.md |
| R09 | Actual PostgreSQL integration, constraints and versioned schemas | verified | reports/test_results.xml, reports/reconciliation.json |
| R10 | Atomic published core output pointer and failure preservation | verified | reports/test_results.xml |
| R11 | MRR, annual normalization, distinct accounts and revenue bridge | verified | reports/test_results.xml, reports/reconciliation.json |
| R12 | Historical balances, early/late payments, refunds and nonoverlapping aging | verified | reports/test_results.xml |
| R13 | Six analytical SQL queries, preaggregation, cohorts and unobserved periods | verified | reports/test_results.xml |
| R14 | Excel XLOOKUP, validations, conditional formatting and SQL reconciliation | verified | reports/workbook/verification.json, reports/workbook/recalculation_checks.json |
| R15 | Two native PivotTables with caches and source references | verified | reports/workbook/verification.json |
| R16 | Workbook visual inspection across all six sheets | verified | reports/workbook/Overview.png, reports/workbook/Cleaned_Master.png, reports/workbook/Customers.png, reports/workbook/Payments.png, reports/workbook/Audit_Pivots.png, reports/workbook/Reconciliation.png |
| R17 | Native Excel open, input-change recalculation and pivot refresh | deferred_by_user | README.md (Limits) |
| R18 | Power BI project with two main pages and audit view | implemented_schema_verified | reports/powerbi_schema_validation.json |
| R19 | Semantic model relationships, snapshot measures and risk integration | implemented_native_unverified | reports/powerbi_schema_validation.json |
| R20 | Native Power BI refresh, visual/filter inspection, PBIX and screenshots | deferred_by_user | README.md (Limits) |
| R21 | Contract billing exceptions, peer IQR, support spikes and defect evaluation | verified | reports/defect_evaluation.json |
| R22 | EDA and single-snapshot exploratory hypothesis with uncertainty | verified | reports/hypothesis_result.json |
| R23 | Point-in-time features and future-observation invariance | verified | reports/test_results.xml |
| R24 | Observed churn labels and chronological train/validation/test splits | verified | reports/test_results.xml, reports/model_evaluation.json |
| R25 | Logistic/forest comparison, baselines, calibration and campaign-capacity metrics | verified | reports/model_evaluation.json |
| R26 | Saved model, score export and model card | verified | reports/reproducibility.json |
| R27 | Executive findings, dictionaries, cleaning log and runbook | verified | reports/reconciliation.json, reports/model_evaluation.json |
