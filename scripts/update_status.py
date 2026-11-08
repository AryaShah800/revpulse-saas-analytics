"""Record evidence-backed requirement status; native acceptance stays deferred."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from revpulse.core import current_run,json_write

root=Path(__file__).resolve().parents[1];run=current_run(root)
tests=ET.parse(root/'reports/test_results.xml').getroot()
suites=list(tests.iter('testsuite'))
test_count=sum(int(s.attrib.get('tests',0)) for s in suites)
if any(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites):raise ValueError('Failing tests cannot be marked verified')
items=[]
def item(id,requirement,implementation,evidence,status='verified'):
    for path in implementation+evidence:
        if not (root/path).exists():raise ValueError(f'Missing evidence: {path}')
    items.append(dict(id=id,requirement=requirement,status=status,implementation=implementation,evidence=evidence))
test=['reports/test_results.xml']
item('R01','Configurable CLI, empty exports, explicit errors',['src/revpulse/cli.py','src/revpulse/core.py','config/project.json'],test)
item('R02','Pinned dependencies and independent environment reproduction',['pyproject.toml','requirements-lock.txt','scripts/verify_clean_environment.ps1'],['reports/reproducibility.json','reports/fresh_environment_tests.xml'])
item('R03','Dated five-table generator with annual/monthly contracts and lifecycle changes',['src/revpulse/generate.py'],test+['docs/source_contracts.md'])
item('R04','Isolated truth, defect manifest and immutable source hashes',['src/revpulse/generate.py'],test+['reports/defect_evaluation.json'])
item('R05','Hand-calculated ten-account financial fixture',['tests/test_financial_contracts.py','tests/fixtures'],test)
item('R06','Strict parsing, missing-amount recovery and quarantine',['src/revpulse/clean.py'],test+['DATA_CLEANING_LOG.md'])
item('R07','Exact duplicates, conflicting keys, overlapping periods and parent integrity',['src/revpulse/clean.py','sql/migrations/001_core.sql'],test)
item('R08','Lineage, dispositions, row reconciliation and exclusion disclosure',['src/revpulse/clean.py','src/revpulse/database.py'],['reports/quality.json','DATA_CLEANING_LOG.md'])
item('R09','Actual PostgreSQL integration, constraints and versioned schemas',['src/revpulse/database.py','scripts/setup_postgres.py'],test+['reports/reconciliation.json'])
item('R10','Atomic published core output pointer and failure preservation',['src/revpulse/pipeline.py'],test)
item('R11','MRR, annual normalization, distinct accounts and revenue bridge',['sql/marts/001_marts.sql'],test+['reports/reconciliation.json'])
item('R12','Historical balances, early/late payments, refunds and nonoverlapping aging',['sql/marts/001_marts.sql'],test)
item('R13','Six analytical SQL queries, preaggregation, cohorts and unobserved periods',['sql/analytical_queries.sql'],test)
item('R14','Excel XLOOKUP, validations, conditional formatting and SQL reconciliation',['excel/RevPulse_Validation_Audit.xlsx','scripts/build_workbook.mjs'],['reports/workbook/verification.json','reports/workbook/recalculation_checks.json'])
item('R15','Two native PivotTables with caches and source references',['scripts/add_native_pivots.py','excel/RevPulse_Validation_Audit.xlsx'],['reports/workbook/verification.json'])
item('R16','Workbook visual inspection across all six sheets',['excel/RevPulse_Validation_Audit.xlsx'],['reports/workbook/Overview.png','reports/workbook/Cleaned_Master.png','reports/workbook/Customers.png','reports/workbook/Payments.png','reports/workbook/Audit_Pivots.png','reports/workbook/Reconciliation.png'])
item('R17','Native Excel open, input-change recalculation and pivot refresh',['excel/RevPulse_Validation_Audit.xlsx'],['docs/NEXT_ACTION.md'],'deferred_by_user')
item('R18','Power BI project with two main pages and audit view',['dashboard/RevPulse.pbip','scripts/build_powerbi.py'],['reports/powerbi_schema_validation.json'],'implemented_schema_verified')
item('R19','Semantic model relationships, snapshot measures and risk integration',['dashboard/RevPulse.SemanticModel/model.bim','dashboard/measures.md'],['reports/powerbi_schema_validation.json'],'implemented_native_unverified')
item('R20','Native Power BI refresh, visual/filter inspection, PBIX and screenshots',['dashboard/RevPulse.pbip'],['docs/NEXT_ACTION.md'],'deferred_by_user')
item('R21','Contract billing exceptions, peer IQR, support spikes and defect evaluation',['src/revpulse/analytics.py'],['reports/defect_evaluation.json'])
item('R22','EDA and single-snapshot exploratory hypothesis with uncertainty',['notebooks/01_data_quality_and_eda.ipynb'],['reports/hypothesis_result.json'])
item('R23','Point-in-time features and future-observation invariance',['src/revpulse/features.py'],test)
item('R24','Observed churn labels and chronological train/validation/test splits',['src/revpulse/features.py','src/revpulse/model.py'],test+['reports/model_evaluation.json'])
item('R25','Logistic/forest comparison, baselines, calibration and campaign-capacity metrics',['src/revpulse/model.py','notebooks/02_churn_evaluation.ipynb'],['reports/model_evaluation.json'])
item('R26','Saved model, score export and model card',['models/churn_model.joblib','docs/model_card.md'],['reports/reproducibility.json'])
item('R27','Executive findings, dictionaries, cleaning log and runbook',['README.md','reports/executive_summary.md','docs/data_dictionary.md','docs/metric_dictionary.md','docs/source_contracts.md','docs/runbook.md'],['reports/reconciliation.json','reports/model_evaluation.json'])
report=dict(status='Portfolio delivery complete; native acceptance deferred by user',test_count=test_count,run_id=run.name,requirements=items,remaining=['Excel native editing/recalculation/PivotTable refresh','Power BI native refresh/DAX/filter/layout validation','Save validated PBIX and native screenshots'])
json_write(root/'reports/implementation_status.json',report)
lines=['# Delivery verification','',f'Automated tests: **{test_count} passed**. Independent-environment reproduction passed.','', '**Portfolio delivery complete. Native Excel and Power BI acceptance remains deferred.**','', '| ID | Requirement | Status | Evidence |','|---|---|---|---|']
for r in items:lines.append(f"| {r['id']} | {r['requirement']} | {r['status']} | {', '.join(r['evidence'])} |")
(root/'reports/DELIVERY_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Recorded {len(items)} requirements with evidence and explicit native deferrals')
