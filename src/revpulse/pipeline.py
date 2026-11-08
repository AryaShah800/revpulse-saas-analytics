import json
import re
import shutil
import uuid
from datetime import date,datetime,timezone
from decimal import Decimal
from pathlib import Path
from psycopg import sql
from .core import CONTRACTS,VERSION,json_write,write_csv,digest
from .generate import generate
from .clean import clean
from .database import connect,load,query_export

MARTS=['dim_date','fact_subscription_month','mart_customer_month','mart_revenue_month','mart_invoice_aging','mart_collections_month','mart_payment_delay','mart_billing_exceptions','mart_cohort_retention']

def reconcile(conn,tables,cfg):
    checks={}
    invoices=sum(r['total_paise'] for r in tables['invoices'] if r['issue_date']<=cfg.cutoff)
    checks['invoice_total']=int(conn.execute('SELECT coalesce(sum(total_paise),0) FROM mart_invoice_aging').fetchone()[0])==invoices
    cash=sum(r['amount_paise']*(1 if r['event_type']=='payment' else -1) for r in tables['payment_events'] if r['status']=='succeeded' and r['event_date']<=cfg.cutoff and r['available_date']<=cfg.cutoff)
    checks['collections_total']=int(conn.execute('SELECT coalesce(sum(net_collections_paise),0) FROM mart_collections_month').fetchone()[0])==cash
    checks['mrr_bridge']=conn.execute('SELECT count(*) FROM mart_revenue_month WHERE closing_mrr_paise<>opening_mrr_paise+new_mrr_paise+reactivation_mrr_paise+expansion_mrr_paise-contraction_mrr_paise-churned_mrr_paise').fetchone()[0]==0
    expected=sum((Decimal(r['recurring_paise']-r['discount_paise'])/r['billing_months'] for r in tables['subscription_periods'] if r['effective_from']<=cfg.cutoff<r['effective_to']),Decimal(0))
    actual=conn.execute('SELECT closing_mrr_paise FROM mart_revenue_month ORDER BY month DESC LIMIT 1').fetchone()[0]
    checks['month_end_mrr']=abs(actual-expected)<Decimal('.000001')
    expected_accounts=len({r['customer_id'] for r in tables['subscription_periods'] if r['effective_from']<=cfg.cutoff<r['effective_to']})
    checks['distinct_active_accounts']=conn.execute('SELECT active_accounts FROM mart_revenue_month ORDER BY month DESC LIMIT 1').fetchone()[0]==expected_accounts
    checks['balance_identity']=conn.execute('SELECT count(*) FROM mart_invoice_aging WHERE total_paise-net_paid_paise<>outstanding_paise-credit_paise').fetchone()[0]==0
    if not all(checks.values()):raise ValueError(f'Reconciliation failed: {checks}')
    return dict(checks=checks,invoiced_paise=invoices,net_collections_paise=cash,closing_mrr_paise=str(expected),active_accounts=expected_accounts)

def build(cfg,source=None,fail_before_publish=False):
    source=source or generate(cfg)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]
    out=cfg.root/'data/runs'/run_id;out.mkdir(parents=True)
    schema='run_'+uuid.uuid4().hex[:16]
    tables,audit=clean(source,out)
    try:
        with connect(cfg.root) as conn:
            load(conn,cfg.root,schema,tables,audit)
            conn.execute('CREATE TABLE run_config(start_date date,cutoff date)')
            conn.execute('INSERT INTO run_config VALUES (%s,%s)',(date.fromisoformat(cfg.start),cfg.cutoff))
            conn.execute((cfg.root/'sql/marts/001_marts.sql').read_text())
            evidence=reconcile(conn,tables,cfg)
            for mart in MARTS:query_export(conn,sql.SQL('SELECT * FROM {}').format(sql.Identifier(mart)),out/'marts'/f'{mart}.csv')
            queries=(cfg.root/'sql/analytical_queries.sql').read_text(encoding='utf-8-sig')
            for name,query in re.findall(r'-- name: (\w+)\s*\n(.*?)(?=-- name:|\Z)',queries,re.S):query_export(conn,query,out/'queries'/f'{name}.csv')
            json_write(out/'audit/reconciliation.json',evidence)
            json_write(out/'manifest.json',dict(run_id=run_id,schema=schema,source=str(source.relative_to(cfg.root)),configuration=cfg.payload(),version=VERSION))
            if fail_before_publish:raise RuntimeError('Injected failure before publication')
        # Immutable output directory and committed schema exist before pointer changes.
        pointer=cfg.root/'data/current.json';temporary=pointer.with_suffix('.tmp')
        json_write(temporary,dict(run_id=run_id,path=str(out.relative_to(cfg.root)),schema=schema))
        temporary.replace(pointer)
    except Exception as error:
        json_write(out/'FAILED.json',dict(error=str(error)))
        raise
    return out

def export_current(root):
    from .core import current_run
    run=current_run(root)
    target=root/'dashboard/data';target.mkdir(parents=True,exist_ok=True)
    for folder in ['clean','marts','queries','analytics']:
        if (run/folder).exists():
            for file in (run/folder).glob('*.csv'):shutil.copy2(file,target/file.name)
    json_write(target/'refresh.json',json.loads((run/'manifest.json').read_text()))
    return target
