-- name: customer_360
WITH billed AS (SELECT customer_id,sum(total_paise) historical_invoiced_paise FROM invoices WHERE issue_date<=(SELECT cutoff FROM run_config) GROUP BY customer_id), usage AS (SELECT customer_id,avg(active_users::numeric/entitled_users) average_usage,sum(tickets_opened) total_tickets FROM customer_monthly_activity WHERE available_date<=(SELECT cutoff FROM run_config) GROUP BY customer_id), latest AS (SELECT * FROM mart_customer_month WHERE month=(SELECT max(month) FROM dim_date))
SELECT c.*,b.historical_invoiced_paise,u.average_usage,u.total_tickets,l.mrr_paise current_mrr_paise FROM customers c LEFT JOIN billed b USING(customer_id) LEFT JOIN usage u USING(customer_id) LEFT JOIN latest l USING(customer_id);
-- name: regional_channel_performance
WITH recurring AS (SELECT region,acquisition_channel,sum(mrr_paise) mrr_paise,count(*) FILTER(WHERE mrr_paise>0) active_accounts FROM mart_customer_month WHERE month=(SELECT max(month) FROM dim_date) GROUP BY region,acquisition_channel), billed AS (SELECT c.region,c.acquisition_channel,sum(i.total_paise) invoiced_paise FROM invoices i JOIN customers c USING(customer_id) WHERE i.issue_date<=(SELECT cutoff FROM run_config) GROUP BY c.region,c.acquisition_channel), paid AS (SELECT c.region,c.acquisition_channel,sum(CASE WHEN p.status='succeeded' THEN CASE WHEN p.event_type='payment' THEN p.amount_paise ELSE -p.amount_paise END ELSE 0 END) collections_paise,count(*) FILTER(WHERE p.event_type='payment' AND p.status='failed')::numeric/NULLIF(count(*) FILTER(WHERE p.event_type='payment'),0) payment_attempt_failure_rate FROM payment_events p JOIN invoices i USING(invoice_id) JOIN customers c ON c.customer_id=i.customer_id WHERE p.event_date<=(SELECT cutoff FROM run_config) AND p.available_date<=(SELECT cutoff FROM run_config) GROUP BY c.region,c.acquisition_channel)
SELECT r.*,r.mrr_paise/NULLIF(r.active_accounts,0) arpa_paise,b.invoiced_paise,p.collections_paise,p.payment_attempt_failure_rate FROM recurring r LEFT JOIN billed b USING(region,acquisition_channel) LEFT JOIN paid p USING(region,acquisition_channel);
-- name: monthly_growth
WITH prior AS (SELECT *,lag(closing_mrr_paise) OVER(ORDER BY month) previous_mrr_paise FROM mart_revenue_month)
SELECT *,100*(closing_mrr_paise-previous_mrr_paise)/NULLIF(previous_mrr_paise,0) mom_growth_pct FROM prior ORDER BY month;
-- name: top_accounts
WITH spend AS (SELECT c.region,c.customer_id,c.company_name,sum(i.total_paise) historical_invoiced_paise FROM customers c JOIN invoices i USING(customer_id) WHERE i.issue_date<=(SELECT cutoff FROM run_config) GROUP BY c.region,c.customer_id,c.company_name),ranked AS (SELECT *,row_number() OVER(PARTITION BY region ORDER BY historical_invoiced_paise DESC,customer_id) position FROM spend)
SELECT * FROM ranked WHERE position<=5 ORDER BY region,position;
-- name: invoice_aging
SELECT aging_bucket,count(*) invoice_count,sum(outstanding_paise) outstanding_paise FROM mart_invoice_aging GROUP BY aging_bucket ORDER BY aging_bucket;
-- name: cohort_retention
SELECT * FROM mart_cohort_retention ORDER BY cohort,age;
