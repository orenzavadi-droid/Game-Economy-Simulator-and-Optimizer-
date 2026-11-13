"""Build an interactive HTML decision dashboard from generated CSVs. Requires Plotly CDN."""
from __future__ import annotations
from pathlib import Path
import json
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.io import to_html

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RPT = ROOT / 'reports'
COLORS = {'Baseline':'#6b86a5','Reward +25%':'#31c5b0','Upgrade Price +25%':'#eeaa64',
          'Targeted Sink +30%':'#bb94ec'}


def style(fig: go.Figure, title: str, height: int = 355) -> go.Figure:
    fig.update_layout(title={'text':title,'font':{'size':17,'color':'#eaf1ff'},'x':0.035},
                      paper_bgcolor='#101a2e', plot_bgcolor='#101a2e',
                      font=dict(family='Inter,Arial,sans-serif',color='#cbd5e1',size=12),
                      margin=dict(l=50,r=25,t=58,b=48), height=height,
                      legend=dict(orientation='h',y=-0.23,x=0.0, font={'size':11}),
                      hovermode='x unified')
    fig.update_xaxes(showgrid=True, gridcolor='#253349',zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#253349',zeroline=False)
    return fig


def card(fig: go.Figure, js: bool = False) -> str:
    return '<div class="plot-card">' + to_html(fig, include_plotlyjs="cdn" if js else False,
                                                    full_html=False, config={'displaylogo':False,'responsive':True}) + '</div>'


def main() -> None:
    daily = pd.read_csv(DATA/'daily_metrics.csv')
    persona = pd.read_csv(DATA/'persona_metrics.csv')
    profiles = pd.read_csv(DATA/'profile_comparison.csv')
    cands = pd.read_csv(DATA/'optimizer_candidates.csv').fillna({'failed_guardrails':''})
    validation = pd.read_csv(DATA/'optimizer_validation_summary.csv')
    stress = pd.read_csv(DATA/'stress_sensitivity.csv')
    selection = json.loads((RPT/'optimization_selection.json').read_text())
    rec = selection['selected_candidate']
    by_metric = validation.set_index('metric')
    baseline_gap = by_metric.loc['affordability_gap_active_pct','baseline_mean']
    recommended_gap = by_metric.loc['affordability_gap_active_pct','recommended_mean']
    base_upg = by_metric.loc['avg_upgrades_per_install','baseline_mean']
    rec_upg = by_metric.loc['avg_upgrades_per_install','recommended_mean']
    b_wallet = by_metric.loc['median_wallet_survivors_day_end','baseline_mean']
    r_wallet = by_metric.loc['median_wallet_survivors_day_end','recommended_mean']
    b_ratio = by_metric.loc['source_to_sink_ratio','baseline_mean']
    r_ratio = by_metric.loc['source_to_sink_ratio','recommended_mean']

    # Core economy trend charts.
    trend1 = go.Figure()
    trend2 = go.Figure()
    for name, g in daily.groupby('scenario',sort=False):
        color = COLORS.get(name,'#ffffff')
        trend1.add_trace(go.Scatter(x=g.day,y=g.cumulative_upgrades_per_install,name=name,
                                    mode='lines',line={'color':color,'width':2.6}))
        trend2.add_trace(go.Scatter(x=g.day,y=g.affordability_gap_active_pct*100,name=name,
                                    mode='lines',line={'color':color,'width':2.6}))
    style(trend1,'Progression · cumulative upgrades per install')
    style(trend2,'Friction · share of active play-days unable to afford next upgrade')
    trend1.update_layout(yaxis_title='Upgrades / original install',xaxis_title='Days since install')
    trend2.update_layout(yaxis_title='Active play-days (%)',xaxis_title='Days since install')
    flow = go.Figure()
    summary = pd.read_csv(DATA/'scenario_summary.csv')
    flow.add_trace(go.Bar(x=summary.scenario,y=summary.earned_coins, name='Sources',marker_color='#2cc6ac'))
    flow.add_trace(go.Bar(x=summary.scenario,y=summary.spent_coins, name='Sinks',marker_color='#f0aa68'))
    style(flow,'30-day soft currency · sources vs sinks')
    flow.update_layout(barmode='group',yaxis_title='Coins (cohort)',xaxis_title='')

    # Feasible frontier, selected candidate and guardrail transparency.
    frontier = go.Figure()
    for feasible, subset in cands.groupby('feasible'):
        frontier.add_trace(go.Scatter(x=subset.affordability_gap_active_pct*100,
                                    y=subset.avg_upgrades_per_install, mode='markers',
                                    name='Feasible' if feasible else 'Guardrail violation',
                                    marker={'color':subset.median_wallet_survivors_day_end,
                                            'colorscale':'Tealgrn','showscale':bool(feasible),
                                            'colorbar':{'title':'Median wallet'},'size':12 if feasible else 9,
                                            'symbol':'circle' if feasible else 'x',
                                            'line':{'width':0.5,'color':'#dae4f3'}},
                                    customdata=np.stack([subset.candidate,subset.reward_multiplier,
                                                         subset.upgrade_price_multiplier,subset.cosmetic_offer_multiplier],axis=1),
                                    hovertemplate='Candidate %{customdata[0]}<br>Gap: %{x:.2f}%<br>Upgrades: %{y:.2f}'
                                                  '<br>Reward x%{customdata[1]} | Upgrade x%{customdata[2]} | Sink x%{customdata[3]}<extra></extra>'))
    chosen = cands[cands.candidate==rec].iloc[0]
    frontier.add_trace(go.Scatter(x=[100*chosen.affordability_gap_active_pct],y=[chosen.avg_upgrades_per_install],
                                  name=f'Selected: {rec}',mode='markers+text',text=['Selected'],
                                  textposition='top center',marker={'symbol':'star','color':'#fac76a','size':20,
                                                                   'line':{'width':1,'color':'#fff'}}))
    style(frontier,'Training grid · affordability vs progression',height=450)
    frontier.update_layout(xaxis_title='Affordability gap (%) — lower is better',
                           yaxis_title='Upgrades per install — higher is better',hovermode='closest')

    # Persona results.
    p7 = persona[persona.day==7]
    pers = go.Figure()
    for scen,g in p7.groupby('scenario',sort=False):
        pers.add_trace(go.Bar(name=scen,x=g.persona,y=g.retention*100,
                              marker_color=COLORS.get(scen,'#ddd')))
    style(pers,'Synthetic exact-day D7 return rate by persona')
    pers.update_layout(barmode='group',yaxis_title='D7 cohort return (%)',xaxis_title='')
    p_gap = persona.groupby(['scenario','persona'],sort=False).apply(
        lambda x: float(np.average(x.affordability_gap_active_pct,weights=x.active_players))
        if x.active_players.sum() else 0,include_groups=False).reset_index(name='gap')
    pg = go.Figure()
    for scen,g in p_gap.groupby('scenario',sort=False):
        pg.add_trace(go.Bar(name=scen,x=g.persona,y=g.gap*100,
                            marker_color=COLORS.get(scen,'#ddd')))
    style(pg,'Affordability friction by behavioral persona')
    pg.update_layout(barmode='group',yaxis_title='Active play-days (%)',xaxis_title='')
    pf = go.Figure()
    pf.add_trace(go.Bar(name='Upgrades / install',x=profiles.scenario,y=profiles.avg_upgrades_per_install,
                        marker_color='#36cab5'))
    style(pf,'Three illustrative economy archetypes — not real genre benchmarks')
    pf.update_layout(yaxis_title='Upgrades / original install',xaxis_title='')
    stress_mean = stress.groupby('stress',sort=False)[['affordability_gap_active_pct','avg_upgrades_per_install',
                                                      'source_to_sink_ratio']].mean().reset_index()
    ss=go.Figure()
    ss.add_trace(go.Bar(x=stress_mean.stress,y=stress_mean.affordability_gap_active_pct*100,
                        name='Affordability gap (%)',marker_color='#e8a36a'))
    style(ss,'Assumption sensitivity · four independent seeds per stress',height=410)
    ss.update_layout(yaxis_title='Active play-days with affordability gap (%)',xaxis_tickangle=-22)
    # Holdout metrics: paired scenarios with range of paired deltas across four seeds.
    vrows = []
    metrics_display = [('affordability_gap_active_pct','Upgrade affordability gap','%',100),
                       ('avg_upgrades_per_install','Upgrades per install','',1),
                       ('median_wallet_survivors_day_end','Median wallet among survivors','coins',1),
                       ('source_to_sink_ratio','Sources / sinks','ratio',1),
                       ('surplus_active_pct','Surplus active play-days','%',100),
                       ('d7_retention','D7 return rate','%',100)]
    for key,lab,unit,mul in metrics_display:
        row=by_metric.loc[key]
        value=lambda v: f'{float(v)*mul:+.2f}'
        vrows.append('<tr><td>'+html.escape(lab)+'</td><td>'+f'{float(row.baseline_mean)*mul:.2f}'+'</td><td>'+f'{float(row.recommended_mean)*mul:.2f}'+'</td><td>'+value(row.paired_delta_mean)+'</td><td>'+f'{float(row.delta_min)*mul:+.2f} to {float(row.delta_max)*mul:+.2f}'+'</td><td>'+html.escape(unit)+'</td></tr>')
    selected_specs = f'Quest reward ×{selection["reward_multiplier"]:.2f} · Upgrade price ×{selection["upgrade_price_multiplier"]:.2f} · Cosmetic offer ×{selection["cosmetic_offer_multiplier"]:.2f}'
    stylecss = '''<style>
      :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#081221;color:#e8f1fc;font-family:Inter,Arial,sans-serif}
      .page{max-width:1320px;margin:auto;padding:36px 28px 65px}.eyebrow{color:#38dfc2;text-transform:uppercase;letter-spacing:.22em;font-size:11px;font-weight:800}
      h1{font-size:36px;letter-spacing:-.035em;margin:13px 0 8px}p{color:#93a9c4;line-height:1.55}h2{font-size:22px;margin:12px 0}
      .top{display:flex;justify-content:space-between;align-items:start;gap:20px}.pill{padding:10px 15px;background:#12332f;border:1px solid #2b7268;border-radius:24px;color:#baf8ed;font-size:11px;white-space:nowrap;font-weight:700}
      .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:29px 0 22px}.metric{background:#101d32;border:1px solid #21344e;border-radius:14px;padding:19px 19px 17px}
      .metric .label{color:#90a7c2;font-size:12px}.metric .number{font-size:28px;font-weight:780;letter-spacing:-.03em;margin:10px 0 5px}.metric .detail{font-size:11px;color:#6bd8c3}
      .note{font-size:12px;color:#a2b6cc;background:#111d30;border-left:3px solid #39bea7;border-radius:5px;padding:13px 15px;margin:22px 0}
      .tabs{display:flex;gap:8px;margin:26px 0 21px;flex-wrap:wrap}.tab{cursor:pointer;background:#122139;color:#b9c9df;border:1px solid #2a3d56;border-radius:8px;padding:11px 15px;font-weight:700}.tab.active{background:#1c4f4b;color:#dcfff7;border-color:#47baab}
      .tab-panel{display:none}.tab-panel.active{display:block}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.plot-card,.table-card{background:#101a2e;border:1px solid #22314a;border-radius:16px;padding:10px 9px;overflow:hidden}
      .span-2{grid-column:span 2}.section-kicker{font-size:12px;color:#7bd8c6;font-weight:700;letter-spacing:.06em;margin:5px 0 15px;text-transform:uppercase}
      table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:13px 14px;border-bottom:1px solid #26364c}th{color:#a3bbd4;font-size:11px;text-transform:uppercase;background:#16253a}tr:last-child td{border-bottom:0}
      .selection{background:linear-gradient(100deg,#153d3c,#14253c);padding:20px;border:1px solid #346f68;border-radius:14px;margin:15px 0 20px}
      .selection b{color:#c5fff4}.footer{font-size:12px;color:#7992b0;margin-top:35px;border-top:1px solid #20314b;padding-top:18px}
      @media(max-width:850px){.page{padding:18px}.top{display:block}.metrics{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.span-2{grid-column:auto}h1{font-size:27px}}
    </style>'''
    doc = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Game Economy Simulator &amp; Optimizer</title>{stylecss}</head><body><div class="page">
    <div class="top"><div><div class="eyebrow">Game Economist · Portfolio Project 01 · Version 2</div><h1>Game Economy Simulator &amp; Optimizer</h1><p>From event-level virtual currency to constrained scenario search and holdout checks.</p></div><div class="pill">SYNTHETIC MODEL · NOT PLAYER DATA</div></div>
    <div class="metrics">
     <div class="metric"><div class="label">Holdout · upgrade affordability</div><div class="number">{recommended_gap:.1%}</div><div class="detail">{(recommended_gap-baseline_gap)*100:+.2f} percentage points vs baseline</div></div>
     <div class="metric"><div class="label">Holdout · upgrades / install</div><div class="number">{rec_upg:.2f}</div><div class="detail">{(rec_upg/base_upg-1)*100:+.1f}% vs baseline</div></div>
     <div class="metric"><div class="label">Holdout · survivor median wallet</div><div class="number">{r_wallet:.0f}</div><div class="detail">{r_wallet-b_wallet:+.0f} coins vs baseline</div></div>
     <div class="metric"><div class="label">Holdout · sources / sinks</div><div class="number">{r_ratio:.3f}</div><div class="detail">{r_ratio-b_ratio:+.3f} vs baseline</div></div>
    </div>
    <div class="note"><strong>Interpretation:</strong> All player behavior, currency flows and abandonment probabilities are assumed. Model comparisons reveal consequences of these assumptions — not measured player preference, causal uplift, real-world price elasticity or revenue performance.</div>
    <nav class="tabs"><button class="tab active" onclick="showTab('economy',this)">01 · Economy trends</button><button class="tab" onclick="showTab('optimization',this)">02 · Optimization</button><button class="tab" onclick="showTab('personas',this)">03 · Personas & archetypes</button><button class="tab" onclick="showTab('robustness',this)">04 · Robustness</button></nav>
    <section id="economy" class="tab-panel active"><div class="section-kicker">30-day fixed cohort · 5,000 simulated installs · four policies</div><div class="grid">{card(trend1,True)}{card(trend2)}<div class="span-2">{card(flow)}</div></div></section>
    <section id="optimization" class="tab-panel"><div class="section-kicker">27 predetermined combinations · 4 selection seeds · 4 separate holdout seeds</div><div class="selection"><b>Selected training candidate {html.escape(rec)}</b><p>{html.escape(selected_specs)}. Selection enforces preset limits on affordability, progression, median wallet, sources/sinks and Casual-player friction. The holdout was <b>not used</b> to select the candidate.</p></div><div class="grid"><div class="span-2">{card(frontier)}</div></div><h2>Holdout comparison</h2><div class="table-card" style="overflow-x:auto"><table><thead><tr><th>Metric</th><th>Baseline</th><th>Selected</th><th>Paired delta</th><th>Across-seed range</th><th>Unit</th></tr></thead><tbody>{''.join(vrows)}</tbody></table></div><p>Range = minimum to maximum paired differences across four simulation seeds, <b>not a confidence interval over actual players</b>.</p></section>
    <section id="personas" class="tab-panel"><div class="section-kicker">Behavioral segmentation · fixed assumed archetype shares</div><div class="grid">{card(pers)}{card(pg)}<div class="span-2">{card(pf)}</div></div></section>
    <section id="robustness" class="tab-panel"><div class="section-kicker">Assumption changes · deliberately outside the optimization search</div><div class="grid"><div class="span-2">{card(ss)}</div></div><div class="note">Stress cases alter the assumed activity rate, churn hazard, quest reward or upgrade price. They test fragility under alternate model assumptions, not how a production player population would respond.</div></section>
    <div class="footer">Reproducible synthetic game-economy portfolio · SQLite event log & wallet reconciliation · All metric definitions, seeds and model constraints are documented in the repository.</div>
    </div><script>function showTab(name,button){{document.querySelectorAll('.tab-panel').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.getElementById(name).classList.add('active');button.classList.add('active');setTimeout(()=>{{document.querySelectorAll('#'+name+' .js-plotly-plot').forEach(p=>{{if(window.Plotly)Plotly.Plots.resize(p)}})}},50)}}</script></body></html>'''
    out = RPT/'interactive_dashboard.html'
    out.write_text(doc,encoding='utf8')
    print(f'Wrote {out} ({out.stat().st_size/1e6:.1f} MB)')


if __name__=='__main__':
    main()
