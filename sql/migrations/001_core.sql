CREATE TABLE customers (
 customer_id text PRIMARY KEY, company_name text NOT NULL, signup_date date NOT NULL,
 region text NOT NULL CHECK(region IN ('North','South','East','West')), acquisition_channel text NOT NULL
);
CREATE TABLE subscription_periods (
 period_id text PRIMARY KEY, subscription_id text NOT NULL, customer_id text NOT NULL REFERENCES customers,
 effective_from date NOT NULL, effective_to date NOT NULL, plan_tier text NOT NULL CHECK(plan_tier IN ('Starter','Growth','Enterprise')),
 billing_months integer NOT NULL CHECK(billing_months IN (1,12)), recurring_paise bigint NOT NULL CHECK(recurring_paise>0),
 discount_paise bigint NOT NULL CHECK(discount_paise>=0 AND discount_paise<recurring_paise),
 CHECK(effective_from<effective_to),
 EXCLUDE USING gist(subscription_id WITH =, daterange(effective_from,effective_to,'[)') WITH &&)
);
CREATE TABLE invoices (
 invoice_id text PRIMARY KEY, customer_id text NOT NULL REFERENCES customers, period_id text NOT NULL REFERENCES subscription_periods,
 issue_date date NOT NULL,due_date date NOT NULL,service_from date NOT NULL,service_to date NOT NULL,
 recurring_paise bigint NOT NULL CHECK(recurring_paise>=0),one_time_paise bigint NOT NULL CHECK(one_time_paise>=0),
 tax_paise bigint NOT NULL CHECK(tax_paise>=0), total_paise bigint NOT NULL,
 CHECK(total_paise=recurring_paise+one_time_paise+tax_paise),CHECK(service_from<service_to),CHECK(due_date>=issue_date)
);
CREATE TABLE payment_events (
 event_id text PRIMARY KEY,invoice_id text NOT NULL REFERENCES invoices,event_date date NOT NULL,available_date date NOT NULL,
 event_type text NOT NULL CHECK(event_type IN ('payment','refund','reversal')),status text NOT NULL CHECK(status IN ('succeeded','failed')),
 amount_paise bigint NOT NULL CHECK(amount_paise>=0),CHECK(available_date>=event_date)
);
CREATE TABLE customer_monthly_activity (
 record_id text PRIMARY KEY,customer_id text NOT NULL REFERENCES customers,month date NOT NULL,available_date date NOT NULL,
 active_users integer NOT NULL,entitled_users integer NOT NULL CHECK(entitled_users>0),
 tickets_opened integer NOT NULL CHECK(tickets_opened>=0),tickets_resolved integer NOT NULL CHECK(tickets_resolved>=0),
 unresolved_tickets integer NOT NULL CHECK(unresolved_tickets>=0),csat_score numeric,csat_responses integer NOT NULL CHECK(csat_responses>=0),
 UNIQUE(customer_id,month),CHECK(active_users BETWEEN 0 AND entitled_users),CHECK(csat_score BETWEEN 1 AND 5),CHECK(available_date>=month)
);
CREATE TABLE source_lineage (table_name text,source_row integer,business_key text,disposition text,reason text,original_json jsonb);
CREATE INDEX invoice_customer_date ON invoices(customer_id,issue_date);
CREATE INDEX payment_invoice_date ON payment_events(invoice_id,event_date);
CREATE INDEX subscription_customer ON subscription_periods(customer_id,effective_from,effective_to);
