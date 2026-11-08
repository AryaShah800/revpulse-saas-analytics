# Power BI measures

## MRR INR

```dax
VAR d = MAX(Dates[month]) RETURN CALCULATE(SUM(CustomerMonth[mrr_paise])/100, Dates[month]=d)
```

## Active accounts

```dax
VAR d = MAX(Dates[month]) RETURN CALCULATE(DISTINCTCOUNT(CustomerMonth[customer_id]),Dates[month]=d,CustomerMonth[mrr_paise]>0)
```

## Opening MRR INR

```dax
VAR d = MAX(Dates[month]) RETURN CALCULATE(SUM(CustomerMonth[opening_mrr_paise])/100,Dates[month]=d)
```

## MoM growth

```dax
DIVIDE([MRR INR]-[Opening MRR INR],[Opening MRR INR])
```

## NRR

```dax
VAR d = MAX(Dates[month]) RETURN DIVIDE(CALCULATE(SUM(CustomerMonth[mrr_paise]),Dates[month]=d,CustomerMonth[opening_mrr_paise]>0),CALCULATE(SUM(CustomerMonth[opening_mrr_paise]),Dates[month]=d))
```

## Customer churn

```dax
VAR d = MAX(Dates[month]) RETURN DIVIDE(CALCULATE(COUNTROWS(CustomerMonth),Dates[month]=d,CustomerMonth[movement]="Churn"),CALCULATE(COUNTROWS(CustomerMonth),Dates[month]=d,CustomerMonth[opening_mrr_paise]>0))
```

## ARPA INR

```dax
DIVIDE([MRR INR],[Active accounts])
```

## Overdue INR

```dax
CALCULATE(SUM(Invoices[outstanding_paise])/100,Invoices[days_overdue]>0)
```

## Outstanding INR

```dax
SUM(Invoices[outstanding_paise])/100
```

## High-risk MRR INR

```dax
CALCULATE(SUM(Risk[mrr_inr]),Risk[risk_category]="High")
```

## Billing flags

```dax
DISTINCTCOUNT(Anomalies[record_id])
```

## Risk accounts

```dax
CALCULATE(COUNTROWS(Risk),Risk[risk_category]="High")
```

## MRR change INR

```dax
VAR d = MAX(Dates[month]) RETURN VAR s = SELECTEDVALUE(Bridge[stage]) RETURN CALCULATE(SUMX(CustomerMonth,IF(s="Churn" || s="Contraction",CustomerMonth[mrr_paise]-CustomerMonth[opening_mrr_paise],IF(s="New" || s="Reactivation",CustomerMonth[mrr_paise],CustomerMonth[mrr_paise]-CustomerMonth[opening_mrr_paise])))/100,Dates[month]=d,CustomerMonth[movement]=s)
```