import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .core import json_write

def analyze(run,root):
    out=run/'analytics';out.mkdir(exist_ok=True)
    invoices=pd.read_csv(run/'clean/invoices.csv')
    periods=pd.read_csv(run/'clean/subscription_periods.csv')
    joined=invoices.merge(periods[['period_id','plan_tier','billing_months']],on='period_id',validate='many_to_one')
    flags=[]
    for (tier,interval),group in joined.groupby(['plan_tier','billing_months']):
        if len(group)<20:continue
        q1,q3=group.recurring_paise.quantile([.25,.75]);iqr=q3-q1
        if iqr==0:continue
        lower=max(0,q1-1.5*iqr);upper=q3+1.5*iqr
        for row in group[(group.recurring_paise>upper)|(group.recurring_paise<lower)].itertuples():
            flags.append(dict(record_id=row.invoice_id,customer_id=row.customer_id,rule='peer_group_iqr',observed_paise=row.recurring_paise,expected_paise=upper,severity='Review',review_status='Open'))
    business=pd.read_csv(run/'marts/mart_billing_exceptions.csv')
    all_flags=pd.concat([business,pd.DataFrame(flags)],ignore_index=True)
    all_flags.to_csv(out/'billing_anomalies.csv',index=False)
    activity=pd.read_csv(run/'clean/customer_monthly_activity.csv').sort_values(['customer_id','month'])
    activity['prior_mean']=activity.groupby('customer_id').tickets_opened.transform(lambda s:s.shift(1).rolling(6,min_periods=3).mean())
    activity['prior_std']=activity.groupby('customer_id').tickets_opened.transform(lambda s:s.shift(1).rolling(6,min_periods=3).std())
    activity['support_zscore']=(activity.tickets_opened-activity.prior_mean)/activity.prior_std.replace(0,np.nan)
    activity[activity.support_zscore>3].to_csv(out/'support_spikes.csv',index=False)
    manifest=json.loads((run/'manifest.json').read_text())
    source_id=PathLike(manifest['source'])
    defects=json.loads((root/'data/reference'/source_id/'defects.json').read_text())
    dispositions=pd.read_csv(run/'audit/row_dispositions.csv')
    evaluation=[]
    for defect in defects:
        matching=dispositions[(dispositions.table==defect['table'])&(dispositions.key==defect['key'])]
        evaluation.append(dict(table=defect['table'],key=defect['key'],kind=defect['kind'],quarantined=bool((matching.disposition=='quarantined').any()),duplicate_detected=bool((matching.disposition=='duplicate').any()),anomaly_flagged=bool((all_flags.record_id==defect['key']).any())))
    expected_business={d['key'] for d in defects if d['kind']=='contract_mismatch'}
    found_business=set(business.record_id)
    transforms=pd.read_csv(run/'audit/transformations.csv')
    for row in evaluation:
        row['transformed']=bool(((transforms.table==row['table'])&(transforms.key==row['key'])).any())
        row['handled']=row['quarantined'] or row['duplicate_detected'] or row['anomaly_flagged'] or row['transformed']
    found_statistical={r['record_id'] for r in flags}
    json_write(out/'defect_evaluation.json',dict(injected=evaluation,statistical_flags=len(flags),business_flags=len(business),business_rule_evaluation={'true_positives':len(found_business&expected_business),'false_positives':len(found_business-expected_business),'false_negatives':len(expected_business-found_business)},statistical_error_detection_evaluation={'true_positives':len(found_statistical&expected_business),'false_positives':len(found_statistical-expected_business),'false_negatives':len(expected_business-found_statistical),'scope':'Accepted invoices only. Treating IQR as an error detector produces false positives on valid simulated add-ons; flags remain investigation candidates.'},note='Statistical flags are investigation candidates; they are not removed. Defect manifest is used for evaluation only.'))
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False})
    monthly=pd.read_csv(run/'marts/mart_revenue_month.csv')
    fig,ax=plt.subplots(figsize=(11,4));ax.plot(pd.to_datetime(monthly.month),monthly.closing_mrr_paise/10000000,color='#255EA8',linewidth=2.5)
    ax.set(title='Month-end recurring revenue',ylabel='MRR (INR lakh)',xlabel='Month');ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(out/'mrr_trend.png',dpi=150);plt.close(fig)
    return all_flags

def PathLike(value):
    return value.replace('\\','/').rstrip('/').split('/')[-1]
