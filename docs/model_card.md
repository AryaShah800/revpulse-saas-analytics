# Churn model card

Purpose: prioritize existing active accounts for investigation at a month-end cutoff. Dataset: synthetic RevPulse simulation, not real customer outcomes.

Selected estimator: **random_forest**. Validation-selected threshold: **0.148586**. Logistic Regression and Random Forest are compared on validation PR-AUC. A prevalence baseline and a simple usage/delay rule are reported on the held-out test set.

Numeric features: usage ratio and change, opened/unresolved tickets, CSAT and missingness, tenure, MRR, overdue balance and recent payment delay. Plan tier is one-hot encoded. Customer IDs, future cancellation dates and generator truth are excluded. Imputation/scaling/encoding are fitted only on training data.

```json
{
  "train": {
    "first": "2023-01-31",
    "last": "2024-12-31",
    "rows": 13526,
    "churns": 293
  },
  "validation": {
    "first": "2025-01-31",
    "last": "2025-06-30",
    "rows": 4507,
    "churns": 109
  },
  "test": {
    "first": "2025-07-31",
    "last": "2025-11-30",
    "rows": 3440,
    "churns": 84
  }
}
```

Held-out PR-AUC: 0.1386; prevalence: 0.0244; precision: 0.1791; recall: 0.1429; F1: 0.1589; Brier score: 0.0226.

The test set is evaluated after validation-based selection, with no test-driven tuning. Re-running the deterministic training command reproduces this report; it does not authorize iterative tuning against held-out outcomes. Monthly top-20 campaign metrics are in model_evaluation.json. Pooled top-K metrics are diagnostic; campaign capacity is evaluated per scoring month.

Existing accounts may appear in multiple chronological splits because the use case is recurring scoring. Results do not measure entirely new-account generalization. Recent payment-delay missingness is retained for training-only imputation. Features use event availability dates. Snapshots without a complete next-month observation window have null labels and are excluded from training/evaluation.

The saved model remains the training-only model used in evaluation; it is not silently refitted on held-out labels. Model and threshold are serialized together. Scoring exports include score date, model version and training-run ID. Current scores and supporting indicators are associations, not causal explanations. Synthetic performance does not establish commercial effectiveness or revenue saved.
