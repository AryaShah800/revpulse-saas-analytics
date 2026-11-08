import json
from pathlib import Path
import shutil
import pandas as pd
import pytest
from revpulse.core import Config,CONTRACTS,read_csv,write_csv,digest,json_write
from revpulse.generate import generate,simulate,validate_truth
from revpulse.clean import clean
from revpulse.pipeline import build

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('seed',[7,42,91])
def test_generated_truth_obeys_financial_contracts(seed):
    validate_truth(simulate(Config(ROOT,seed=seed,accounts=20,months=18)))

@pytest.fixture
def workspace(tmp_path):
    shutil.copytree(ROOT/'sql',tmp_path/'sql')
    (tmp_path/'.local').mkdir()
    shutil.copy2(ROOT/'.local/database.json',tmp_path/'.local/database.json')
    return tmp_path

def test_reproducible_sources_and_hash_protection(workspace):
    cfg=Config(workspace,accounts=10)
    source=generate(cfg);before={t:digest(source/f'{t}.csv') for t in CONTRACTS}
    assert generate(cfg)==source
    assert before=={t:digest(source/f'{t}.csv') for t in CONTRACTS}
    with (source/'invoices.csv').open('a') as f:f.write('\n')
    with pytest.raises(ValueError,match='hash mismatch'):generate(cfg)

def test_quarantine_recovery_and_row_reconciliation(workspace):
    cfg=Config(workspace,accounts=10);source=generate(cfg)
    tables,audit=clean(source,workspace/'check')
    evidence=json.loads((workspace/'check/audit/quality.json').read_text())
    for table,v in evidence['tables'].items():assert v['input']==v['accepted']+v['duplicate']+v['quarantined']
    reasons={r['reason'] for r in audit}
    assert {'exact_duplicate','conflicting_key','invoice_component_mismatch','orphan_customer','invalid_usage'}<=reasons
    assert any(r['reason'].startswith('invalid_iso_date') for r in audit)
    conflict_ids={r['key'] for r in audit if r['reason']=='conflicting_key'}
    assert not conflict_ids & {r['invoice_id'] for r in tables['invoices']}
    changes=read_csv(workspace/'check/audit/transformations.csv')
    assert {'authoritative_components','region_mapping'}<={r['rule'] for r in changes}

def test_failed_run_preserves_all_published_outputs(workspace):
    cfg=Config(workspace,accounts=10)
    run=build(cfg);pointer=(workspace/'data/current.json').read_bytes()
    before={str(f.relative_to(run)):digest(f) for f in run.rglob('*') if f.is_file()}
    with pytest.raises(RuntimeError,match='Injected failure'):build(cfg,fail_before_publish=True)
    assert (workspace/'data/current.json').read_bytes()==pointer
    assert before=={str(f.relative_to(run)):digest(f) for f in run.rglob('*') if f.is_file()}
    rerun=build(cfg)
    for file in (run/'marts').glob('*.csv'):
        # SQL physical ordering is not a contract: compare sorted values.
        left=pd.read_csv(file).astype(str).fillna('');right=pd.read_csv(rerun/'marts'/file.name).astype(str).fillna('')
        pd.testing.assert_frame_equal(left.sort_values(list(left.columns)).reset_index(drop=True),right.sort_values(list(right.columns)).reset_index(drop=True))
    assert len(list((rerun/'queries').glob('*.csv')))==6

def test_empty_source_build_has_zero_calendar_mrr(workspace):
    source=workspace/'empty_source'
    for table in CONTRACTS:write_csv(source/f'{table}.csv',[],CONTRACTS[table])
    json_write(source/'manifest.json',dict(source_id='empty',hashes={t:digest(source/f'{t}.csv') for t in CONTRACTS}))
    run=build(Config(workspace,accounts=10),source)
    revenue=pd.read_csv(run/'marts/mart_revenue_month.csv')
    assert len(revenue)==36
    assert revenue.closing_mrr_paise.sum()==0
    assert revenue.nrr.isna().all()
