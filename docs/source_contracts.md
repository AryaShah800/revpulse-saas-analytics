# Source contracts and scope

Five CSV files use UTF-8 headers matching data_dictionary.md, ISO dates, integer paise, and stable business IDs. Input manifests contain SHA-256 hashes. `revpulse --source` expects this manifest alongside source files. No connector to a live billing platform is included.

Raw generation is deterministic by seed/configuration/version and stored under `data/sources/<source_id>`. Existing source files are verified, never silently overwritten. Reference truth and injected-defect manifests live under `data/reference/<source_id>` and are only used for evaluation.

Subscription periods are half-open [effective_from, effective_to). A future sentinel date denotes subscriptions still active at the observation cutoff; it is excluded from prediction features. Monthly and annual fixed-price plans are supported. Changes happen at renewal, avoiding proration. The simulation supports multiple subscriptions, partial payments, refunds, failed attempts, cancellation and reactivation. Tax is a simulated invoice component, not a tax-compliance implementation. No currency conversion or accounting revenue-recognition schedules are supplied.

Payment rows are immutable events. Exact repeats are duplicates; conflicting payloads for one event ID are quarantined. Mutable status-snapshot exports require an upstream adapter with version/event timestamps; this project does not guess which conflicting version is authoritative.

Only documented regional variants are normalized. Dates with slashes are ambiguous under the ISO source contract and are quarantined. Missing invoice totals are recovered only from populated authoritative components. Missing CSAT remains unavailable. Invalid usage is quarantined rather than clipped.

Conflicting keys and all detected overlapping subscription periods are quarantined. Dependent records lacking accepted parents are also quarantined, preserving relational integrity. Exclusions can reduce financial coverage; unknown missing financial values are not assigned invented amounts. Source row, original JSON, disposition and reason remain in the run audit and PostgreSQL lineage table.
