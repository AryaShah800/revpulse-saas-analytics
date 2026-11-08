"""Seeded operational simulation. Reference truth is isolated from pipeline inputs."""
from copy import deepcopy
from datetime import date,timedelta
import hashlib
import json
import random
from .core import CONTRACTS,KEYS,VERSION,add_months,month_end,write_csv,json_write,digest

def simulate(cfg):
    rng=random.Random(cfg.seed)
    tables={k:[] for k in CONTRACTS}
    prices={'Starter':100000,'Growth':500000,'Enterprise':2000000}
    start=date.fromisoformat(cfg.start)
    for i in range(cfg.accounts):
        cid=f'C{i+1:04d}'
        joined=rng.randrange(min(18,cfg.months-3))
        signup=add_months(start,joined)
        tables['customers'].append(dict(customer_id=cid,company_name=f'RevPulse Demo Company {i+1:04d}',signup_date=signup,region=rng.choice(['North','South','East','West']),acquisition_channel=rng.choice(['Organic','Referral','LinkedIn Ads','Cold Email'])))
        health=rng.uniform(.45,.95);active=True;reactivate_at=None;primary=None;secondary=None;renewal=None;unresolved=0
        period_number=0
        for m in range(joined,cfg.months):
            d=add_months(start,m);end=month_end(d)
            if not active:
                if reactivate_at is not None and m==reactivate_at:active=True;primary=None;health=rng.uniform(.5,.9)
                else:continue
            health=max(.06,min(.98,health+rng.gauss(.005,.10)))
            if primary is None or (d==renewal and rng.random()<.16):
                if primary is not None:primary['effective_to']=d
                period_number+=1
                tier=rng.choices(list(prices),[.45,.4,.15])[0]
                interval=rng.choices([1,12],[.8,.2])[0]
                monthly=prices[tier]
                discount=monthly*interval//10 if rng.random()<.15 else 0
                primary=dict(period_id=f'{cid}-P{period_number}',subscription_id=f'{cid}-S1',customer_id=cid,effective_from=d,effective_to=date(2100,1,1),plan_tier=tier,billing_months=interval,recurring_paise=monthly*interval,discount_paise=discount)
                tables['subscription_periods'].append(primary);renewal=d
            # A second subscription allows distinct-account counting to be tested.
            if secondary is None and m==joined+3 and i%10==0:
                secondary=dict(period_id=f'{cid}-ADD',subscription_id=f'{cid}-S2',customer_id=cid,effective_from=d,effective_to=date(2100,1,1),plan_tier='Starter',billing_months=1,recurring_paise=50000,discount_paise=0)
                tables['subscription_periods'].append(secondary)
            billed=[]
            if d==renewal:
                billed.append(primary);renewal=add_months(d,primary['billing_months'])
            if secondary is not None:billed.append(secondary)
            for period in billed:
                iid=f"{period['period_id']}-{d:%Y%m}"
                recurring=period['recurring_paise']-period['discount_paise']
                one_time=25000 if m==joined else 0
                tax=(recurring+one_time)*18//100
                total=recurring+one_time+tax
                inv=dict(invoice_id=iid,customer_id=cid,period_id=period['period_id'],issue_date=d,due_date=d+timedelta(days=14),service_from=d,service_to=add_months(d,period['billing_months']),recurring_paise=recurring,one_time_paise=one_time,tax_paise=tax,total_paise=total)
                tables['invoices'].append(inv)
                delay=max(-10,int(rng.gauss((1-health)*40-8,9)))
                paid=inv['due_date']+timedelta(days=delay)
                if rng.random()<.08+(1-health)*.15:
                    tables['payment_events'].append(dict(event_id=iid+'-F',invoice_id=iid,event_date=inv['due_date'],available_date=inv['due_date'],event_type='payment',status='failed',amount_paise=total))
                    paid+=timedelta(days=10)
                if rng.random()<.04+(1-health)*.05:continue
                partial=rng.random()<.08
                amount=total//2 if partial else total
                tables['payment_events'].append(dict(event_id=iid+'-PAY',invoice_id=iid,event_date=paid,available_date=paid,event_type='payment',status='succeeded',amount_paise=amount))
                if partial:
                    later=paid+timedelta(days=20)
                    tables['payment_events'].append(dict(event_id=iid+'-BAL',invoice_id=iid,event_date=later,available_date=later,event_type='payment',status='succeeded',amount_paise=total-amount))
                elif rng.random()<.015:
                    later=paid+timedelta(days=5)
                    tables['payment_events'].append(dict(event_id=iid+'-REF',invoice_id=iid,event_date=later,available_date=later,event_type='refund',status='succeeded',amount_paise=total//10))
            entitled=50 if primary['plan_tier']!='Enterprise' else 200
            tickets=max(0,int(rng.gauss((1-health)*8,2)))
            resolved=min(unresolved+tickets,rng.randrange(1,8));unresolved=unresolved+tickets-resolved
            responses=rng.choice([0,1,3,5])
            tables['customer_monthly_activity'].append(dict(record_id=f'{cid}-{d:%Y%m}',customer_id=cid,month=d,available_date=end,active_users=max(0,min(entitled,int(entitled*health+rng.gauss(0,3)))),entitled_users=entitled,tickets_opened=tickets,tickets_resolved=resolved,unresolved_tickets=unresolved,csat_score=round(max(1,min(5,1+health*4+rng.gauss(0,.4))),2) if responses else None,csat_responses=responses))
            # Outcome is sampled after observed activity, not copied into predictors.
            if m<cfg.months-1 and rng.random()<.008+(1-health)**3*.18:
                ending=add_months(d,1);primary['effective_to']=ending
                if secondary is not None:secondary['effective_to']=ending
                secondary=None;active=False;reactivate_at=m+rng.randrange(3,8) if rng.random()<.35 else None
    tables['payment_events']=[r for r in tables['payment_events'] if r['available_date']<=cfg.cutoff]
    return tables

def generate(cfg):
    signature={k:v for k,v in cfg.payload().items() if k!='root'}
    source_id=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:16]
    source=cfg.root/'data/sources'/source_id
    if (source/'manifest.json').exists():
        manifest=json.loads((source/'manifest.json').read_text())
        if any(digest(source/f'{k}.csv')!=v for k,v in manifest['hashes'].items()):raise ValueError('Immutable source hash mismatch')
        return source
    truth=simulate(cfg);validate_truth(truth);dirty=deepcopy(truth);defects=[]
    for name,rows in truth.items():write_csv(cfg.root/'data/reference'/source_id/f'{name}.csv',rows,CONTRACTS[name])
    def change(table,index,field,value,kind):
        row=dirty[table][index];old=row[field];row[field]=value
        defects.append(dict(table=table,key=row[KEYS[table]],field=field,original=str(old),injected=str(value),kind=kind))
    if len(dirty['invoices'])>10:
        dirty['invoices'].append(deepcopy(dirty['invoices'][0]));defects.append(dict(table='invoices',key=dirty['invoices'][0]['invoice_id'],kind='exact_duplicate'))
        change('invoices',1,'total_paise','', 'recoverable_missing')
        change('invoices',2,'total_paise',dirty['invoices'][2]['total_paise']+10000,'invoice_mismatch')
        conflict=deepcopy(dirty['invoices'][3]);conflict['total_paise']+=5000;dirty['invoices'].append(conflict)
        defects.append(dict(table='invoices',key=conflict['invoice_id'],kind='conflicting_key'))
        change('invoices',4,'customer_id','UNKNOWN','orphan_customer')
        change('invoices',5,'issue_date','04/05/2023','ambiguous_date')
        # Internally balanced charge discrepancy must be caught against contract terms.
        dirty['invoices'][6]['recurring_paise']+=30000
        change('invoices',6,'total_paise',dirty['invoices'][6]['total_paise']+30000,'contract_mismatch')
        change('customer_monthly_activity',0,'active_users',9999,'invalid_usage')
        change('customers',0,'region',' west-india ','region_variant')
    for name,rows in dirty.items():write_csv(source/f'{name}.csv',rows,CONTRACTS[name])
    json_write(cfg.root/'data/reference'/source_id/'defects.json',defects)
    json_write(source/'manifest.json',dict(source_id=source_id,configuration=signature,hashes={k:digest(source/f'{k}.csv') for k in CONTRACTS}))
    return source

def validate_truth(tables):
    for name,rows in tables.items():
        ids=[r[KEYS[name]] for r in rows]
        if len(ids)!=len(set(ids)):raise ValueError(f'Generator duplicate key: {name}')
    customers={r['customer_id'] for r in tables['customers']}
    periods={r['period_id']:r for r in tables['subscription_periods']}
    invoices={r['invoice_id']:r for r in tables['invoices']}
    for period in periods.values():
        if period['customer_id'] not in customers or period['effective_from']>=period['effective_to']:raise ValueError('Generator invalid period')
    for row in invoices.values():
        if row['customer_id'] not in customers or row['period_id'] not in periods:raise ValueError('Generator orphan invoice')
        if row['total_paise']!=row['recurring_paise']+row['one_time_paise']+row['tax_paise']:raise ValueError('Generator invoice identity')
    if any(r['invoice_id'] not in invoices for r in tables['payment_events']):raise ValueError('Generator orphan payment')
    if any(not 0<=r['active_users']<=r['entitled_users'] for r in tables['customer_monthly_activity']):raise ValueError('Generator usage bounds')
