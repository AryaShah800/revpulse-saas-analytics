# Data dictionary

One row has the grain below. Required fields are non-null except CSAT; missing invoice totals may be reconstructed during cleaning.

## customers
Grain: one customer account.

| Field | Type |
|---|---|
| `customer_id` | text |
| `company_name` | text |
| `signup_date` | date |
| `region` | text |
| `acquisition_channel` | text |

## subscription_periods
Grain: one unchanged interval of subscription terms.

| Field | Type |
|---|---|
| `period_id` | text |
| `subscription_id` | text |
| `customer_id` | text |
| `effective_from` | date |
| `effective_to` | date |
| `plan_tier` | text |
| `billing_months` | int |
| `recurring_paise` | int |
| `discount_paise` | int |

## invoices
Grain: one issued invoice.

| Field | Type |
|---|---|
| `invoice_id` | text |
| `customer_id` | text |
| `period_id` | text |
| `issue_date` | date |
| `due_date` | date |
| `service_from` | date |
| `service_to` | date |
| `recurring_paise` | int |
| `one_time_paise` | int |
| `tax_paise` | int |
| `total_paise` | int |

## payment_events
Grain: one immutable payment/refund/reversal event.

| Field | Type |
|---|---|
| `event_id` | text |
| `invoice_id` | text |
| `event_date` | date |
| `available_date` | date |
| `event_type` | text |
| `status` | text |
| `amount_paise` | int |

## customer_monthly_activity
Grain: one account-month.

| Field | Type |
|---|---|
| `record_id` | text |
| `customer_id` | text |
| `month` | date |
| `available_date` | date |
| `active_users` | int |
| `entitled_users` | int |
| `tickets_opened` | int |
| `tickets_resolved` | int |
| `unresolved_tickets` | int |
| `csat_score` | float |
| `csat_responses` | int |
