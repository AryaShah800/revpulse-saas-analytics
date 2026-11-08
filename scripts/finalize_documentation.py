"""Generate delivery documentation from measured outputs, not invented findings."""
from pathlib import Path
import json
import shutil
import pandas as pd
from revpulse.core import current_run,CONTRACTS,json_write

ROOT=Path(__file__).resolve().parents[1];run=current_run(ROOT)
manifest=json.loads((run/'manifest.json').read_text());quality=json.loads((run/'audit/quality.json').read_text());evaluation=json.loads((run/'analytics/model_evaluation.json').read_text())
monthly=pd.read_csv(run/'marts/mart_revenue_month.csv');last=monthly.iloc[-1]
aging=pd.read_csv(run/'marts/mart_invoice_aging.csv');scores=pd.read_csv(run/'analytics/churn_predictions.csv')
def write(name,text):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.strip()+'\n',encoding='utf-8')

write('docs/metric_dictionary.md', '''# Metric dictionary

All source money is integer paise (100 paise = INR 1). SQL normalizes annual contracts using exact NUMERIC arithmetic. Presentation rounds only for display. Event dates use business dates in Asia/Calcutta; monthly activity is assumed available at that month's end.

| Metric | Definition and scope |
|---|---|
| MRR | Recurring contract charges less recurring discount, divided by billing months, for subscriptions active at month-end. Excludes taxes and one-time charges. |
| ARR | 12 times month-end MRR; an annualized run rate, not recognized revenue. |
| Invoiced amount | Sum of issued invoice totals, including simulated taxes and one-time charges. |
| Net collections | Successful payments less successful refunds/reversals, with both event and availability dates at or before cutoff. |
| Active accounts | Distinct customers with positive month-end MRR; concurrent subscriptions count once. |
| ARPA | Month-end MRR divided by active accounts. |
| Opening MRR | Prior month-end account MRR. Before first observed activation it is zero. |
| New / reactivated MRR | Closing MRR for accounts with zero opening MRR, distinguished using prior observed activity. |
| Expansion / contraction | Positive / negative difference in MRR for accounts active at both endpoints. |
| Churned MRR | Opening MRR for accounts with zero closing MRR. |
| Customer churn rate | Opening accounts inactive at month-end divided by opening active accounts. |
| NRR | Closing MRR from opening active accounts divided by their opening MRR; excludes new and reactivated accounts. |
| MoM growth | Change in MRR divided by preceding MRR; undefined when the preceding value is zero. |
| Outstanding / credit | Positive unpaid balance / positive overpayment at cutoff. Refunds reopen balance in this simulation; credit-note accounting is outside scope. |
| Days overdue | max(0, cutoff minus due date), only for outstanding invoices. Buckets: Current, 1–15, 16–30, 31–60, 61+. Paid rows are separate. |
| Payment delay | Successful payment event date minus invoice due date. Negative means early; averages are event-weighted, not invoice-weighted. |
| Payment failure rate | Failed payment attempts divided by all payment attempts; refunds/reversals excluded from denominator. |
| Retention cohort | First observed paid-contract activation month. Fraction with positive MRR at each later month-end; future unobserved ages stay null. Reactivated accounts count as retained at the observed endpoint. |
| Prediction label | Whether an account loses its last subscription during the next calendar month. Same-time renewals are not churn. A loss followed by reactivation still counts as an event. |
| High-risk MRR | Current MRR of scored accounts above the validation-selected threshold. Exposure, not guaranteed loss or probability-weighted expected loss. |

The generator changes lifecycle state only at month boundaries, so event churn and endpoint churn agree on this dataset. For general imported data these definitions can differ. The Power BI plan slicer assigns an account's full MRR to its largest current subscription tier; inactive accounts retain their last active tier so churn remains visible under plan filters. This is an account-segmentation view; upgrades move accounts between segments. Invoice plan segmentation uses the invoiced contract tier.

MRR is a snapshot: each card uses the latest selected month. Summing month-end MRR across dates does not produce a valid MRR card. Historical invoicing/collections in the regional query cover the full observed reporting period; current MRR/ARPA use its final month.
''')
write('docs/source_contracts.md','''# Source contracts and scope

Five CSV files use UTF-8 headers matching data_dictionary.md, ISO dates, integer paise, and stable business IDs. Input manifests contain SHA-256 hashes. `revpulse --source` expects this manifest alongside source files. No connector to a live billing platform is included.

Raw generation is deterministic by seed/configuration/version and stored under `data/sources/<source_id>`. Existing source files are verified, never silently overwritten. Reference truth and injected-defect manifests live under `data/reference/<source_id>` and are only used for evaluation.

Subscription periods are half-open [effective_from, effective_to). A future sentinel date denotes subscriptions still active at the observation cutoff; it is excluded from prediction features. Monthly and annual fixed-price plans are supported. Changes happen at renewal, avoiding proration. The simulation supports multiple subscriptions, partial payments, refunds, failed attempts, cancellation and reactivation. Tax is a simulated invoice component, not a tax-compliance implementation. No currency conversion or accounting revenue-recognition schedules are supplied.

Payment rows are immutable events. Exact repeats are duplicates; conflicting payloads for one event ID are quarantined. Mutable status-snapshot exports require an upstream adapter with version/event timestamps; this project does not guess which conflicting version is authoritative.

Only documented regional variants are normalized. Dates with slashes are ambiguous under the ISO source contract and are quarantined. Missing invoice totals are recovered only from populated authoritative components. Missing CSAT remains unavailable. Invalid usage is quarantined rather than clipped.

Conflicting keys and all detected overlapping subscription periods are quarantined. Dependent records lacking accepted parents are also quarantined, preserving relational integrity. Exclusions can reduce financial coverage; unknown missing financial values are not assigned invented amounts. Source row, original JSON, disposition and reason remain in the run audit and PostgreSQL lineage table.
''')
dictionary=['# Data dictionary','', 'One row has the grain below. Required fields are non-null except CSAT; missing invoice totals may be reconstructed during cleaning.','']
grains={'customers':'one customer account','subscription_periods':'one unchanged interval of subscription terms','invoices':'one issued invoice','payment_events':'one immutable payment/refund/reversal event','customer_monthly_activity':'one account-month'}
for table,fields in CONTRACTS.items():
    dictionary.extend([f'## {table}',f'Grain: {grains[table]}.','', '| Field | Type |','|---|---|']+[f'| `{field}` | {typ} |' for field,typ in fields.items()]+[''])
write('docs/data_dictionary.md','\n'.join(dictionary))
dispositions=pd.read_csv(run/'audit/row_dispositions.csv');transformations=pd.read_csv(run/'audit/transformations.csv')
log=['# Cleaning and validation log','',f'Run: `{run.name}`. Original source values remain in the run audit.','', '| Table | Input | Accepted | Exact duplicates | Quarantined |','|---|---:|---:|---:|---:|']
for table,v in quality['tables'].items():log.append(f"| {table} | {v['input']} | {v['accepted']} | {v['duplicate']} | {v['quarantined']} |")
log+=['','## Rejection reasons','','| Table | Reason | Rows |','|---|---|---:|']
for (table,reason),count in dispositions[dispositions.disposition!='accepted'].groupby(['table','reason']).size().items():log.append(f'| {table} | {reason} | {count} |')
log+=['','## Transformations','','| Table | Record | Field | Rule |','|---|---|---|---|']
for r in transformations.itertuples():log.append(f'| {r.table} | {r.key} | {r.field} | {r.rule} |')
log+=['','No statistical imputation is used for reported financial values. Statistical anomalies remain in accepted reporting data unless a separate validity rule quarantines them.']
write('docs/DATA_CLEANING_LOG.md','\n'.join(log));write('DATA_CLEANING_LOG.md','\n'.join(log))
write('docs/model_card.md',f'''# Churn model card

Purpose: prioritize existing active accounts for investigation at a month-end cutoff. Dataset: synthetic RevPulse simulation, not real customer outcomes.

Selected estimator: **{evaluation['selected_model']}**. Validation-selected threshold: **{evaluation['threshold']:.6f}**. Logistic Regression and Random Forest are compared on validation PR-AUC. A prevalence baseline and a simple usage/delay rule are reported on the held-out test set.

Numeric features: usage ratio and change, opened/unresolved tickets, CSAT and missingness, tenure, MRR, overdue balance and recent payment delay. Plan tier is one-hot encoded. Customer IDs, future cancellation dates and generator truth are excluded. Imputation/scaling/encoding are fitted only on training data.

```json
{json.dumps(evaluation['splits'],indent=2)}
```

Held-out PR-AUC: {evaluation['test']['pr_auc']:.4f}; prevalence: {evaluation['test']['prevalence']:.4f}; precision: {evaluation['test']['precision']:.4f}; recall: {evaluation['test']['recall']:.4f}; F1: {evaluation['test']['f1']:.4f}; Brier score: {evaluation['test']['brier']:.4f}.

The test set is evaluated after validation-based selection, with no test-driven tuning. Re-running the deterministic training command reproduces this report; it does not authorize iterative tuning against held-out outcomes. Monthly top-20 campaign metrics are in model_evaluation.json. Pooled top-K metrics are diagnostic; campaign capacity is evaluated per scoring month.

Existing accounts may appear in multiple chronological splits because the use case is recurring scoring. Results do not measure entirely new-account generalization. Recent payment-delay missingness is retained for training-only imputation. Features use event availability dates. Snapshots without a complete next-month observation window have null labels and are excluded from training/evaluation.

The saved model remains the training-only model used in evaluation; it is not silently refitted on held-out labels. Model and threshold are serialized together. Scoring exports include score date, model version and training-run ID. Current scores and supporting indicators are associations, not causal explanations. Synthetic performance does not establish commercial effectiveness or revenue saved.
''')
high=scores[scores.risk_category=='High']
overdue=aging.loc[aging.days_overdue>0,'outstanding_paise'].sum()/100
previous=monthly.iloc[-2].closing_mrr_paise
findings=f'''# Executive summary

Synthetic reporting cutoff: **{manifest['configuration']['cutoff']}**. All amounts below are INR. These findings describe the generated dataset.

1. Month-end MRR is **₹{last.closing_mrr_paise/100:,.2f}** across **{int(last.active_accounts):,} active accounts**, a **{(last.closing_mrr_paise/previous-1)*100:.2f}%** change from the preceding month. Review the SQL MRR bridge to separate expansion, contraction, acquisition and churn.
2. Latest-month NRR is **{last.nrr*100:.2f}%** and customer churn is **{last.customer_churn_rate*100:.2f}%**. Compare cohort retention before interpreting acquisition-led growth as retention improvement.
3. Overdue balances total **₹{overdue:,.2f}** at cutoff. Prioritize the oldest balances and review disputed/returned payments before collection outreach.
4. **{len(high):,} accounts** exceed the validation-selected churn threshold, representing **₹{high.mrr_inr.sum():,.2f}** of MRR exposure. This is not a prediction that the whole amount will be lost. Review usage decline and payment/support context before acting.
5. The selected churn model achieves held-out PR-AUC **{evaluation['test']['pr_auc']:.3f}** versus a churn prevalence of **{evaluation['test']['prevalence']:.3f}**. Recall at its selected threshold is **{evaluation['test']['recall']:.1%}**, so the model misses substantial churn and must not be treated as a complete retention strategy.

Validation: invoice totals, net collections, MRR, distinct accounts, balances and the MRR bridge reconcile. The Excel annual invoicing/delay audit has zero differences against matching SQL totals. Quarantined rows and transformations are itemized in DATA_CLEANING_LOG.md.

Native Excel refresh/editing and Power BI refresh/render/save-to-PBIX are deferred at the user's request. The XLSX structure/formulas/cached totals and PBIP JSON definitions have been checked independently.
'''
write('reports/executive_summary.md',findings)
for file in ['model_evaluation.json','defect_evaluation.json','hypothesis_result.json','mrr_trend.png']:
    if (run/'analytics'/file).exists():shutil.copy2(run/'analytics'/file,ROOT/'reports'/file)
for file in ['quality.json','reconciliation.json']:shutil.copy2(run/'audit'/file,ROOT/'reports'/file)
write('docs/runbook.md',r'''# Runbook

## Install and run

Use Python 3.13 on Windows for the supplied dependency lock. PostgreSQL 18 was used for verification. Alternative supported Python versions may need a newly resolved lock.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe scripts/setup_postgres.py
.\.venv\Scripts\python.exe -m revpulse.cli all
.\.venv\Scripts\python.exe -m pytest tests -q
```

The setup script creates only the project-owned `.local/pgdata` cluster at 127.0.0.1:55432, with a generated password in ignored `.local/database.json`. It does not reset or edit the existing server. Set POSTGRES_BIN if binaries are elsewhere. A preconfigured REVPULSE_DATABASE_URL can be used instead; the database role needs permission to create schemas and the btree_gist extension. Do not commit credentials.

`config/project.json` provides generation defaults. CLI flags override seed/accounts/start/months. Use `--workspace <absolute-project-directory>` when running from another directory or a non-editable installation. `generate` creates/reuses immutable source files. `ingest` and `validate` produce a new staging/audit directory without publication. `build` / `build-marts` build and publish core reporting outputs. `train` analyzes anomalies, trains/evaluates models and scores current accounts. `score` uses the saved model. `export` refreshes CSV extracts. `all` executes generate/build/train/score/export.

## Publication and recovery

`data/current.json` is the authoritative active-run pointer. Each core build writes a new run folder and a new PostgreSQL schema. Constraints and reconciliations pass before the schema commits and the pointer is replaced. Failed builds preserve the existing pointer and all published core files. Failed run folders carry FAILED.json; do not use them for reporting. Concurrent writers to one workspace are not supported. Unreferenced historical schemas/run folders are retained; cleanup is a deliberate operator task.

Analytics outputs are derived after core publication and include model/run metadata. If training fails, the core financial run remains valid but analytics are incomplete; rerun `train`, then `export`. Never present the presence of the core pointer as proof that every downstream artifact is refreshed.

The original prototype is retained under `data/legacy/prototype`. Old `data/raw` and `data/processed` files belong to that prototype and are not current inputs. Use the pointer and versioned run directories.

## Excel

Run `scripts/prepare_workbook.py`, then `scripts/build_workbook.ps1` with the bundled Node, module directory and Python paths returned by the artifact runtime loader. The builder uses @oai/artifact-tool; `add_native_pivots.py` supplements missing native pivot export using OOXML. `verify_artifacts.py` reads and verifies the result. The annual audit covers invoices issued and successful payment events in the cutoff calendar year; outstanding balances are as of cutoff.

The workbook includes XLOOKUPs, actual native PivotTables, validation, conditional formatting, cached results and SQL reconciliation. To validate native refresh later: activate Excel, open the workbook, confirm there is no repair prompt, refresh both pivots, force full calculation, inspect the reconciliation cells, then edit a source amount in a disposable copy and confirm dependent formulas/pivots update. Restore the original source afterward. Current native editing/refresh validation is deferred because Office is unlicensed.

## Power BI

```powershell
.\.venv\Scripts\python.exe -m revpulse.cli export
.\.venv\Scripts\python.exe scripts/build_powerbi.py
.\.venv\Scripts\python.exe scripts/validate_powerbi.py
```

Open `dashboard/RevPulse.pbip` in Power BI Desktop. DataFolder is an editable Power Query parameter; regenerate the project after relocating the repository or change this parameter. Refresh, verify the latest-month cards against mart_revenue_month.csv, then compare region/plan/date selections with customer-month SQL. Check that selecting multiple months still shows latest-month MRR. The actions page is a cutoff snapshot; the top-20 table is globally ranked before slicer filtering.

The project contains two main pages plus an audit/definitions page. Native refresh, DAX evaluation, visual screenshots and Save As `RevPulse_BI_Dashboard.pbix` remain deferred. PBIR schema checks are not a substitute for native checks. The downloaded signed installer is at D:\RevPulseRuntime\PBIDesktopSetup_x64.exe; administrator elevation is required. The prior installer attempt failed elevation despite returning exit code 0; its log records the failure. Do not interpret installer exit code alone as success.

Official format references: [report folders](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [semantic model folders](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).

## Notebooks and reproducibility

```powershell
.\.venv\Scripts\python.exe -m ipykernel install --user --name revpulse --display-name 'Python (RevPulse)'
.\.venv\Scripts\python.exe scripts/create_analysis_notebooks.py
```

Notebooks are saved with executed outputs. The hypothesis test uses a fixed single-month snapshot, not repeated customer-months as independent observations. Model evaluation consumes saved results and does not retune on test data.

`scripts/verify_clean_environment.ps1` creates a separate source checkout and virtual environment, installs the lock, runs tests and the complete 1,000-account pipeline. Supply a new verification directory for each run. Its test report is copied to reports/fresh_environment_tests.xml.

On this workstation `.venv` is a junction to D:\RevPulseRuntime\venv to avoid exhausting C:. This is a local storage arrangement, not required on other machines.
''')
write('README.md',f'''# RevPulse BI

Reproducible B2B SaaS revenue, billing quality and retention analytics. **All data is synthetic.** The project separates recurring revenue, invoicing and cash collections, preserves source lineage, and evaluates churn predictions using chronological splits.

## Delivery status

Implemented and tested: deterministic multi-table generation, strict validation/quarantine, PostgreSQL schemas and financial marts, six SQL analyses, Excel audit workbook, anomaly investigation, trained churn models, score exports, executed notebooks and documentation.

**Native application validation is deferred by user agreement:** Excel refresh/editing requires Office activation; Power BI refresh/rendering and final `.pbix` saving require Desktop installation with administrator approval. A schema-validated native `.pbip` project is supplied. No `.pbix` or native dashboard screenshots are claimed to exist.

## Start

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-lock.txt
.\\.venv\\Scripts\\python.exe -m pip install -e . --no-deps
.\\.venv\\Scripts\\python.exe scripts/setup_postgres.py
.\\.venv\\Scripts\\python.exe -m revpulse.cli all
.\\.venv\\Scripts\\python.exe -m pytest tests -q
```

See [runbook](docs/runbook.md) for artifact refresh, database configuration, environment reproduction and troubleshooting.

## Review the deliverables

- [Excel audit](excel/RevPulse_Validation_Audit.xlsx): {manifest['configuration']['cutoff'][:4]} invoicing and payment-delay audit, XLOOKUP enrichment, two native PivotTables and independent SQL controls.
- [Power BI project](dashboard/RevPulse.pbip): revenue/retention, collection/account actions, and definitions/quality pages.
- [Executed EDA notebook](notebooks/01_data_quality_and_eda.ipynb) and [churn evaluation](notebooks/02_churn_evaluation.ipynb).
- [Executive findings](reports/executive_summary.md), [model card](docs/model_card.md), [metric dictionary](docs/metric_dictionary.md), and [cleaning log](DATA_CLEANING_LOG.md).
- [Verification ledger](reports/implementation_status.json) records implemented, verified and deferred requirements.

## Architecture

```mermaid
flowchart LR
    A[Immutable source exports] --> B[Validation and quarantine]
    B --> C[Versioned PostgreSQL schema]
    C --> D[Reconciled SQL marts]
    D --> E[Excel audit]
    D --> F[Power BI project]
    D --> G[Anomaly and churn analysis]
    G --> F
```

Sources and run outputs are generated under ignored data directories. `data/current.json` identifies the published run and PostgreSQL schema. Core publication is atomic at this pointer. Reference truth never feeds model features. The legacy SQLite prototype is archived and no longer used by the CLI.

## Measured results

At {manifest['configuration']['cutoff']}, simulated MRR is ₹{last.closing_mrr_paise/100:,.2f} across {int(last.active_accounts):,} active accounts. Selected-model held-out PR-AUC is {evaluation['test']['pr_auc']:.3f}; recall is {evaluation['test']['recall']:.1%}. These are measured simulation results, not claims of real-world revenue saved.

![Simulated MRR trend](reports/mrr_trend.png)

## Limits

Fixed-price INR subscriptions, business-date events, no usage-based pricing, credit-note accounting, tax compliance, real-time ingestion or live customer outreach. Model indicators are associative. See the metric dictionary for churn/retention and plan-segmentation semantics.
''')
write('docs/NEXT_ACTION.md','''# Remaining native acceptance steps

The user explicitly chose to continue with files and defer native validation.

1. Activate Excel and verify workbook open, recalculation, PivotTable refresh and an input-change test.
2. Install Power BI Desktop with administrator approval, open dashboard/RevPulse.pbip, refresh, validate DAX/filter behavior, and inspect visual layout.
3. Save dashboard/RevPulse_BI_Dashboard.pbix and capture native report screenshots.
4. Update the verification ledger only after those checks pass.

Do not restart planning or rebuild already verified core components merely to resume these acceptance steps.
''')
print('Updated README, data/metric/source contracts, cleaning log, model card, executive summary and runbook')
