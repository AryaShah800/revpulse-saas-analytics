CREATE TABLE dim_date AS
SELECT d::date AS month,(d+interval '1 month'-interval '1 day')::date AS month_end
FROM run_config,generate_series(start_date,date_trunc('month',cutoff),interval '1 month') d;
CREATE TABLE fact_subscription_month AS
SELECT d.month,d.month_end,s.period_id,s.subscription_id,s.customer_id,s.plan_tier,
 (s.recurring_paise-s.discount_paise)::numeric/s.billing_months AS mrr_paise
FROM dim_date d JOIN subscription_periods s ON s.effective_from<=d.month_end AND s.effective_to>d.month_end;
CREATE INDEX subscription_month_customer ON fact_subscription_month(customer_id,month);
CREATE TABLE mart_customer_month AS
WITH base AS (
 SELECT c.customer_id,c.company_name,c.region,c.acquisition_channel,d.month,d.month_end,
 COALESCE(sum(f.mrr_paise),0) AS mrr_paise,
 COALESCE((array_agg(f.plan_tier ORDER BY f.mrr_paise DESC,f.period_id) FILTER(WHERE f.period_id IS NOT NULL))[1],
 (SELECT prior.plan_tier FROM fact_subscription_month prior WHERE prior.customer_id=c.customer_id AND prior.month<d.month ORDER BY prior.month DESC,prior.mrr_paise DESC,prior.period_id LIMIT 1),'Inactive') AS plan_tier
 FROM customers c CROSS JOIN dim_date d LEFT JOIN fact_subscription_month f ON f.customer_id=c.customer_id AND f.month=d.month
 WHERE c.signup_date<=d.month_end GROUP BY c.customer_id,c.company_name,c.region,c.acquisition_channel,d.month,d.month_end
), lagged AS (
 SELECT *,COALESCE(lag(mrr_paise) OVER(PARTITION BY customer_id ORDER BY month),0) AS opening_mrr_paise,
 COALESCE(max(mrr_paise) OVER(PARTITION BY customer_id ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) AS historical_max FROM base
)
SELECT *,CASE WHEN opening_mrr_paise=0 AND mrr_paise>0 AND historical_max=0 THEN 'New'
 WHEN opening_mrr_paise=0 AND mrr_paise>0 THEN 'Reactivation'
 WHEN opening_mrr_paise>0 AND mrr_paise=0 THEN 'Churn'
 WHEN mrr_paise>opening_mrr_paise THEN 'Expansion'
 WHEN mrr_paise<opening_mrr_paise THEN 'Contraction' ELSE 'Unchanged' END AS movement FROM lagged;
CREATE TABLE mart_revenue_month AS
SELECT month,max(month_end) month_end,sum(opening_mrr_paise) opening_mrr_paise,sum(mrr_paise) closing_mrr_paise,
 sum(CASE WHEN movement='New' THEN mrr_paise ELSE 0 END) new_mrr_paise,
 sum(CASE WHEN movement='Reactivation' THEN mrr_paise ELSE 0 END) reactivation_mrr_paise,
 sum(CASE WHEN movement='Expansion' THEN mrr_paise-opening_mrr_paise ELSE 0 END) expansion_mrr_paise,
 sum(CASE WHEN movement='Contraction' THEN opening_mrr_paise-mrr_paise ELSE 0 END) contraction_mrr_paise,
 sum(CASE WHEN movement='Churn' THEN opening_mrr_paise ELSE 0 END) churned_mrr_paise,
 count(*) FILTER(WHERE mrr_paise>0) active_accounts,count(*) FILTER(WHERE opening_mrr_paise>0) opening_accounts,
 count(*) FILTER(WHERE movement='Churn') churned_accounts,
 sum(mrr_paise) FILTER(WHERE opening_mrr_paise>0)/NULLIF(sum(opening_mrr_paise),0) nrr,
 count(*) FILTER(WHERE movement='Churn')::numeric/NULLIF(count(*) FILTER(WHERE opening_mrr_paise>0),0) customer_churn_rate
FROM mart_customer_month GROUP BY month ORDER BY month;
-- Keep complete calendar coverage even when no customers exist yet.
INSERT INTO mart_revenue_month
SELECT d.month,d.month_end,0,0,0,0,0,0,0,0,0,0,NULL,NULL
FROM dim_date d WHERE NOT EXISTS (SELECT 1 FROM mart_revenue_month r WHERE r.month=d.month);
CREATE TABLE mart_invoice_aging AS
WITH paid AS (
 SELECT p.invoice_id,sum(CASE WHEN p.event_type='payment' THEN p.amount_paise ELSE -p.amount_paise END) net_paid_paise
 FROM payment_events p CROSS JOIN run_config r WHERE p.status='succeeded' AND p.event_date<=r.cutoff AND p.available_date<=r.cutoff GROUP BY p.invoice_id
), balances AS (
 SELECT i.*,c.region,c.acquisition_channel,s.plan_tier,r.cutoff,COALESCE(p.net_paid_paise,0) net_paid_paise,
 greatest(i.total_paise-COALESCE(p.net_paid_paise,0),0) outstanding_paise,
 greatest(COALESCE(p.net_paid_paise,0)-i.total_paise,0) credit_paise,
 CASE WHEN i.total_paise>COALESCE(p.net_paid_paise,0) THEN greatest(r.cutoff-i.due_date,0) ELSE 0 END days_overdue
 FROM invoices i JOIN customers c USING(customer_id) JOIN subscription_periods s USING(period_id)
 CROSS JOIN run_config r LEFT JOIN paid p USING(invoice_id) WHERE i.issue_date<=r.cutoff
)
SELECT *,CASE WHEN outstanding_paise=0 THEN 'Paid' WHEN days_overdue=0 THEN 'Current'
 WHEN days_overdue<=15 THEN '1-15' WHEN days_overdue<=30 THEN '16-30'
 WHEN days_overdue<=60 THEN '31-60' ELSE '61+' END aging_bucket FROM balances;
CREATE TABLE mart_collections_month AS
SELECT d.month,COALESCE(sum(CASE WHEN p.status='succeeded' THEN CASE WHEN p.event_type='payment' THEN p.amount_paise ELSE -p.amount_paise END ELSE 0 END),0) net_collections_paise
FROM dim_date d LEFT JOIN payment_events p ON p.event_date>=d.month AND p.event_date<d.month+interval '1 month'
AND p.available_date<=(SELECT cutoff FROM run_config) GROUP BY d.month;
CREATE TABLE mart_payment_delay AS
SELECT p.event_id,p.invoice_id,i.customer_id,s.plan_tier,c.region,p.event_date,i.due_date,p.event_date-i.due_date AS delay_days,p.amount_paise
FROM payment_events p JOIN invoices i USING(invoice_id) JOIN subscription_periods s USING(period_id) JOIN customers c ON c.customer_id=i.customer_id
WHERE p.status='succeeded' AND p.event_type='payment'
AND p.event_date<=(SELECT cutoff FROM run_config) AND p.available_date<=(SELECT cutoff FROM run_config);
CREATE TABLE mart_billing_exceptions AS
SELECT i.invoice_id AS record_id,i.customer_id,'contract_charge_mismatch'::text AS rule,
 i.recurring_paise AS observed_paise,s.recurring_paise-s.discount_paise AS expected_paise,
 'High'::text severity,'Open'::text review_status FROM invoices i JOIN subscription_periods s USING(period_id)
WHERE i.recurring_paise<>s.recurring_paise-s.discount_paise AND i.issue_date<=(SELECT cutoff FROM run_config);
CREATE TABLE mart_cohort_retention AS
WITH first_active AS (SELECT customer_id,min(month) cohort FROM mart_customer_month WHERE mrr_paise>0 GROUP BY customer_id),
grid AS (SELECT f.customer_id,f.cohort,n.age,(f.cohort+make_interval(months=>n.age))::date AS month FROM first_active f CROSS JOIN generate_series(0,12) n(age))
SELECT g.cohort,g.age,count(*) cohort_size,
CASE WHEN max(g.month)>(SELECT max(month) FROM dim_date) THEN NULL ELSE count(*) FILTER(WHERE m.mrr_paise>0)::numeric/count(*) END retention
FROM grid g LEFT JOIN mart_customer_month m ON m.customer_id=g.customer_id AND m.month=g.month GROUP BY g.cohort,g.age;
