"""Shared contracts, configuration and deterministic file I/O."""
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
import csv
import hashlib
import json
import os

VERSION = '2.0.0'
CONTRACTS = {
 'customers': {'customer_id':'text','company_name':'text','signup_date':'date','region':'text','acquisition_channel':'text'},
 'subscription_periods': {'period_id':'text','subscription_id':'text','customer_id':'text','effective_from':'date','effective_to':'date','plan_tier':'text','billing_months':'int','recurring_paise':'int','discount_paise':'int'},
 'invoices': {'invoice_id':'text','customer_id':'text','period_id':'text','issue_date':'date','due_date':'date','service_from':'date','service_to':'date','recurring_paise':'int','one_time_paise':'int','tax_paise':'int','total_paise':'int'},
 'payment_events': {'event_id':'text','invoice_id':'text','event_date':'date','available_date':'date','event_type':'text','status':'text','amount_paise':'int'},
 'customer_monthly_activity': {'record_id':'text','customer_id':'text','month':'date','available_date':'date','active_users':'int','entitled_users':'int','tickets_opened':'int','tickets_resolved':'int','unresolved_tickets':'int','csat_score':'float','csat_responses':'int'},
}
KEYS = {name:next(iter(fields)) for name,fields in CONTRACTS.items()}

@dataclass(frozen=True)
class Config:
    root: Path
    seed: int = 42
    accounts: int = 1000
    start: str = '2023-01-01'
    months: int = 36
    def __post_init__(self):
        if self.accounts < 1 or self.months < 6 or date.fromisoformat(self.start).day != 1:
            raise ValueError('accounts must be positive, months >= 6, and start must be an ISO month-start')
    @property
    def cutoff(self): return month_end(add_months(date.fromisoformat(self.start),self.months-1))
    def payload(self): return {**asdict(self),'root':str(self.root),'version':VERSION,'cutoff':self.cutoff.isoformat()}

def add_months(d,n):
    m=d.year*12+d.month-1+n
    return date(m//12,m%12+1,1)

def month_end(d):
    from datetime import timedelta
    return add_months(d,1)-timedelta(days=1)

def root_default(): return Path(os.environ.get('REVPULSE_WORKSPACE',Path(__file__).resolve().parents[2])).resolve()

def json_write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False),encoding='utf-8')

def write_csv(path,rows,fields):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)

def read_csv(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def current_run(root):
    pointer=Path(root)/'data/current.json'
    if not pointer.exists():raise ValueError('No published run. Run revpulse all first.')
    return Path(root)/json.loads(pointer.read_text())['path']
