"""Export typed workbook inputs and independent SQL control totals."""
from pathlib import Path
import json
import pandas as pd
from psycopg import sql
from revpulse.core import current_run,json_write
from revpulse.database import connect

root=Path(__file__).resolve().parents[1];run=current_run(root)
manifest=json.loads((run/'manifest.json').read_text());cutoff=manifest['configuration']['cutoff']
start=f'{cutoff[:4]}-01-01'
customers=pd.read_csv(run/'clean/customers.csv')
invoices=pd.read_csv(run/'marts/mart_invoice_aging.csv')
invoices=invoices[(invoices.issue_date>=start)&(invoices.issue_date<=cutoff)].copy()
delays=pd.read_csv(run/'marts/mart_payment_delay.csv')
delays=delays[(delays.event_date>=start)&(delays.event_date<=cutoff)].copy()
invoices['amount_inr']=invoices.total_paise/100;invoices['outstanding_inr']=invoices.outstanding_paise/100
columns=['invoice_id','customer_id','issue_date','due_date','plan_tier','amount_inr','outstanding_inr','days_overdue']
with connect(root) as conn:
    conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(manifest['schema'])))
    regional=conn.execute('SELECT region,sum(total_paise)/100.0 FROM mart_invoice_aging WHERE issue_date BETWEEN %s AND %s GROUP BY region ORDER BY region',(start,cutoff)).fetchall()
    plan_delay=conn.execute('SELECT plan_tier,avg(delay_days) FROM mart_payment_delay WHERE event_date BETWEEN %s AND %s GROUP BY plan_tier ORDER BY plan_tier',(start,cutoff)).fetchall()
    total=conn.execute('SELECT sum(total_paise)/100.0 FROM mart_invoice_aging WHERE issue_date BETWEEN %s AND %s',(start,cutoff)).fetchone()[0]
payload=dict(start=start,cutoff=cutoff,source_id=manifest['source'],run_id=manifest['run_id'],customers=customers[['customer_id','company_name','region','acquisition_channel']].values.tolist(),invoices=invoices[columns].values.tolist(),invoice_headers=columns,delays=delays[['event_id','invoice_id','plan_tier','delay_days']].values.tolist(),regional=[[k,float(v)] for k,v in regional],plan_delay=[[k,float(v)] for k,v in plan_delay],total_inr=float(total))
json_write(root/'.local/artifact/workbook_input.json',payload)
print(f'Workbook scope: {len(invoices)} invoices and {len(delays)} payments, {start} through {cutoff}')
