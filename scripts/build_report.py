"""Build docs/index.html (static report, findings first) from reports/data/*.csv and reports/model_evaluation.json.
Usage: python scripts/build_report.py [--png] [--offline] [--out DIR]
All data is SIMULATED (seed 42). Amounts are INR (source files hold paise). No database needed."""
import json
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).parent))
from report_style import BLUE, ORANGE, AQUA, VIOLET, RED, SEQ, style, build_page, screenshot  # noqa: E402

R = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else R / "docs"
D = R / "reports" / "data"
g = pd.read_csv(D / "monthly_growth.csv", parse_dates=["month"])
aging = pd.read_csv(D / "invoice_aging.csv")
reg = pd.read_csv(D / "regional_channel_performance.csv")
coh = pd.read_csv(D / "cohort_retention.csv")
model = json.load(open(R / "reports" / "model_evaluation.json"))


def inr(paise):
    return paise / 100.0


g["mrr"] = inr(g.closing_mrr_paise)
mrr_now, mrr_yoy = g.iloc[-1].mrr, g.iloc[-13].mrr
yoy = (mrr_now / mrr_yoy - 1) * 100
l12 = g.iloc[-12:]
churned12, reactiv12 = inr(l12.churned_mrr_paise.sum()), inr(l12.reactivation_mrr_paise.sum())
exp12, con12 = inr(l12.expansion_mrr_paise.sum()), inr(l12.contraction_mrr_paise.sum())

unpaid = aging[aging.aging_bucket != "Paid"]
b61 = aging[aging.aging_bucket == "61+"].iloc[0]
out_total = inr(unpaid.outstanding_paise.sum())
share61 = b61.outstanding_paise / unpaid.outstanding_paise.sum() * 100

ch = reg.groupby("acquisition_channel")[["invoiced_paise", "collections_paise", "mrr_paise"]].sum()
ch["rate"] = ch.collections_paise / ch.invoiced_paise * 100
overall_rate = reg.collections_paise.sum() / reg.invoiced_paise.sum() * 100
worst_ch = ch.rate.idxmin()
ref_share = ch.loc["Referral", "mrr_paise"] / ch.mrr_paise.sum() * 100

w = coh.assign(k=coh.retention * coh.cohort_size).groupby("age").agg(k=("k", "sum"), n=("cohort_size", "sum"))
ret = w.k / w.n * 100
ret6, ret12 = ret.loc[6], ret.loc[12]

t = model["test"]
insights = [
    dict(num=f"{yoy:.1f}% MRR",
         what=f"Simulated monthly recurring revenue is INR {mrr_now:,.0f}, {abs(yoy):.1f}% below a year earlier. Expansion and contraction nearly cancel (net INR {exp12-con12:,.0f}); churned MRR (INR {churned12:,.0f}) drives the fall.",
         action="Put retention ahead of expansion: track churned MRR per month as the lead KPI.",
         impact=f"Reactivation recovers only INR {reactiv12:,.0f} of the INR {churned12:,.0f} churned over 12 months. The simulation signs up no new accounts after month 18, so this says nothing about acquisition."),
    dict(num=f"{share61:.1f}% is 61+ days",
         what=f"Of INR {out_total:,.0f} outstanding across {int(unpaid.invoice_count.sum()):,} unpaid invoices, INR {inr(b61.outstanding_paise):,.0f} ({int(b61.invoice_count)} invoices) is more than 60 days old.",
         action="Work the 61+ day invoices first; check disputed and returned payments before outreach.",
         impact="The largest single pool of cash at risk, so chasing the oldest bucket recovers the most per call."),
    dict(num=f"{ch.loc['Referral', 'rate']:.1f}% collected",
         what=f"Referral is the top-value channel ({ref_share:.1f}% of MRR) but collects {ch.loc['Referral', 'rate']:.1f}% of invoiced value against {overall_rate:.1f}% overall; weakest channel: {worst_ch}.",
         action="Aim collections effort at Referral-sourced accounts first.",
         impact="Descriptive, not tested; recent invoices may not be due yet, so part of the gap is timing."),
    dict(num=f"{ret12:.1f}% at month 12",
         what=f"{ret12:.1f}% of accounts are still active at month 12; {100-ret6:.1f} of the {100-ret12:.1f} points lost are gone by month 6.",
         action="Focus onboarding and customer-success effort on the first six months.",
         impact="Most of the retention loss happens early, so month-6 retention is the metric to move."),
    dict(num=f"{t['recall']*100:.1f}% recall",
         what=f"The churn model (held-out PR-AUC {t['pr_auc']:.3f} vs {t['prevalence']:.3f} prevalence) catches only {t['recall']*100:.1f}% of churners; precision is {t['precision']*100:.1f}%.",
         action="Use the risk list as a triage aid, not a strategy; check usage decline, tickets and payment context before acting.",
         impact="A weak but better-than-baseline signal on simulated data; it should not drive spend on its own."),
]

f1 = go.Figure(go.Scatter(x=g.month, y=g.mrr / 1e6, mode="lines", line=dict(color=BLUE, width=2.5),
                          hovertemplate="%{x|%b %Y}: INR %{y:.2f} M<extra></extra>"))
f1.update_yaxes(title="Month-end MRR, INR millions", rangemode="tozero")
style(f1, 340, False)

bridge = pd.DataFrame({
    "m": g.month, "New": inr(g.new_mrr_paise), "Reactivation": inr(g.reactivation_mrr_paise),
    "Expansion": inr(g.expansion_mrr_paise), "Contraction": -inr(g.contraction_mrr_paise), "Churn": -inr(g.churned_mrr_paise)})
f2 = go.Figure()
for name, col in [("New", BLUE), ("Reactivation", AQUA), ("Expansion", VIOLET), ("Contraction", ORANGE), ("Churn", RED)]:
    f2.add_bar(x=bridge.m, y=bridge[name] / 1e6, name=name, marker_color=col,
               hovertemplate=name + " %{x|%b %Y}: INR %{y:.2f} M<extra></extra>")
f2.update_layout(barmode="relative", bargap=0.2)
f2.update_yaxes(title="MRR movement, INR millions")
style(f2, 380)

a = unpaid.copy()
a["m"] = inr(a.outstanding_paise) / 1e6
f3 = go.Figure(go.Bar(x=a.aging_bucket, y=a.m, marker_color=[BLUE, BLUE, ORANGE],
                      text=[f"INR {v:.1f} M" for v in a.m], textposition="outside",
                      hovertemplate="%{x} days: INR %{y:.2f} M<extra></extra>"))
f3.update_yaxes(title="Outstanding, INR millions", range=[0, a.m.max() * 1.2])
style(f3, 320, False)

cs = ch.sort_values("rate")
f4 = go.Figure(go.Bar(x=cs.rate, y=cs.index, orientation="h", marker_color=[ORANGE if i == worst_ch else BLUE for i in cs.index],
                      text=[f"{v:.2f}%" for v in cs.rate], textposition="outside"))
f4.update_xaxes(title="% of invoiced value collected", range=[cs.rate.min() - 3, 100])
style(f4, 320, False)

piv = coh.pivot(index="cohort", columns="age", values="retention") * 100
f5 = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=[str(i)[:7] for i in piv.index],
                          colorscale=[[0, SEQ[0]], [.5, SEQ[2]], [1, SEQ[4]]], zmin=50, zmax=100,
                          colorbar=dict(title="% active"), hovertemplate="Cohort %{y}, month %{x}: %{z:.1f}%<extra></extra>"))
f5.update_yaxes(autorange="reversed")
f5.update_xaxes(title="Months since signup")
style(f5, 420, False)

sections = [
    ("MRR trend", "Month-end monthly recurring revenue, 36 simulated months.", f1),
    ("Where MRR is gained and lost", "Monthly movements. New signups stop after month 18 in the simulation.", f2),
    ("Unpaid invoices by age", "Outstanding balance by invoice age in days.", f3),
    ("Collection rate by acquisition channel", "Collected as a share of invoiced value, all time. Orange = weakest.", f4),
    ("Cohort retention", "Share of each signup cohort still active, by months since signup (color floor 50%).", f5),
]
out, size = build_page(
    "RevPulse: where simulated SaaS revenue leaks",
    "B2B SaaS revenue, billing and retention analytics. ALL DATA IS SIMULATED (seed 42, 1,000 accounts, 36 months to Dec 2025). Amounts in INR.",
    insights, sections,
    caveat="Synthetic data: these findings describe a generated dataset, not a real business. No new accounts are simulated after month 18. The churn model was evaluated on a chronological hold-out and is weak.",
    footer="Data: reports/data/*.csv (exports of the SQL marts) and reports/model_evaluation.json. Rebuild: python scripts/build_report.py.",
    out=str(OUT / "index.html"), offline="--offline" in sys.argv)
print("wrote", out, f"{size/1e6:.2f} MB")
if "--png" in sys.argv:
    (OUT / "img").mkdir(exist_ok=True)
    screenshot(out, OUT / "img" / "report-top.png", height=1100)
    screenshot(out, OUT / "img" / "report-full.png", full=True)
