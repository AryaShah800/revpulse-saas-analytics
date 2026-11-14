# Runbook

## Install and run

Use Python 3.13 on Windows for the supplied dependency lock. PostgreSQL 18 was used for verification. Alternative supported Python versions may need a newly resolved lock.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe scripts/setup_postgres.py
.\.venv\Scripts\python.exe -m revpulse.cli all
.\.venv\Scripts\python.exe -m pytest tests -q
```

The setup script creates only the project-owned `.local/pgdata` cluster at 127.0.0.1:55432, with a generated password in ignored `.local/database.json`. It does not reset or edit the existing server. Set POSTGRES_BIN if binaries are elsewhere. A preconfigured REVPULSE_DATABASE_URL can be used instead; the database role needs permission to create schemas and the btree_gist extension. Do not commit credentials.

`config/project.json` provides generation defaults. CLI flags override seed/accounts/start/months. Use `--workspace <absolute-project-directory>` when running from another directory or a non-editable installation. `generate` creates/reuses immutable source files. `ingest` and `validate` produce a new staging/audit directory without publication. `build` / `build-marts` build and publish core reporting outputs. `train` analyzes anomalies, trains/evaluates models and scores current accounts. `score` uses the saved model. `export` refreshes CSV extracts. `all` executes generate/build/train/score/export.

## Publication and recovery

`data/current.json` is the authoritative active-run pointer. Each core build writes a new run folder and a new PostgreSQL schema. Constraints and reconciliations pass before the schema commits and the pointer is replaced. Failed builds preserve the existing pointer and all published core files. Failed run folders carry FAILED.json; do not use them for reporting. Concurrent writers to one workspace are not supported. Unreferenced historical schemas/run folders are retained; cleanup is a deliberate operator task.

Analytics outputs are derived after core publication and include model/run metadata. If training fails, the core financial run remains valid but analytics are incomplete; rerun `train`, then `export`. Never present the presence of the core pointer as proof that every downstream artifact is refreshed.

The original prototype is retained under `data/legacy/prototype`. Old `data/raw` and `data/processed` files belong to that prototype and are not current inputs. Use the pointer and versioned run directories.

## Excel

Run `scripts/prepare_workbook.py`, then `scripts/build_workbook.ps1` with the bundled Node, module directory and Python paths returned by the artifact runtime loader. The builder uses @oai/artifact-tool; `add_native_pivots.py` supplements missing native pivot export using OOXML. `verify_artifacts.py` reads and verifies the result. The annual audit covers invoices issued and successful payment events in the cutoff calendar year; outstanding balances are as of cutoff.

The workbook includes XLOOKUPs, actual native PivotTables, validation, conditional formatting, cached results and SQL reconciliation. To validate native refresh later: activate Excel, open the workbook, confirm there is no repair prompt, refresh both pivots, force full calculation, inspect the reconciliation cells, then edit a source amount in a disposable copy and confirm dependent formulas/pivots update. Restore the original source afterward. Current native editing/refresh validation is deferred because Office is unlicensed.

## Power BI

```powershell
.\.venv\Scripts\python.exe -m revpulse.cli export
.\.venv\Scripts\python.exe scripts/build_powerbi.py
.\.venv\Scripts\python.exe scripts/validate_powerbi.py
```

Open `dashboard/RevPulse.pbip` in Power BI Desktop. DataFolder is an editable Power Query parameter; regenerate the project after relocating the repository or change this parameter. Refresh, verify the latest-month cards against mart_revenue_month.csv, then compare region/plan/date selections with customer-month SQL. Check that selecting multiple months still shows latest-month MRR. The actions page is a cutoff snapshot; the top-20 table is globally ranked before slicer filtering.

The project contains two main pages plus an audit/definitions page. It was opened, refreshed and checked in Power BI Desktop on 2026-11-14 and saved as `dashboard/RevPulse.pbix` with `RevPulse.pdf` and `page-1.png` to `page-3.png`. Desktop rewrote some PBIR/model files when saving; do not overwrite them with generator output (`scripts/build_powerbi.py`). The saved `DataFolder` points to an earlier export folder; see the README for what that means.
