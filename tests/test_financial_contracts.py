from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import shutil
import uuid
import pandas as pd
import pytest
from psycopg import sql
from revpulse.core import Config,CONTRACTS,write_csv,digest,json_write
from revpulse.database import connect,load
from revpulse.pipeline import build,reconcile
from revpulse.features import make_features,NUMERIC,CATEGORICAL

ROOT=Path(__file__).resolve().parents[1]

def fixture_tables():
    t={k:[] for k in CONTRACTS}
    for i in range(1,11):t['customers'].append(dict(customer_id=f'C{i}',company_name=f'Fixture {i}',signup_date=date(2023,1,1),region='West',acquisition_channel='Organic'))
    def period(pid,cid,start,end,amount,interval=1,subscription=None):
        t['subscription_periods'].append(dict(period_id=pid,subscription_id=subscription or pid,customer_id=cid,effective_from=date.fromisoformat(start),effective_to=date.fromisoformat(end),plan_tier='Starter',billing_months=interval,recurring_paise=amount,discount_paise=0))
    period('annual','C1','2023-01-01','2100-01-01',1200000,12)
    period('base','C2','2023-01-01','2100-01-01',100000)
    period('addon','C2','2023-01-01','2023-03-01',50000)
    period('upgrade1','C3','2023-01-01','2023-02-01',100000,subscription='upgrade')
    period('upgrade2','C3','2023-02-01','2100-01-01',200000,subscription='upgrade')
    period('cancel','C4','2023-01-01','2023-02-01',100000)
    period('react1','C5','2023-01-01','2023-02-01',100000,subscription='react')
    period('react2','C5','2023-03-01','2100-01-01',100000,subscription='react')
    for i in range(6,11):period(f'P{i}',f'C{i}','2023-01-01','2100-01-01',100000)
    for iid,cid,pid,amount in [('I1','C1','annual',1200000),('I6','C6','P6',100000),('I7','C7','P7',100000),('I8','C8','P8',100000)]:
        t['invoices'].append(dict(invoice_id=iid,customer_id=cid,period_id=pid,issue_date=date(2023,1,1),due_date=date(2023,1,15),service_from=date(2023,1,1),service_to=date(2024,1,1) if iid=='I1' else date(2023,2,1),recurring_paise=amount,one_time_paise=0,tax_paise=0,total_paise=amount))
    for eid,iid,when,kind,amount in [('E1','I6','2023-01-10','payment',40000),('E2','I6','2023-07-01','payment',60000),('E3','I7','2023-01-10','payment',100000),('E4','I7','2023-02-01','refund',10000),('E5','I8','2023-07-01','payment',100000)]:
        t['payment_events'].append(dict(event_id=eid,invoice_id=iid,event_date=date.fromisoformat(when),available_date=date.fromisoformat(when),event_type=kind,status='succeeded',amount_paise=amount))
    return t

@pytest.fixture
def db():
    conn=connect(ROOT)
    try:yield conn
    finally:conn.rollback();conn.close()

def test_hand_calculated_financial_fixture(db):
    tables=fixture_tables();schema='fixture_'+uuid.uuid4().hex[:12]
    load(db,ROOT,schema,tables,[])
    db.execute('CREATE TABLE run_config(start_date date,cutoff date)')
    db.execute("INSERT INTO run_config VALUES ('2023-01-01','2023-06-30')")
    db.execute((ROOT/'sql/marts/001_marts.sql').read_text())
    rows=db.execute('SELECT month,closing_mrr_paise,active_accounts FROM mart_revenue_month ORDER BY month').fetchall()
    assert rows[0][1:]==(Decimal(1050000),10)
    assert rows[1][1:]==(Decimal(950000),8)
    assert rows[2][1:]==(Decimal(1000000),9)
    balances=dict(db.execute('SELECT invoice_id,outstanding_paise FROM mart_invoice_aging').fetchall())
    assert balances=={'I1':1200000,'I6':60000,'I7':10000,'I8':100000}
    assert db.execute("SELECT mrr_paise FROM fact_subscription_month WHERE period_id='annual' LIMIT 1").fetchone()[0]==100000
    assert db.execute("SELECT count(*) FROM mart_customer_month WHERE customer_id='C2' AND movement='Churn'").fetchone()[0]==0
    assert db.execute("SELECT movement FROM mart_customer_month WHERE customer_id='C5' AND month='2023-03-01'").fetchone()[0]=='Reactivation'
    assert db.execute("SELECT plan_tier FROM mart_customer_month WHERE customer_id='C4' AND month='2023-02-01'").fetchone()[0]=='Starter'
    assert db.execute('SELECT count(*) FROM mart_revenue_month WHERE closing_mrr_paise<>opening_mrr_paise+new_mrr_paise+reactivation_mrr_paise+expansion_mrr_paise-contraction_mrr_paise-churned_mrr_paise').fetchone()[0]==0
    assert db.execute('SELECT count(*) FROM mart_cohort_retention WHERE age=12 AND retention IS NOT NULL').fetchone()[0]==0
    assert db.execute("SELECT delay_days FROM mart_payment_delay WHERE event_id='E1'").fetchone()[0]==-5
    assert db.execute("SELECT count(*) FROM mart_payment_delay WHERE event_id IN ('E2','E5')").fetchone()[0]==0
    import re
    results={}
    for name,query in re.findall(r'-- name: (\w+)\s*\n(.*?)(?=-- name:|\Z)',(ROOT/'sql/analytical_queries.sql').read_text(),re.S):
        cursor=db.execute(query);results[name]=[dict(zip([c.name for c in cursor.description],r)) for r in cursor.fetchall()]
    assert len(results)==6
    assert sum(r['historical_invoiced_paise'] or 0 for r in results['customer_360'])==1500000
    assert sum(r['collections_paise'] or 0 for r in results['regional_channel_performance'])==130000

def test_database_rejects_overlapping_periods(db):
    load(db,ROOT,'fixture_'+uuid.uuid4().hex[:12],fixture_tables(),[])
    with pytest.raises(Exception,match='exclusion constraint'):
        db.execute("INSERT INTO subscription_periods SELECT 'bad',subscription_id,customer_id,effective_from,effective_to,plan_tier,billing_months,recurring_paise,discount_paise FROM subscription_periods WHERE period_id='annual'")

def test_future_events_do_not_change_features():
    t=fixture_tables();frames={k:pd.DataFrame(v,columns=CONTRACTS[k]) for k,v in t.items()}
    frames['customer_monthly_activity']=pd.DataFrame([
        dict(record_id='known',customer_id='C1',month='2023-01-01',available_date='2023-01-31',active_users=20,entitled_users=50,tickets_opened=2,tickets_resolved=1,unresolved_tickets=1,csat_score=4,csat_responses=1),
        dict(record_id='future',customer_id='C1',month='2023-02-01',available_date='2023-02-28',active_users=1,entitled_users=50,tickets_opened=30,tickets_resolved=0,unresolved_tickets=31,csat_score=1,csat_responses=1)
    ])
    for name,contract in CONTRACTS.items():
        for col,typ in contract.items():
            if typ=='date':frames[name][col]=pd.to_datetime(frames[name][col])
    before=make_features(frames,['2023-01-01'],'2023-06-30')
    frames['payment_events'].loc[frames['payment_events'].event_date>'2023-01-31','amount_paise']=999999999
    frames['customer_monthly_activity'].loc[frames['customer_monthly_activity'].available_date>'2023-01-31','active_users']=49
    after=make_features(frames,['2023-01-01'],'2023-06-30')
    pd.testing.assert_frame_equal(before[NUMERIC+CATEGORICAL],after[NUMERIC+CATEGORICAL])
    assert before.set_index('customer_id').loc['C2','is_churned']==0
    assert before.set_index('customer_id').loc['C1','usage_ratio']==.4
    assert before.set_index('customer_id').loc['C4','is_churned']==1
    assert make_features(frames,['2023-06-01'],'2023-06-30').is_churned.isna().all()

def test_empty_csv_retains_contract(tmp_path):
    file=tmp_path/'empty.csv';write_csv(file,[],CONTRACTS['invoices'])
    assert file.read_text().strip()==','.join(CONTRACTS['invoices'])

def test_invalid_configuration():
    with pytest.raises(ValueError):Config(ROOT,accounts=0)
    with pytest.raises(ValueError):Config(ROOT,start='2023-01-02')
