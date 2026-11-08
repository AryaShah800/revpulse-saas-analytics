"""Strict source parsing, conflict quarantine and complete row dispositions."""
from collections import Counter,defaultdict
from datetime import date
import json
import csv
import math
import re
from .core import CONTRACTS,KEYS,read_csv,write_csv,json_write,digest

def clean(source,out):
    manifest=json.loads((source/'manifest.json').read_text())
    for table,expected in manifest['hashes'].items():
        if digest(source/f'{table}.csv')!=expected:raise ValueError(f'Source changed: {table}')
    accepted={};audit=[];changes=[];summary={}
    for table,contract in CONTRACTS.items():
        with (source/f'{table}.csv').open(encoding='utf-8',newline='') as f:
            header=next(csv.reader(f),[])
        missing=set(contract)-set(header)
        if missing:raise ValueError(f'{table}: missing required columns {sorted(missing)}')
        raw=read_csv(source/f'{table}.csv');groups=defaultdict(list)
        for line,row in enumerate(raw,2):groups[row[KEYS[table]]].append((line,row))
        overlapping=set()
        if table=='subscription_periods':
            by_subscription=defaultdict(list)
            for row in raw:
                try:by_subscription[row['subscription_id']].append((date.fromisoformat(row['effective_from']),date.fromisoformat(row['effective_to']),row['period_id']))
                except ValueError:pass  # Date parsing below records the actual rejection.
            for intervals in by_subscription.values():
                for i,(start,end,pid) in enumerate(intervals):
                    for other_start,other_end,other_id in intervals[i+1:]:
                        if pid!=other_id and start<other_end and other_start<end:overlapping.update([pid,other_id])
        records=[]
        customer_ids={r['customer_id'] for r in accepted.get('customers',[])}
        invoice_ids={r['invoice_id'] for r in accepted.get('invoices',[])}
        periods={r['period_id']:r for r in accepted.get('subscription_periods',[])}
        for key,items in groups.items():
            variants={tuple(r.items()) for _,r in items}
            conflict=len(variants)>1
            for n,(line,row) in enumerate(items):
                disposition='accepted';reason='';parsed={}
                if key in overlapping:disposition='quarantined';reason='overlapping_period'
                elif conflict:disposition='quarantined';reason='conflicting_key'
                elif n>0:disposition='duplicate';reason='exact_duplicate'
                else:
                    try:
                        for col,typ in contract.items():
                            value=row.get(col,'')
                            if value=='' and (col=='csat_score' or (table=='invoices' and col=='total_paise')):parsed[col]=None;continue
                            if value=='':raise ValueError(f'missing:{col}')
                            if typ=='date':
                                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError(f'invalid_iso_date:{col}')
                                parsed[col]=date.fromisoformat(value)
                            elif typ=='int':parsed[col]=int(value)
                            elif typ=='float':
                                parsed[col]=float(value)
                                if not math.isfinite(parsed[col]):raise ValueError(f'nonfinite:{col}')
                            else:parsed[col]=value.strip()
                        if table=='customers':
                            normalized=parsed['region'].lower().replace('-',' ').replace('india','').strip().title()
                            if normalized not in ['North','South','East','West']:raise ValueError('invalid_region')
                            if normalized!=parsed['region']:
                                changes.append(dict(table=table,key=key,field='region',original=row['region'],replacement=normalized,rule='region_mapping'))
                                parsed['region']=normalized
                        if table!='customers':
                            if 'customer_id' in parsed and parsed['customer_id'] not in customer_ids:raise ValueError('orphan_customer')
                        if table=='subscription_periods':
                            if parsed['effective_from']>=parsed['effective_to']:raise ValueError('invalid_period')
                            if parsed['billing_months'] not in [1,12] or parsed['plan_tier'] not in ['Starter','Growth','Enterprise']:raise ValueError('invalid_contract')
                            if not 0<=parsed['discount_paise']<parsed['recurring_paise']:raise ValueError('invalid_discount')
                            if any(r['subscription_id']==parsed['subscription_id'] and parsed['effective_from']<r['effective_to'] and r['effective_from']<parsed['effective_to'] for r in records):raise ValueError('overlapping_period')
                        if table=='invoices':
                            if parsed['period_id'] not in periods:raise ValueError('orphan_period')
                            if periods[parsed['period_id']]['customer_id']!=parsed['customer_id']:raise ValueError('period_customer_mismatch')
                            components=sum(parsed[c] for c in ['recurring_paise','one_time_paise','tax_paise'])
                            if parsed['total_paise'] is None:
                                parsed['total_paise']=components
                                changes.append(dict(table=table,key=key,field='total_paise',original='',replacement=components,rule='authoritative_components'))
                            if parsed['total_paise']!=components:raise ValueError('invoice_component_mismatch')
                            if any(parsed[c]<0 for c in ['recurring_paise','one_time_paise','tax_paise']):raise ValueError('negative_invoice')
                            if parsed['service_from']>=parsed['service_to'] or parsed['due_date']<parsed['issue_date']:raise ValueError('invalid_invoice_dates')
                        if table=='payment_events':
                            if parsed['invoice_id'] not in invoice_ids:raise ValueError('orphan_invoice')
                            if parsed['event_type'] not in ['payment','refund','reversal'] or parsed['status'] not in ['succeeded','failed']:raise ValueError('invalid_payment_type')
                            if parsed['amount_paise']<0 or parsed['available_date']<parsed['event_date']:raise ValueError('invalid_payment')
                        if table=='customer_monthly_activity':
                            if parsed['entitled_users']<=0 or not 0<=parsed['active_users']<=parsed['entitled_users']:raise ValueError('invalid_usage')
                            if any(parsed[c]<0 for c in ['tickets_opened','tickets_resolved','unresolved_tickets','csat_responses']):raise ValueError('negative_activity')
                            if parsed['csat_score'] is not None and not 1<=parsed['csat_score']<=5:raise ValueError('invalid_csat')
                            if parsed['available_date']<parsed['month']:raise ValueError('invalid_availability')
                        records.append(parsed)
                    except (ValueError,KeyError,TypeError) as error:disposition='quarantined';reason=str(error)
                audit.append(dict(table=table,source_row=line,key=key,disposition=disposition,reason=reason,original_json=json.dumps(row,sort_keys=True)))
        accepted[table]=records
        counts=Counter(r['disposition'] for r in audit if r['table']==table)
        summary[table]=dict(input=len(raw),accepted=counts['accepted'],duplicate=counts['duplicate'],quarantined=counts['quarantined'])
        if sum(summary[table][k] for k in ['accepted','duplicate','quarantined'])!=len(raw):raise RuntimeError('Row reconciliation failed')
        write_csv(out/'clean'/f'{table}.csv',records,contract)
    write_csv(out/'audit/row_dispositions.csv',audit,['table','source_row','key','disposition','reason','original_json'])
    write_csv(out/'audit/transformations.csv',changes,['table','key','field','original','replacement','rule'])
    write_csv(out/'quarantine/records.csv',[r for r in audit if r['disposition']=='quarantined'],['table','source_row','key','disposition','reason','original_json'])
    json_write(out/'audit/quality.json',dict(tables=summary,transformations=len(changes),source_id=manifest['source_id'],unknown_financial_amounts='Missing totals recovered only when all authoritative components exist. Quarantine is excluded and counted.'))
    return accepted,audit
