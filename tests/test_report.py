"""Headline numbers on the report cards must equal values computed from the source files (no hardcoded copies)."""
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
import pytest

R = Path(__file__).resolve().parents[1]
D = R / "reports" / "data"


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    subprocess.run([sys.executable, str(R / "scripts" / "build_report.py"), "--out", str(out)], check=True, cwd=R)
    return (out / "index.html").read_text(encoding="utf-8")


def test_findings_come_before_charts(page):
    assert page.index("Key findings") < page.index('id="c0"')


def test_states_data_is_simulated(page):
    assert "SIMULATED" in page


def test_headline_numbers_match_sources(page):
    g = pd.read_csv(D / "monthly_growth.csv")
    yoy = (g.closing_mrr_paise.iloc[-1] / g.closing_mrr_paise.iloc[-13] - 1) * 100
    aging = pd.read_csv(D / "invoice_aging.csv")
    unpaid = aging[aging.aging_bucket != "Paid"]
    share61 = aging[aging.aging_bucket == "61+"].outstanding_paise.iloc[0] / unpaid.outstanding_paise.sum() * 100
    reg = pd.read_csv(D / "regional_channel_performance.csv")
    ref = reg[reg.acquisition_channel == "Referral"]
    ref_rate = ref.collections_paise.sum() / ref.invoiced_paise.sum() * 100
    coh = pd.read_csv(D / "cohort_retention.csv")
    m12 = coh[coh.age == 12]
    ret12 = (m12.retention * m12.cohort_size).sum() / m12.cohort_size.sum() * 100
    t = json.load(open(R / "reports" / "model_evaluation.json"))["test"]
    for e in [f"{yoy:.1f}% MRR", f"{share61:.1f}% is 61+ days", f"{ref_rate:.1f}% collected",
              f"{ret12:.1f}% at month 12", f"{t['recall']*100:.1f}% recall", f"{t['pr_auc']:.3f}"]:
        assert e in page, e
