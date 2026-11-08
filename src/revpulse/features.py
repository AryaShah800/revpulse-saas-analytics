"""Features computed from dated observations available at each score cutoff."""
import pandas as pd
import numpy as np

NUMERIC=['usage_ratio','usage_change','tickets_opened','unresolved_tickets','csat_score','csat_missing','tenure_months','mrr_inr','overdue_inr','average_delay_days']
CATEGORICAL=['plan_tier']

def load_frames(run):
    frames={name:pd.read_csv(run/'clean'/f'{name}.csv') for name in ['customers','subscription_periods','invoices','payment_events','customer_monthly_activity']}
    for name,cols in {'customers':['signup_date'],'subscription_periods':['effective_from','effective_to'],'invoices':['issue_date','due_date'],'payment_events':['event_date','available_date'],'customer_monthly_activity':['month','available_date']}.items():
        for col in cols:frames[name][col]=pd.to_datetime(frames[name][col])
    return frames

def make_features(frames,months,observation_end):
    customers=frames['customers'];periods=frames['subscription_periods'];invoices=frames['invoices'];payments=frames['payment_events'];activity=frames['customer_monthly_activity']
    outputs=[]
    for month in months:
        month=pd.Timestamp(month);cutoff=month+pd.offsets.MonthEnd(0);following_end=cutoff+pd.offsets.MonthEnd(1)
        active=periods[(periods.effective_from<=cutoff)&(periods.effective_to>cutoff)].copy()
        if active.empty:continue
        active['mrr_inr']=(active.recurring_paise-active.discount_paise)/active.billing_months/100
        mrr=active.groupby('customer_id').mrr_inr.sum()
        plan=active.sort_values(['mrr_inr','period_id'],ascending=[False,True]).drop_duplicates('customer_id').set_index('customer_id').plan_tier
        out=customers[customers.customer_id.isin(mrr.index)].set_index('customer_id').copy()
        out['mrr_inr']=mrr;out['plan_tier']=plan;out['score_date']=cutoff
        out['tenure_months']=(cutoff.year-out.signup_date.dt.year)*12+cutoff.month-out.signup_date.dt.month
        known=activity[(activity.available_date<=cutoff)&(activity.month<=month)].copy()
        known['usage_ratio']=known.active_users/known.entitled_users
        known=known.sort_values(['customer_id','month','record_id'])
        known['previous_usage']=known.groupby('customer_id').usage_ratio.shift(1)
        latest=known.drop_duplicates('customer_id',keep='last').set_index('customer_id')
        for col in ['usage_ratio','tickets_opened','unresolved_tickets','csat_score']:out[col]=latest[col]
        out['usage_change']=out.usage_ratio-latest.previous_usage
        out['csat_missing']=out.csat_score.isna().astype(int)
        inv=invoices[invoices.issue_date<=cutoff].copy()
        pay=payments[(payments.available_date<=cutoff)&(payments.event_date<=cutoff)&(payments.status=='succeeded')].copy()
        pay['signed']=np.where(pay.event_type=='payment',pay.amount_paise,-pay.amount_paise)
        inv['paid']=inv.invoice_id.map(pay.groupby('invoice_id').signed.sum()).fillna(0)
        inv['overdue']=np.where(inv.due_date<cutoff,np.maximum(inv.total_paise-inv.paid,0),0)
        out['overdue_inr']=inv.groupby('customer_id').overdue.sum().reindex(out.index).fillna(0)/100
        recent=pay[(pay.event_type=='payment')&(pay.event_date>cutoff-pd.Timedelta(days=90))].merge(inv[['invoice_id','customer_id','due_date']],on='invoice_id')
        recent['delay']=(recent.event_date-recent.due_date).dt.days
        out['average_delay_days']=recent.groupby('customer_id').delay.mean()
        # Labels use future lifecycle events, never exposed to predictors.
        if following_end<=pd.Timestamp(observation_end):
            ends=periods[(periods.effective_to>cutoff)&(periods.effective_to<=following_end)]
            churn_ids=set()
            for end_date,events in ends.groupby('effective_to'):
                still_active=set(periods[(periods.effective_from<=end_date)&(periods.effective_to>end_date)].customer_id)
                churn_ids.update(set(events.customer_id)-still_active)
            out['is_churned']=out.index.isin(churn_ids).astype(int)
        else:out['is_churned']=np.nan
        outputs.append(out.reset_index()[['customer_id','company_name','region','acquisition_channel','score_date']+NUMERIC+CATEGORICAL+['is_churned']])
    return pd.concat(outputs,ignore_index=True) if outputs else pd.DataFrame(columns=['customer_id','score_date']+NUMERIC+CATEGORICAL+['is_churned'])
