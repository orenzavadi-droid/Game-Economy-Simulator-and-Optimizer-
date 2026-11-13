"""Optional workbook export using artifact_tool.

The XLSX is a snapshot, not an independent simulation; recompute with
python -m src.run_analysis before regenerating it.
"""
from pathlib import Path
import csv
import json
from artifact_tool import Workbook, SpreadsheetFile

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; REPORTS=ROOT/'reports'
NAVY='#11243F'; NAVY2='#173353'; TEAL='#0D9488'; GREEN='#DDF7F1'
INK='#11243F'; SLATE='#60718A'; WHITE='#FFFFFF'; PALE='#EAF1F8'


def rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(v):
    if v is None or v == '': return None
    if str(v).lower() == 'true': return 'Yes'
    if str(v).lower() == 'false': return 'No'
    try: return float(v)
    except ValueError: return str(v)


def write_table(sheet, firstrow, headers, values, widths=None):
    n=len(headers)
    end=firstrow+len(values)
    sheet.get_range_by_indexes(firstrow-1,0,1,n).values=[headers]
    if values:
        sheet.get_range_by_indexes(firstrow,0,len(values),n).values=values
    sheet.get_range_by_indexes(firstrow-1,0,1,n).format={
        'fill':NAVY2, 'font':{'color':WHITE,'bold':True,'size':11},
        'row_height':28, 'vertical_alignment':'center'}
    sheet.get_range_by_indexes(firstrow,0,max(1,len(values)),n).format.row_height=22
    sheet.freeze_panes.freeze_rows(firstrow)
    if widths:
        for i,w in enumerate(widths):
            sheet.get_range_by_indexes(0,i,max(end+2,10),1).format.column_width=w


def title(sheet, heading, sub, end='H'):
    sheet.merge_cells(f'A1:{end}2')
    sheet.get_range('A1').values=[[heading]]
    sheet.get_range(f'A1:{end}2').format={'fill':NAVY,'font':{'color':WHITE,'bold':True,'size':19},
          'row_height':26,'vertical_alignment':'center'}
    sheet.merge_cells(f'A3:{end}3')
    sheet.get_range('A3').values=[[sub]]
    sheet.get_range(f'A3:{end}3').format={'fill':PALE,'font':{'color':INK,'size':10},'row_height':25}


def main():
    wb=Workbook.create()
    summary=rows(DATA/'optimizer_validation_summary.csv')
    summary_index={row['metric']:row for row in summary}
    scenarios=rows(DATA/'scenario_summary.csv')
    candidates=rows(DATA/'optimizer_candidates.csv')
    personas=rows(DATA/'persona_metrics.csv')
    daily=rows(DATA/'daily_metrics.csv')
    profiles=rows(DATA/'profile_comparison.csv')
    selection=json.loads((REPORTS/'optimization_selection.json').read_text())

    overview=wb.worksheets.add('EXECUTIVE SCORECARD')
    title(overview,'GAME ECONOMY | BALANCING LAB 2.0',
          'HOLDOUT SIMULATION • synthetic assumptions • 4 matched seed pairs')
    overview.get_range('A5:G5').values=[['Game economy health metric','Baseline','Selected','Paired delta','Minimum delta','Maximum delta','Unit']]
    overview.get_range('A5:G5').format={'fill':TEAL,'font':{'bold':True,'color':WHITE},'row_height':26}
    specs=[('affordability_gap_active_pct','Upgrade affordability gap','percentage points',100),
           ('avg_upgrades_per_install','Upgrades per install','upgrades / install',1),
           ('median_wallet_survivors_day_end','Survivor median wallet','soft coins',1),
           ('source_to_sink_ratio','Sources / sinks','ratio',1),
           ('sink_utilization','Sink utilization','percentage points',100),
           ('surplus_active_pct','Surplus play-days','percentage points',100),
           ('d7_retention','D7 exact-day return','percentage points',100)]
    for idx,(metric,lab,unit,multiplier) in enumerate(specs, start=6):
        r=summary_index[metric]
        overview.get_range(f'A{idx}:C{idx}').values=[[lab,float(r['baseline_mean'])*multiplier,float(r['recommended_mean'])*multiplier]]
        overview.get_range(f'D{idx}').formulas=[[f'=C{idx}-B{idx}']]
        overview.get_range(f'E{idx}:G{idx}').values=[[float(r['delta_min'])*multiplier,float(r['delta_max'])*multiplier,unit]]
    overview.get_range('B6:F12').set_number_format('0.00;[Red](0.00)')
    overview.get_range('A6:A12').format.font.bold=True
    overview.get_range('A6:G12').format.row_height=25
    overview.get_range('A15:G15').merge()
    overview.get_range('A15').values=[['TRAINING SELECTION — transparent guardrails']]
    overview.get_range('A15:G15').format={'fill':NAVY2,'font':{'color':WHITE,'bold':True},'row_height':26}
    overview.get_range('A17:B21').values=[
        ['Candidate ID',selection['selected_candidate']],
        ['Quest reward multiplier',selection['reward_multiplier']],
        ['Upgrade price multiplier',selection['upgrade_price_multiplier']],
        ['Optional sink offer multiplier',selection['cosmetic_offer_multiplier']],
        ['Training / holdout seeds','4 / 4 (disjoint)']]
    overview.get_range('A24:G25').merge()
    overview.get_range('A24').values=[['MODEL POLICY: synthetic data, assumed player behavior. No empirical causality, real-money pricing, or revenue estimates. This workbook is a snapshot; edit Python configuration to rerun the model.']]
    overview.get_range('A24:G25').format={'fill':PALE,'font':{'color':INK,'size':10},'wrap_text':True,'row_height':24}
    for c,w in zip('ABCDEFG',[35,17,17,16,17,17,24]):overview.get_range(f'{c}:{c}').format.column_width=w

    sc=wb.worksheets.add('SCENARIO COMPARISON')
    title(sc,'FOUR ECONOMY SCENARIOS','30 simulated days × 5,000 installs per scenario')
    fields=[('scenario','Scenario'),('d7_retention','D7 return'),('avg_upgrades_per_install','Upgrades / install'),
            ('affordability_gap_active_pct','Upgrade gap'),('source_to_sink_ratio','Sources / sinks'),
            ('median_wallet_survivors_day_end','Survivor wallet'),('earned_coins','Sources (coins)'),('spent_coins','Sinks (coins)')]
    write_table(sc,5,[x[1] for x in fields],[[num(d[f]) for f,_ in fields] for d in scenarios],
                [28,16,19,18,18,20,20,20])
    sc.get_range('B6:B9').set_number_format('0.0%');sc.get_range('D6:D9').set_number_format('0.0%')
    sc.get_range('G6:H9').set_number_format('#,##0')

    op=wb.worksheets.add('OPTIMIZATION GRID')
    title(op,'CONSTRAINED ECONOMY SEARCH','27 fixed combinations • 4 training seeds • Pareto frontier • selected candidate from training only','K')
    op_fields=[('candidate','Candidate'),('reward_multiplier','Reward ×'),('upgrade_price_multiplier','Upgrade ×'),
               ('cosmetic_offer_multiplier','Sink offer ×'),('affordability_gap_active_pct','Upgrade gap'),
               ('avg_upgrades_per_install','Upgrades / install'),('median_wallet_survivors_day_end','Median wallet'),
               ('surplus_active_pct','Surplus share'),('objective_score','Decision score'),
               ('feasible','Pass guardrails'),('pareto_efficient','Pareto frontier')]
    write_table(op,5,[v for _,v in op_fields],[[num(d[k]) for k,_ in op_fields] for d in candidates],
                [14,13,13,15,16,21,18,17,17,18,18])
    op.get_range('E6:E32').set_number_format('0.0%');op.get_range('H6:H32').set_number_format('0.0%')
    op.get_range('I6:I32').set_number_format('0.00')
    op.get_range('A6:K32').conditional_formats.add_custom('=$A6="'+selection['selected_candidate']+'"',{'fill':GREEN})

    ps=wb.worksheets.add('PERSONA ANALYSIS')
    title(ps,'PLAYER PERSONAS','Casual / Regular / Engaged · D7 slice only, model-defined archetypes')
    p7=[r for r in personas if int(r['day'])==7]
    p_fields=[('scenario','Scenario'),('persona','Persona'),('cohort_size','Installs'),('retention','D7 return'),
              ('avg_upgrades_per_install','Upgrades / install'),('affordability_gap_active_pct','Day7 upgrade gap'),
              ('median_wallet_survivors','Survivor median wallet')]
    write_table(ps,5,[x[1] for x in p_fields],[[num(d[f]) for f,_ in p_fields] for d in p7],[28,17,14,17,22,22,23])
    ps.get_range('D6:D17').set_number_format('0.0%');ps.get_range('F6:F17').set_number_format('0.0%')

    dt=wb.worksheets.add('DAILY TRENDS')
    title(dt,'DAILY COHORT ECONOMY','Day 1 to Day 30 · fixed original install cohort','H')
    # Wide pivot, charts appear to right without blocking data.
    names=[x['scenario'] for x in scenarios]
    hdr=['Day']+[f'Upgrade gap — {name}' for name in names]+[f'Progression — {name}' for name in names]
    values=[]
    dm={(r['scenario'],int(r['day'])):r for r in daily}
    for day in range(1,31):
        values.append([day]+[float(dm[(name,day)]['affordability_gap_active_pct']) for name in names]
                    +[float(dm[(name,day)]['cumulative_upgrades_per_install']) for name in names])
    write_table(dt,5,hdr,values,[12]+[30]*8)
    dt.get_range('B6:E35').set_number_format('0.0%')
    c1=dt.charts.add('line',{'title':'Upgrade affordability by day','has_legend':True})
    for ix,name in enumerate(names):
        series=c1.series.add(name)
        col='BCDE'[ix]
        series.category_formula="'DAILY TRENDS'!$A$6:$A$35"
        series.formula=f"'DAILY TRENDS'!${col}$6:${col}$35"
    c1.set_position('K5','S20')
    c2=dt.charts.add('line',{'title':'Cumulative upgrades per install','has_legend':True})
    for ix,name in enumerate(names):
        series=c2.series.add(name)
        col='FGHI'[ix]
        series.category_formula="'DAILY TRENDS'!$A$6:$A$35"
        series.formula=f"'DAILY TRENDS'!${col}$6:${col}$35"
    c2.set_position('K22','S37')

    ar=wb.worksheets.add('ARCHETYPES & AUDIT')
    title(ar,'ARCHETYPES & DATA INTEGRITY','Illustrative presets only · SQLite coin ledger reconciles every simulated player')
    ar_fields=[('scenario','Archetype'),('avg_upgrades_per_install','Upgrades / install'),
               ('affordability_gap_active_pct','Upgrade gap'),('source_to_sink_ratio','Sources / sinks'),
               ('median_wallet_survivors_day_end','Survivor wallet')]
    write_table(ar,6,[x[1] for x in ar_fields],[[num(d[f]) for f,_ in ar_fields] for d in profiles],[27,25,18,20,22])
    ar.get_range('C7:C9').set_number_format('0.0%')
    audit_rows=rows(REPORTS/'sql_outputs'/'04_wallet_reconciliation.csv')
    mismatch=sum(abs(float(x['wallet_difference']))>1e-7 for x in audit_rows)
    ar.get_range('A12:B16').values=[['SQL currency ledger audit','Result'],['Checked players',len(audit_rows)],
                                   ['Unreconciled wallets',mismatch],['Reconciliation status','PASS' if mismatch==0 else 'FAIL'],
                                   ['Currency audit rule','initial wallet + all event deltas = ending wallet']]
    ar.get_range('A12:B12').format={'fill':TEAL,'font':{'bold':True,'color':WHITE},'row_height':25}
    ar.get_range('A19:E21').merge()
    ar.get_range('A19').values=[['All event rows are synthetic and originate from the model. The SQLite database, SQL source queries, and per-player audit output are packaged alongside this Excel summary.']]
    ar.get_range('A19:E21').format={'fill':PALE,'wrap_text':True,'font':{'size':10,'color':INK}}

    wb.inspect({'kind':'table','range':'EXECUTIVE SCORECARD!A5:G12','include':'values,formulas',
                'table_max_rows':10,'table_max_cols':7})
    target=REPORTS/'Economy_Scenario_Workbook.xlsx'
    SpreadsheetFile.export_xlsx(wb).save(str(target))
    print('Wrote',target, target.stat().st_size)
    try:
        snap=wb.render({'sheet_name':'EXECUTIVE SCORECARD','range':'A1:G25','scale':1.4})
        snap.save(str(REPORTS/'excel_preview.png'))
    except Exception as exc:
        print('Optional preview unavailable:',repr(exc))


if __name__=='__main__':main()
