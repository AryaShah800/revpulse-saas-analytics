"""Chronological baseline comparison, evaluation and versioned scoring."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score,precision_score,recall_score,f1_score,confusion_matrix,brier_score_loss
from sklearn.calibration import calibration_curve
from .core import json_write,VERSION
from .features import NUMERIC,CATEGORICAL,load_frames,make_features

def metrics(y,p,threshold,k=20):
    pred=np.asarray(p)>=threshold;y=np.asarray(y,dtype=int)
    # Capacity is applied separately to each month's campaign by caller.
    k=min(k,len(y));selected=np.argsort(-np.asarray(p),kind='stable')[:k]
    return dict(pr_auc=float(average_precision_score(y,p)),precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred,zero_division=0)),f1=float(f1_score(y,pred,zero_division=0)),brier=float(brier_score_loss(y,p)),confusion_matrix=confusion_matrix(y,pred,labels=[0,1]).tolist(),precision_at_k=float(y[selected].mean()),recall_at_k=float(y[selected].sum()/max(y.sum(),1)),k=k,prevalence=float(y.mean()),rows=len(y))

def train(run,root):
    manifest=json.loads((run/'manifest.json').read_text());cfg=manifest['configuration']
    months=pd.date_range(cfg['start'],periods=cfg['months'],freq='MS')
    features=make_features(load_frames(run),months,cfg['cutoff'])
    output=run/'analytics';output.mkdir(exist_ok=True)
    features.to_csv(output/'customer_features.csv',index=False)
    observed=features[features.is_churned.notna()].copy()
    if len(months)<18:raise ValueError('At least 18 months required for chronological model evaluation')
    train_boundary=months[int(len(months)*2/3)]
    test_boundary=months[int(len(months)*5/6)]
    # Train labels end before first validation scoring date; validation labels end before first test scoring date.
    training=observed[observed.score_date<train_boundary]
    validation=observed[(observed.score_date>=train_boundary)&(observed.score_date<test_boundary)]
    test=observed[observed.score_date>=test_boundary]
    for label,part in [('training',training),('validation',validation),('test',test)]:
        if part.is_churned.nunique()<2:raise ValueError(f'{label} requires both classes; increase generated accounts/months')
    numeric=Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True)),('scale',StandardScaler())])
    prep=ColumnTransformer([('numeric',numeric,NUMERIC),('categorical',OneHotEncoder(handle_unknown='ignore'),CATEGORICAL)])
    candidates={'logistic_regression':LogisticRegression(max_iter=1000,random_state=42),'random_forest':RandomForestClassifier(n_estimators=200,min_samples_leaf=15,max_depth=8,n_jobs=-1,random_state=42)}
    fitted={};validation_results={};thresholds={}
    for name,estimator in candidates.items():
        from sklearn.base import clone
        model=Pipeline([('preprocessing',clone(prep)),('classifier',estimator)])
        model.fit(training[NUMERIC+CATEGORICAL],training.is_churned.astype(int))
        p=model.predict_proba(validation[NUMERIC+CATEGORICAL])[:,1]
        threshold=max(np.linspace(.01,.5,100),key=lambda t:f1_score(validation.is_churned,p>=t,zero_division=0))
        fitted[name]=model;thresholds[name]=float(threshold);validation_results[name]=metrics(validation.is_churned,p,threshold)
    selected=max(validation_results,key=lambda n:validation_results[n]['pr_auc'])
    model=fitted[selected];threshold=thresholds[selected]
    probability=model.predict_proba(test[NUMERIC+CATEGORICAL])[:,1]
    evaluation=metrics(test.is_churned,probability,threshold)
    campaigns=[]
    for score_date,group in test.assign(probability=probability).groupby('score_date'):
        campaigns.append({'score_date':str(score_date.date()),**metrics(group.is_churned,group.probability,threshold)})
    rule=((test.usage_ratio<.4)|(test.average_delay_days>20)).astype(float)*.8+.1
    prevalence=np.full(len(test),training.is_churned.mean())
    frac,mean=calibration_curve(test.is_churned,probability,n_bins=8,strategy='quantile')
    report=dict(selected_model=selected,threshold=threshold,validation=validation_results,test=evaluation,campaigns=campaigns,
        baselines={'prevalence':metrics(test.is_churned,prevalence,.5),'operational_rule':metrics(test.is_churned,rule,.5)},
        calibration={'mean_probability':mean.tolist(),'observed_frequency':frac.tolist()},
        splits={name:{'first':str(part.score_date.min().date()),'last':str(part.score_date.max().date()),'rows':len(part),'churns':int(part.is_churned.sum())} for name,part in [('train',training),('validation',validation),('test',test)]},
        limitations=['Synthetic simulation; scores do not prove real-world effectiveness.','Existing accounts recur across time splits; unseen-account generalization is not measured.','Indicators are associations, not causal explanations.'])
    json_write(output/'model_evaluation.json',report)
    test.assign(probability=probability).to_csv(output/'heldout_predictions.csv',index=False)
    artifact=dict(model=model,threshold=threshold,version=VERSION,selected=selected,training_run=manifest['run_id'])
    joblib.dump(artifact,output/'churn_model.joblib')
    (root/'models').mkdir(exist_ok=True)
    joblib.dump(artifact,root/'models/churn_model.joblib')
    score(run,root,features)
    return report

def score(run,root,features=None):
    cfg=json.loads((run/'manifest.json').read_text())['configuration']
    artifact=joblib.load(root/'models/churn_model.joblib')
    if features is None:features=make_features(load_frames(run),[pd.Timestamp(cfg['cutoff']).replace(day=1)],cfg['cutoff'])
    latest=features[features.score_date==features.score_date.max()].copy()
    latest['churn_probability']=artifact['model'].predict_proba(latest[NUMERIC+CATEGORICAL])[:,1]
    latest['risk_category']=np.where(latest.churn_probability>=artifact['threshold'],'High',np.where(latest.churn_probability>=artifact['threshold']/2,'Medium','Low'))
    latest['model_version']=artifact['version'];latest['model_training_run']=artifact['training_run']
    latest=latest.drop(columns=['is_churned']).sort_values(['churn_probability','customer_id'],ascending=[False,True])
    if latest.customer_id.duplicated().any() or not latest.churn_probability.between(0,1).all():raise ValueError('Invalid score output')
    (run/'analytics').mkdir(exist_ok=True)
    latest.to_csv(run/'analytics/churn_predictions.csv',index=False)
    return latest
