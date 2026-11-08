# Cleaning and validation log

Run: `20261107T082251_ebe78748`. Original source values remain in the run audit.

| Table | Input | Accepted | Exact duplicates | Quarantined |
|---|---:|---:|---:|---:|
| customers | 1000 | 1000 | 0 | 0 |
| subscription_periods | 3223 | 3223 | 0 | 0 |
| invoices | 15441 | 15435 | 1 | 5 |
| payment_events | 17697 | 17693 | 0 | 4 |
| customer_monthly_activity | 22124 | 22123 | 0 | 1 |

## Rejection reasons

| Table | Reason | Rows |
|---|---|---:|
| customer_monthly_activity | invalid_usage | 1 |
| invoices | conflicting_key | 2 |
| invoices | exact_duplicate | 1 |
| invoices | invalid_iso_date:issue_date | 1 |
| invoices | invoice_component_mismatch | 1 |
| invoices | orphan_customer | 1 |
| payment_events | orphan_invoice | 4 |

## Transformations

| Table | Record | Field | Rule |
|---|---|---|---|
| customers | C0001 | region | region_mapping |
| invoices | C0001-P2-202305 | total_paise | authoritative_components |

No statistical imputation is used for reported financial values. Statistical anomalies remain in accepted reporting data unless a separate validity rule quarantines them.
