# RevPulse completion: diagnosis and execution contract

Audit date: 6 November 2026. Read this before continuing COMPLETION_PLAN.md.

## Why previous attempts did not finish

The primary failure was premature termination of execution: the assistant repeatedly delivered small increments and ended despite authorization for the complete project. No evidence shows that the full project was technically impossible. Creating another plan did not resolve that execution failure.

Contributing problems:

1. The large backlog was never translated into a tracked sequence with evidence required for closure.
2. The prototype schema was implemented before the required lifecycle and financial fields, creating rework for aging, annual MRR, and churn.
3. Dependencies and desktop artifact creation were not validated early.
4. Three passing tests were treated as progress without explicitly measuring requirement coverage. They do not establish financial correctness or end-to-end completeness.
5. The latest database publication safeguard covers only the database: CSV outputs are overwritten before validation finishes. Failed builds can still expose inconsistent outputs.
6. Scope silently shrank: invoice growth replaced MRR growth; outstanding balances replaced aging; SQLite replaced PostgreSQL. These are scaffolds, not completed requirements.

## Verified environment findings

| Finding | Evidence | Resolution |
|---|---|---|
| PostgreSQL 18 is installed and running | Windows service running; pg_isready accepts connections on 5432 | Use native PostgreSQL; Docker is unnecessary |
| Tested PostgreSQL role requires credentials | Noninteractive localhost connection as postgres failed with no password supplied | Use a user-configured least-privilege connection; do not reset existing passwords. If unavailable, initialize an isolated project-owned cluster on a separate local port using installed binaries, with explicit local authentication configuration |
| Docker executable exists but engine is unavailable | Docker API named-pipe connection failed | Do not make Docker a prerequisite |
| Excel is registered | App Paths registry identifies Office16 EXCEL.EXE | Verify file/application launch and workbook recalculation before claiming Excel validation |
| Power BI availability is unresolved | Common install path and Store-package probe produced no result | Inspect installed-app registry and alternate locations; if absent, prepare native report source and arrange Desktop installation/open validation. Do not label an unvalidated source project a finished PBIX |
| Required Python analytics libraries were absent in the checked interpreter | pandas, sklearn, openpyxl, pytest discovery returned false | Create a project virtual environment and install pinned dependencies; verify imports |

These findings are narrower than blanket claims that Excel or Power BI is unavailable. No desktop launch or full installation inventory has yet been performed.

## Next implementation run: mandatory order

### 1. Preflight and persist progress

- Read both existing plans and inspect current code without recreating planning documents.
- Create a machine-readable requirement ledger with IDs, implementation paths, acceptance command/manual check, status, and evidence path.
- Record each requirement as pending, implemented-unverified, verified, or externally-blocked. Never infer verification from file existence.
- Establish the Python virtual environment and database connection first.
- Resolve Excel and Power BI authoring/validation routes immediately; continue independent code while any genuine external dependency is pending.

### 2. Build one complete vertical slice

Use ten accounts covering annual billing, concurrent subscriptions, upgrades, cancellations, reactivation, partial payments, refunds, and late payments.

Implement source contracts -> validation -> PostgreSQL -> customer-month/aging marts -> independent expected results. Only expand to 1,000 accounts after these checks pass. Replace prototype fields rather than layering complex logic onto missing dates.

### 3. Finish pipeline and SQL

Complete WP1–WP4 from COMPLETION_PLAN.md. Publish a validated run directory containing all CSVs, audits, and database version references; switch the active-run pointer only after successful validation. A failed run must not partially replace published artifacts.

Use migrations, keys, explicit dates, point-in-time logic, defect manifests, quarantine, decimal/integer money, and six genuinely complete analyses. Run integration tests against PostgreSQL, not just SQLite.

### 4. Deliver native business artifacts

Complete WP5–WP6. Use the spreadsheet skill when creating the workbook and computer-use guidance for native UI validation. Verify formulas, genuine PivotTables, refresh, and dashboard filters. Save visual evidence.

If a native application cannot be used, record that exact missing acceptance step and continue all independent work. Do not substitute CSV/HTML screenshots and mark Excel/Power BI complete.

### 5. Finish advanced analytics

Complete WP7–WP8. Generate temporally valid features; fit preprocessing only on training data; compare operational/model baselines; evaluate held-out periods once. Save model artifacts, score exports, anomaly evaluations, and limitations. Use synthetic results as workflow evidence rather than proof of commercial impact.

### 6. Integrate and close

Complete WP9. Run from a fresh environment, reconcile all outputs, refresh native artifacts, update documentation, and produce one completion report mapping every requirement to evidence.

## Rules that prevent another partial delivery

- One user authorization covers the full local implementation. Do not ask the user to say “continue” after each package.
- Keep implementing after a successful package; a milestone is not a reason to end the task.
- Checkpoint progress to `reports/implementation_status.json` and `docs/NEXT_ACTION.md` so a continuation resumes the exact unfinished step.
- If execution must be interrupted, state incomplete status and preserve a runnable checkpoint; do not claim completion or generate another plan as a substitute.
- Ask only for concrete missing inputs that cannot be resolved safely; do all independent work first.
- Do not promise that all native-app dependencies can be resolved without installation/access. Separate verified blockers from untested assumptions.
- Final completion requires all mandatory requirements verified. Externally blocked requirements remain visibly incomplete.

## Suggested next-run instruction

> Implement COMPLETION_PLAN.md in C:\Projects\revpulse-saas-analytics, following RECOVERY_AND_EXECUTION_PLAN.md. Execute the complete backlog rather than producing another plan. Establish the environment, track every requirement with verification evidence, build and test the financial vertical slice, then finish PostgreSQL, Excel, Power BI, anomalies, churn, and documentation. Continue through all independent work without stopping at milestones. Preserve checkpoints and report only genuinely unresolved external dependencies. Do not mark the project complete until its acceptance gates pass.

No prompt guarantees completion by itself. The corrective mechanism is sustained execution, early dependency checks, explicit coverage, and evidence-based acceptance.
