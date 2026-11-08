"""Build a native PBIP report and TMSL semantic model from verified CSV exports.
Schemas: https://learn.microsoft.com/power-bi/developer/projects/projects-report
"""
from pathlib import Path
import json
import uuid
import pandas as pd
from revpulse.core import json_write,current_run

ROOT=Path(__file__).resolve().parents[1];DASH=ROOT/'dashboard';DATA=DASH/'data'
REPORT=DASH/'RevPulse.Report';MODEL=DASH/'RevPulse.SemanticModel'
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'

def literal(value):
    if isinstance(value,bool):value='true' if value else 'false'
    elif isinstance(value,str):value="'"+value.replace("'","''")+"'"
    else:value=str(value)+'D'
    return {'expr':{'Literal':{'Value':value}}}

def field(table,col,measure=False):return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':col}}
def projection(table,col,measure=False):return {'field':field(table,col,measure),'queryRef':table+'.'+col,'nativeQueryRef':col}

def visual(page,name,kind,x,y,w,h,title,roles):
    query={role:{'projections':[projection(*item) for item in items]} for role,items in roles.items()}
    v={'$schema':SCHEMA+'visualContainer/2.4.0/schema.json','name':name,'position':{'x':x,'y':y,'z':0,'width':w,'height':h,'tabOrder':y+x},'visual':{'visualType':kind,'query':{'queryState':query},'drillFilterOtherVisuals':True,'visualContainerObjects':{'title':[{'properties':{'show':literal(True),'text':literal(title),'fontSize':literal(12),'fontColor':{'solid':{'color':literal('#19324F')}}}}],'background':[{'properties':{'show':literal(True),'color':{'solid':{'color':literal('#FFFFFF')}},'transparency':literal(0)}}]}}}
    json_write(REPORT/'definition/pages'/page/'visuals'/name/'visual.json',v)

def main():
    run=current_run(ROOT);cfg=json.loads((run/'manifest.json').read_text())['configuration']
    pd.DataFrame({'plan_tier':['Starter','Growth','Enterprise','Inactive']}).to_csv(DATA/'dim_plan.csv',index=False)
    pd.DataFrame({'stage':['New','Expansion','Reactivation','Contraction','Churn'],'sort':[1,2,3,4,5]}).to_csv(DATA/'dim_bridge.csv',index=False)
    pd.read_csv(DATA/'churn_predictions.csv').head(20).to_csv(DATA/'top20_risk.csv',index=False)
    quality=json.loads((run/'audit/quality.json').read_text())
    pd.DataFrame([{'table_name':k,**v} for k,v in quality['tables'].items()]).to_csv(DATA/'quality_summary.csv',index=False)
    pd.DataFrame([{'cutoff':cfg['cutoff'],'run_id':run.name,'data_type':'Synthetic demonstration','definitions':'MRR excludes tax and one-time charges. High-risk MRR is exposure, not guaranteed loss.','coverage':'Quarantined records excluded; see quality table.','model':'Chronological test; synthetic performance does not establish real-world effectiveness.'}]).to_csv(DATA/'report_metadata.csv',index=False)
    sources={'Customers':'customers','Dates':'dim_date','Plans':'dim_plan','CustomerMonth':'mart_customer_month','Invoices':'mart_invoice_aging','Risk':'churn_predictions','TopRisk':'top20_risk','Anomalies':'billing_anomalies','Bridge':'dim_bridge','Quality':'quality_summary','Metadata':'report_metadata','Cohorts':'mart_cohort_retention'}
    tables=[]
    date_cols={'month','month_end','issue_date','due_date','service_from','service_to','cutoff','score_date','signup_date','cohort'}
    for name,file in sources.items():
        df=pd.read_csv(DATA/(file+'.csv'));columns=[];types=[]
        for col in df.columns:
            dtype='dateTime' if col in date_cols else 'int64' if pd.api.types.is_integer_dtype(df[col]) else 'double' if pd.api.types.is_numeric_dtype(df[col]) else 'string'
            columns.append({'name':col,'dataType':dtype,'sourceColumn':col,'summarizeBy':'none' if dtype in ['string','dateTime'] else 'sum',**({'formatString':'dd MMM yyyy'} if dtype=='dateTime' else {})})
            if col in ['churn_probability','usage_ratio','usage_change','retention','average_usage','nrr','customer_churn_rate']:columns[-1]['formatString']='0.0%'
            if col in ['mrr_inr','overdue_inr']:columns[-1]['formatString']='₹#,##0.00'
            types.append('{"'+col+'", '+{'dateTime':'type date','int64':'Int64.Type','double':'type number','string':'type text'}[dtype]+'}')
        expression=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "{file}.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source,[PromoteAllScalars=true]),','    Typed = Table.TransformColumnTypes(Headers,{'+','.join(types)+'},"en-US")','in','    Typed']
        tables.append({'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]})
    latest='VAR d = MAX(Dates[month]) RETURN '
    measures={
      'MRR INR':latest+'CALCULATE(SUM(CustomerMonth[mrr_paise])/100, Dates[month]=d)',
      'Active accounts':latest+'CALCULATE(DISTINCTCOUNT(CustomerMonth[customer_id]),Dates[month]=d,CustomerMonth[mrr_paise]>0)',
      'Opening MRR INR':latest+'CALCULATE(SUM(CustomerMonth[opening_mrr_paise])/100,Dates[month]=d)',
      'MoM growth':'DIVIDE([MRR INR]-[Opening MRR INR],[Opening MRR INR])',
      'NRR':latest+'DIVIDE(CALCULATE(SUM(CustomerMonth[mrr_paise]),Dates[month]=d,CustomerMonth[opening_mrr_paise]>0),CALCULATE(SUM(CustomerMonth[opening_mrr_paise]),Dates[month]=d))',
      'Customer churn':latest+'DIVIDE(CALCULATE(COUNTROWS(CustomerMonth),Dates[month]=d,CustomerMonth[movement]="Churn"),CALCULATE(COUNTROWS(CustomerMonth),Dates[month]=d,CustomerMonth[opening_mrr_paise]>0))',
      'ARPA INR':'DIVIDE([MRR INR],[Active accounts])',
      'Overdue INR':'CALCULATE(SUM(Invoices[outstanding_paise])/100,Invoices[days_overdue]>0)',
      'Outstanding INR':'SUM(Invoices[outstanding_paise])/100',
      'High-risk MRR INR':'CALCULATE(SUM(Risk[mrr_inr]),Risk[risk_category]="High")',
      'Billing flags':'DISTINCTCOUNT(Anomalies[record_id])',
      'Risk accounts':'CALCULATE(COUNTROWS(Risk),Risk[risk_category]="High")',
      'MRR change INR':latest+'VAR s = SELECTEDVALUE(Bridge[stage]) RETURN CALCULATE(SUMX(CustomerMonth,IF(s="Churn" || s="Contraction",CustomerMonth[mrr_paise]-CustomerMonth[opening_mrr_paise],IF(s="New" || s="Reactivation",CustomerMonth[mrr_paise],CustomerMonth[mrr_paise]-CustomerMonth[opening_mrr_paise])))/100,Dates[month]=d,CustomerMonth[movement]=s)',
    }
    for table in tables:
        if table['name']=='CustomerMonth':table['measures']=[{'name':name,'expression':expression,'formatString':'0.0%' if name in ['NRR','Customer churn','MoM growth'] else '₹#,##0; (₹#,##0)' if 'INR' in name else '#,##0'} for name,expression in measures.items()]
        if table['name']=='Bridge':table['columns'][0]['sortByColumn']='sort'
    relationships=[]
    for fact,key,dim,dkey in [('CustomerMonth','customer_id','Customers','customer_id'),('Invoices','customer_id','Customers','customer_id'),('Risk','customer_id','Customers','customer_id'),('TopRisk','customer_id','Customers','customer_id'),('Anomalies','customer_id','Customers','customer_id'),('CustomerMonth','month','Dates','month'),('CustomerMonth','plan_tier','Plans','plan_tier'),('Invoices','plan_tier','Plans','plan_tier'),('Risk','plan_tier','Plans','plan_tier'),('TopRisk','plan_tier','Plans','plan_tier')]:
        relationships.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,f'{fact}.{key}->{dim}.{dkey}')),'fromTable':fact,'fromColumn':key,'toTable':dim,'toColumn':dkey,'crossFilteringBehavior':'oneDirection'})
    folder=str(DATA).replace('\\','/')+'/'
    model={'name':'RevPulse','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','tables':tables,'relationships':relationships,'expressions':[{'name':'DataFolder','kind':'m','expression':'"'+folder+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(['DataFolder']+list(sources))}]}}
    json_write(MODEL/'model.bim',model);json_write(MODEL/'definition.pbism',{'version':'4.0','settings':{}})
    json_write(REPORT/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../RevPulse.SemanticModel'}}})
    json_write(DASH/'RevPulse.pbip',{'version':'1.0','artifacts':[{'report':{'path':'RevPulse.Report'}}],'settings':{'enableAutoRecovery':True}})
    json_write(REPORT/'definition/version.json',{'$schema':SCHEMA+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    json_write(REPORT/'definition/report.json',{'$schema':SCHEMA+'report/3.1.0/schema.json','themeCollection':{}})
    pages=[('revenue','Revenue and retention'),('actions','Collections and retention actions'),('audit','Definitions and data quality')]
    json_write(REPORT/'definition/pages/pages.json',{'$schema':SCHEMA+'pagesMetadata/1.0.0/schema.json','pageOrder':[p[0] for p in pages],'activePageName':'revenue'})
    for name,title in pages:json_write(REPORT/'definition/pages'/name/'page.json',{'$schema':SCHEMA+'page/2.0.0/schema.json','name':name,'displayName':title,'displayOption':'FitToPage','width':1440,'height':900})
    for i,(measure,title) in enumerate([('MRR INR','Month-end MRR'),('Active accounts','Active accounts'),('NRR','Net revenue retention'),('Customer churn','Customer churn rate')]):visual('revenue','card'+str(i),'card',20+i*350,20,330,135,title,{'Values':[('CustomerMonth',measure,True)]})
    for i,(table,col,title) in enumerate([('Dates','month','Reporting month'),('Customers','region','Region'),('Plans','plan_tier','Plan')]):visual('revenue','slicer'+str(i),'slicer',20+i*470,165,450,90,title,{'Values':[(table,col)]})
    visual('revenue','trend','lineChart',20,270,850,280,'Recurring revenue over time (INR)',{'Category':[('Dates','month')],'Y':[('CustomerMonth','MRR INR',True)]})
    visual('revenue','region','clusteredBarChart',890,270,530,280,'MRR by region (INR)',{'Category':[('Customers','region')],'Y':[('CustomerMonth','MRR INR',True)]})
    visual('revenue','bridge','waterfallChart',20,570,850,300,'MRR changes in the latest selected month (INR)',{'Category':[('Bridge','stage')],'Y':[('CustomerMonth','MRR change INR',True)]})
    visual('revenue','channel','clusteredBarChart',890,570,530,300,'MRR by acquisition channel (INR)',{'Category':[('Customers','acquisition_channel')],'Y':[('CustomerMonth','MRR INR',True)]})
    for i,(measure,title) in enumerate([('Overdue INR','Overdue balance'),('High-risk MRR INR','High-risk MRR exposure'),('Risk accounts','High-risk accounts'),('Billing flags','Billing investigation flags')]):visual('actions','card'+str(i),'card',20+i*350,20,330,130,title,{'Values':[('CustomerMonth',measure,True)]})
    visual('actions','region','slicer',20,160,450,80,'Region',{'Values':[('Customers','region')]})
    visual('actions','plan','slicer',490,160,450,80,'Plan',{'Values':[('Plans','plan_tier')]})
    visual('actions','aging','clusteredBarChart',20,255,530,255,'Outstanding balances by aging bucket (INR)',{'Category':[('Invoices','aging_bucket')],'Y':[('CustomerMonth','Outstanding INR',True)]})
    visual('actions','scatter','scatterChart',570,255,850,255,'Usage and MRR by current risk category',{'Category':[('Risk','company_name')],'X':[('Risk','usage_ratio')],'Y':[('Risk','mrr_inr')],'Series':[('Risk','risk_category')]})
    visual('actions','accounts','tableEx',20,530,1000,340,'Top 20 accounts by predicted risk (overall ranking)',{'Values':[('TopRisk',c) for c in ['company_name','churn_probability','risk_category','mrr_inr','overdue_inr','usage_change','score_date']]})
    visual('actions','exceptions','tableEx',1040,530,380,340,'Billing exceptions for investigation',{'Values':[('Anomalies',c) for c in ['record_id','rule','severity']]})
    visual('audit','quality','tableEx',20,20,900,300,'Source dispositions',{'Values':[('Quality',c) for c in ['table_name','input','accepted','duplicate','quarantined']]})
    visual('audit','metadata','tableEx',20,340,1400,220,'Reporting scope and definitions',{'Values':[('Metadata',c) for c in ['cutoff','data_type','definitions','coverage','model']]})
    visual('audit','cohort','tableEx',20,580,900,280,'Paid activation cohorts; unobserved future retention is blank',{'Values':[('Cohorts',c) for c in ['cohort','age','cohort_size','retention']]})
    (DASH/'measures.md').write_text('# Power BI measures\n\n'+ '\n\n'.join(f'## {name}\n\n```dax\n{expr}\n```' for name,expr in measures.items()),encoding='utf-8')
    print(DASH/'RevPulse.pbip')

if __name__=='__main__':main()
