# Metric dictionary

All source money is integer paise (100 paise = INR 1). SQL normalizes annual contracts using exact NUMERIC arithmetic. Presentation rounds only for display. Event dates use business dates in Asia/Calcutta; monthly activity is assumed available at that month's end.

| Metric | Definition and scope |
|---|---|
| MRR | Recurring contract charges less recurring discount, divided by billing months, for subscriptions active at month-end. Excludes taxes and one-time charges. |
| ARR | 12 times month-end MRR; an annualized run rate, not recognized revenue. |
| Invoiced amount | Sum of issued invoice totals, including simulated taxes and one-time charges. |
| Net collections | Successful payments less successful refunds/reversals, with both event and availability dates at or before cutoff. |
| Active accounts | Distinct customers with positive month-end MRR; concurrent subscriptions count once. |
| ARPA | Month-end MRR divided by active accounts. |
| Opening MRR | Prior month-end account MRR. Before first observed activation it is zero. |
| New / reactivated MRR | Closing MRR for accounts with zero opening MRR, distinguished using prior observed activity. |
| Expansion / contraction | Positive / negative difference in MRR for accounts active at both endpoints. |
| Churned MRR | Opening MRR for accounts with zero closing MRR. |
| Customer churn rate | Opening accounts inactive at month-end divided by opening active accounts. |
| NRR | Closing MRR from opening active accounts divided by their opening MRR; excludes new and reactivated accounts. |
| MoM growth | Change in MRR divided by preceding MRR; undefined when the preceding value is zero. |
| Outstanding / credit | Positive unpaid balance / positive overpayment at cutoff. Refunds reopen balance in this simulation; credit-note accounting is outside scope. |
| Days overdue | max(0, cutoff minus due date), only for outstanding invoices. Buckets: Current, 1–15, 16–30, 31–60, 61+. Paid rows are separate. |
| Payment delay | Successful payment event date minus invoice due date. Negative means early; averages are event-weighted, not invoice-weighted. |
| Payment failure rate | Failed payment attempts divided by all payment attempts; refunds/reversals excluded from denominator. |
| Retention cohort | First observed paid-contract activation month. Fraction with positive MRR at each later month-end; future unobserved ages stay null. Reactivated accounts count as retained at the observed endpoint. |
| Prediction label | Whether an account loses its last subscription during the next calendar month. Same-time renewals are not churn. A loss followed by reactivation still counts as an event. |
| High-risk MRR | Current MRR of scored accounts above the validation-selected threshold. Exposure, not guaranteed loss or probability-weighted expected loss. |

The generator changes lifecycle state only at month boundaries, so event churn and endpoint churn agree on this dataset. For general imported data these definitions can differ. The Power BI plan slicer assigns an account's full MRR to its largest current subscription tier; inactive accounts retain their last active tier so churn remains visible under plan filters. This is an account-segmentation view; upgrades move accounts between segments. Invoice plan segmentation uses the invoiced contract tier.

MRR is a snapshot: each card uses the latest selected month. Summing month-end MRR across dates does not produce a valid MRR card. Historical invoicing/collections in the regional query cover the full observed reporting period; current MRR/ARPA use its final month.
