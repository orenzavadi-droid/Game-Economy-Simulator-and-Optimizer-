"""Optional live Streamlit what-if simulator (pip install streamlit)."""
from dataclasses import replace
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from src.economy import EconomyConfig, simulate

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Game Economy Balancing Lab',page_icon='🎮',layout='wide')
st.title('🎮 Game Economy · What-if Lab')
st.caption('Portfolio project 01 · synthetic cohort economics · no actual human-player or revenue data')
st.warning('Model-only sensitivity. None of these settings are calibrated to real player behavior or show measured causal uplift.',icon='⚠️')
with st.sidebar:
    st.header('Adjust the policy')
    rewards=st.slider('Quest reward multiplier',0.60,1.50,1.00,0.05)
    upgrade=st.slider('Upgrade price multiplier',0.65,1.50,1.00,0.05)
    sink=st.slider('Optional cosmetic offer ×',0.50,2.00,1.00,0.05)
    profile=st.selectbox('Illustrative progression profile',['Balanced casual','Fast progression','Scarce resources'])
    cohort=st.select_slider('Synthetic original installs',options=[500,1000,2500,5000,10000],value=5000)
    seed=int(st.number_input('Random seed',min_value=0,max_value=4294967295,value=20261112,step=1))
    st.caption('Changes to this interactive sandbox do not rewrite the packaged fixed-seed optimization results.')
presets=json.loads((ROOT/'config/profiles.json').read_text())['profiles']
base=EconomyConfig(n_players=cohort,seed=seed,**presets[profile])
custom=replace(base,scenario='Custom',reward_multiplier=rewards,
               upgrade_price_multiplier=upgrade,cosmetic_offer_multiplier=sink)
@st.cache_data(show_spinner=False)
def simulate_cached(conf: EconomyConfig):return simulate(conf)
base_day,base_summary,base_persona=simulate_cached(base)
custom_day,custom_summary,custom_persona=simulate_cached(custom)
base_day=base_day.assign(scenario='Baseline')
base_summary=base_summary.assign(scenario='Baseline')
base_persona=base_persona.assign(scenario='Baseline')
combined=pd.concat([base_day,custom_day],ignore_index=True)
cols=st.columns(4)
for col,caption,metric,percent in zip(cols,['Upgrades / install','Affordability gap','Sources / sinks','Surplus play-days'],
                                      ['avg_upgrades_per_install','affordability_gap_active_pct',
                                       'source_to_sink_ratio','surplus_active_pct'],[False,True,False,True]):
    a=float(base_summary[metric].iloc[0]);b=float(custom_summary[metric].iloc[0]);diff=b-a
    col.metric(caption,f'{b:.1%}' if percent else f'{b:.2f}',
               (f'{100*diff:+.2f} pp' if percent else f'{diff:+.2f}')+' vs baseline',delta_color='off')
tab1,tab2,tab3=st.tabs(['📈 Player progression & currency','👥 Persona fairness','📋 Model result & disclaimers'])
with tab1:
    l,r=st.columns(2)
    with l:
        st.plotly_chart(px.line(combined,x='day',y='cumulative_upgrades_per_install',color='scenario',
                               title='Cumulative upgrades / original install'),use_container_width=True)
        st.plotly_chart(px.line(combined,x='day',y='median_wallet_survivors',color='scenario',
                               title='Survivor median wallet'),use_container_width=True)
    with r:
        st.plotly_chart(px.line(combined,x='day',y='affordability_gap_active_pct',color='scenario',
                               title='Active play-days without an affordable upgrade'),use_container_width=True)
        st.plotly_chart(px.line(combined,x='day',y='retention',color='scenario',
                               title='Synthetic exact-day cohort returns'),use_container_width=True)
with tab2:
    both=pd.concat([base_persona,custom_persona],ignore_index=True)
    segment=both.groupby(['scenario','persona']).apply(lambda g: pd.Series({
        'affordability_gap':float((g.affordability_gap_active_pct*g.active_players).sum() / max(1,g.active_players.sum())),
        'd7_return':float(g.loc[g.day==7,'retention'].iloc[0])}),include_groups=False).reset_index()
    st.plotly_chart(px.bar(segment,x='persona',y='affordability_gap',color='scenario',barmode='group',
                           title='Affordability gap by persona'),use_container_width=True)
    st.dataframe(segment,use_container_width=True,hide_index=True)
with tab3:
    st.dataframe(pd.concat([base_summary,custom_summary],ignore_index=True),use_container_width=True,hide_index=True)
    st.download_button('Download comparison CSV',combined.to_csv(index=False),'what_if_daily.csv','text/csv')
    st.markdown('**Important:** This simulator is not a validated live-game forecast. The hard-coded player archetypes, upgrade preferences, inactivity process and currency mechanics are assumptions. Without real telemetry, you cannot infer causal impact, revenue optimization, or genuine human price sensitivity.')
