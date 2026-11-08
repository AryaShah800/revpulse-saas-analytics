from pathlib import Path
import json
import math
import pandas as pd
from revpulse.core import current_run,digest,json_write,CONTRACTS

root=Path(__file__).resolve().parents[1]
other=Path('D:/RevPulseRuntime/verification')
left=current_run(root);right=current_run(other)
checks={}
for table in CONTRACTS:
    checks['clean_'+table]=digest(left/'clean'/f'{table}.csv')==digest(right/'clean'/f'{table}.csv')
for file in (left/'marts').glob('*.csv'):
    a=pd.read_csv(file).astype(str);b=pd.read_csv(right/'marts'/file.name).astype(str)
    a=a.sort_values(list(a.columns)).reset_index(drop=True);b=b.sort_values(list(b.columns)).reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b)
    checks[file.stem]=True
a=pd.read_csv(left/'analytics/churn_predictions.csv').drop(columns=['model_training_run'])
b=pd.read_csv(right/'analytics/churn_predictions.csv').drop(columns=['model_training_run'])
pd.testing.assert_frame_equal(a,b,rtol=1e-10,atol=1e-10)
checks['churn_predictions']=True
def equivalent(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    return a==b
checks['model_metrics']=equivalent(json.loads((left/'analytics/model_evaluation.json').read_text()),json.loads((right/'analytics/model_evaluation.json').read_text()))
if not all(checks.values()):raise ValueError(checks)
json_write(root/'reports/reproducibility.json',dict(status='passed',primary_run=left.name,independent_run=right.name,checks=checks,numeric_tolerance='1e-12 for evaluation metrics; parallel forest accumulation differs at approximately 1e-18. Scores compared at 1e-10. Source CSVs and sorted SQL marts match exactly.',scope='Separate source checkout and virtual environment; shared local PostgreSQL server with isolated per-run schemas. Native Excel and Power BI validation deferred by user.'))
print('Independent environment reproduced clean data, all marts, model metrics and current scores')
