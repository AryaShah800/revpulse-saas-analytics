"""Author and execute reproducible notebooks using the current published run."""
from pathlib import Path
import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
setup="""from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from revpulse.core import current_run
root=Path.cwd().parent if Path.cwd().name=='notebooks' else Path.cwd()
run=current_run(root)
print('Run:',run.name)
"""
eda=nbf.v4.new_notebook(cells=[
 nbf.v4.new_markdown_cell('# RevPulse data quality and exploratory analysis\n\nSynthetic SaaS data. Monetary source fields are integer paise. Invoicing, collections and MRR are separate metrics. No causal conclusions are drawn.'),
 nbf.v4.new_code_cell(setup),
 nbf.v4.new_code_cell("quality=json.loads((run/'audit/quality.json').read_text())\npd.DataFrame(quality['tables']).T"),
 nbf.v4.new_code_cell("pd.read_csv(run/'audit/transformations.csv')"),
 nbf.v4.new_code_cell("pd.read_csv(run/'quarantine/records.csv')[['table','key','reason']].head(15)"),
 nbf.v4.new_markdown_cell('## Financial controls\nThe SQL totals below are reconciled against independent Python arithmetic. Annual charges are normalized for MRR; taxes and one-time fees stay in invoicing.'),
 nbf.v4.new_code_cell("json.loads((run/'audit/reconciliation.json').read_text())"),
 nbf.v4.new_code_cell("monthly=pd.read_csv(run/'marts/mart_revenue_month.csv')\nax=monthly.assign(month=pd.to_datetime(monthly.month),mrr_inr=monthly.closing_mrr_paise/100).plot(x='month',y='mrr_inr',figsize=(11,4),legend=False,title='Month-end MRR (INR)'); ax.set_ylabel('INR'); plt.show()"),
 nbf.v4.new_code_cell("pd.read_csv(run/'queries/regional_channel_performance.csv')"),
 nbf.v4.new_markdown_cell('## Billing investigation\nIQR flags compare plan and billing-interval peers. A statistical flag does not establish a billing error. Sparse groups and zero-IQR groups are skipped. Contract mismatches use explicit invoice-versus-contract checks.'),
 nbf.v4.new_code_cell("pd.read_csv(run/'analytics/billing_anomalies.csv').head(15)"),
 nbf.v4.new_code_cell("json.loads((run/'analytics/defect_evaluation.json').read_text())"),
 nbf.v4.new_markdown_cell('## Exploratory hypothesis\nAt one fixed month, do accounts that churn during the following month have different recent payment delays? Using one snapshot avoids treating repeated customer-months as independent observations. This is observational and exploratory, with no causal interpretation.'),
 nbf.v4.new_code_cell("features=pd.read_csv(run/'analytics/customer_features.csv')\nobserved=features[features.is_churned.notna()]\ndates=sorted(observed.score_date.unique()); snapshot=observed[observed.score_date==dates[-6]].copy()\nprint('Fixed snapshot:',dates[-6], 'accounts:',len(snapshot))\nsns.heatmap(snapshot[['usage_ratio','usage_change','average_delay_days','tickets_opened','csat_score','is_churned']].corr(),annot=True,fmt='.2f',vmin=-1,vmax=1,cmap='coolwarm'); plt.title('Exploratory correlations: one account per row'); plt.show()"),
 nbf.v4.new_code_cell("from scipy.stats import mannwhitneyu\na=snapshot.loc[snapshot.is_churned==1,'average_delay_days'].dropna().to_numpy()\nb=snapshot.loc[snapshot.is_churned==0,'average_delay_days'].dropna().to_numpy()\nif len(a) and len(b):\n    result=mannwhitneyu(a,b,alternative='two-sided')\n    rng=np.random.default_rng(42)\n    boot=[np.median(rng.choice(a,len(a)))-np.median(rng.choice(b,len(b))) for _ in range(1000)]\n    finding={'churned_n':len(a),'retained_n':len(b),'median_delay_difference_days':float(np.median(a)-np.median(b)),'bootstrap_95pct_interval':np.quantile(boot,[.025,.975]).tolist(),'mann_whitney_p':float(result.pvalue),'rank_biserial_effect':float(2*result.statistic/(len(a)*len(b))-1)}\n    (run/'analytics/hypothesis_result.json').write_text(json.dumps(finding,indent=2))\n    display(finding)\nelse:\n    print('Insufficient observed classes; no test reported.')"),
 nbf.v4.new_markdown_cell('Missing delay values are excluded from the hypothesis test and their counts remain visible in the sample sizes. The bootstrap resamples accounts within outcome groups. Simulation assumptions and a single chosen month limit generalization.')])
model=nbf.v4.new_notebook(cells=[
 nbf.v4.new_markdown_cell('# RevPulse churn evaluation\n\nThis notebook reports the saved, once-evaluated chronological holdout. It does not tune on the test set.'),
 nbf.v4.new_code_cell(setup),
 nbf.v4.new_code_cell("evaluation=json.loads((run/'analytics/model_evaluation.json').read_text())\npd.DataFrame(evaluation['splits']).T"),
 nbf.v4.new_code_cell("pd.DataFrame(evaluation['validation']).T[['pr_auc','precision','recall','f1','brier']]"),
 nbf.v4.new_code_cell("print('Selected:',evaluation['selected_model'],'threshold:',evaluation['threshold'])\npd.DataFrame({'selected':evaluation['test'],**evaluation['baselines']}).T[['pr_auc','precision','recall','f1','brier']]"),
 nbf.v4.new_code_cell("sns.heatmap(evaluation['test']['confusion_matrix'],annot=True,fmt='d',cmap='Blues',xticklabels=['Retained','Churn'],yticklabels=['Retained','Churn']); plt.xlabel('Predicted');plt.ylabel('Observed');plt.title('Held-out confusion matrix');plt.show()"),
 nbf.v4.new_code_cell("cal=evaluation['calibration'];plt.plot(cal['mean_probability'],cal['observed_frequency'],'o-',label='Model');plt.plot([0,1],[0,1],'--',color='gray',label='Ideal');plt.xlabel('Predicted probability');plt.ylabel('Observed churn frequency');plt.title('Held-out calibration');plt.legend();plt.show()"),
 nbf.v4.new_code_cell("pd.DataFrame(evaluation['campaigns'])[['score_date','k','precision_at_k','recall_at_k','prevalence']]"),
 nbf.v4.new_code_cell("scores=pd.read_csv(run/'analytics/churn_predictions.csv');scores[['company_name','churn_probability','risk_category','mrr_inr','overdue_inr','usage_change','score_date']].head(20)"),
 nbf.v4.new_markdown_cell('## Limitations\nSynthetic data demonstrates the pipeline, not validated commercial prediction. Existing accounts recur across chronological splits; unseen-account generalization is not evaluated. High-risk MRR is exposure, not expected loss. Current scores use the selected training-only model to preserve the documented evaluation; there is no silent retraining on held-out labels.')])
for name,notebook in [('01_data_quality_and_eda',eda),('02_churn_evaluation',model)]:
    notebook.metadata['kernelspec']={'display_name':'Python (RevPulse)','language':'python','name':'revpulse'}
    output=ROOT/'notebooks'/f'{name}.ipynb'
    nbf.write(notebook,output)
    NotebookClient(notebook,timeout=180,kernel_name='revpulse',resources={'metadata':{'path':str(ROOT)}}).execute()
    nbf.write(notebook,output)
    print('Executed',output.name)
