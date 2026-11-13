"""Optional GitHub-facing PNG summary; requires matplotlib."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
ROOT=Path(__file__).resolve().parents[1]
v=pd.read_csv(ROOT/'data/optimizer_validation_summary.csv').set_index('metric')
c=pd.read_csv(ROOT/'data/optimizer_candidates.csv')
d=pd.read_csv(ROOT/'data/daily_metrics.csv')
fig=plt.figure(figsize=(14,8.2),dpi=160,facecolor='#081221')
gs=GridSpec(8,12,figure=fig,left=.055,right=.965,top=.75,bottom=.10,wspace=.55,hspace=1.0)
fig.text(.055,.94,'GAME ECONOMY · BALANCING LAB',fontweight='bold',fontsize=23,color='#edf7ff')
fig.text(.055,.895,'Model-driven currency, progression and constrained search',fontsize=12,color='#96abc4')
fig.text(.055,.855,'SYNTHETIC MODEL  /  5,000 simulated installs  /  30 days  /  27 optimization candidates',fontsize=9,color='#35d4b7')
ax1=fig.add_subplot(gs[0:4,0:7]);ax2=fig.add_subplot(gs[0:4,7:12]);ax3=fig.add_subplot(gs[5:8,0:12])
for ax in (ax1,ax2,ax3):
    ax.set_facecolor('#101c30');ax.tick_params(colors='#b4c6dd',labelsize=9)
    for sp in ax.spines.values():sp.set_color('#2a3a51')
    ax.grid(True,color='#24364e',alpha=.7);ax.set_axisbelow(True)
for scenario,color in [('Baseline','#708cb2'),('Reward +25%','#41d2ba'),('Upgrade Price +25%','#f1b477'),('Targeted Sink +30%','#bb94ee')]:
    sub=d[d.scenario==scenario]
    ax1.plot(sub.day,sub.cumulative_upgrades_per_install,label=scenario,lw=2.3,color=color)
ax1.set_title('PROGRESSION BY SCENARIO',color='#e6f2ff',loc='left',fontsize=11,pad=15,fontweight='bold')
ax1.set_xlabel('Days since install',color='#97aec7');ax1.set_ylabel('Upgrades per install',color='#97aec7')
ax1.legend(loc='upper left',fontsize=8,frameon=False,labelcolor='#c2d5e8')
ax2.scatter(c.affordability_gap_active_pct*100,c.avg_upgrades_per_install,c=np.where(c.feasible,'#38cbb3','#62758a'),s=45,alpha=.9)
rec=c.loc[c.objective_score.idxmax()]  # Highlight winner among feasible in this build.
assert bool(rec.feasible)
ax2.scatter([rec.affordability_gap_active_pct*100],[rec.avg_upgrades_per_install],marker='*',s=300,color='#facb75',edgecolors='white',zorder=10)
ax2.annotate(f'selected {rec.candidate}',(rec.affordability_gap_active_pct*100,rec.avg_upgrades_per_install),xytext=(8,10),textcoords='offset points',color='#facb75',fontsize=9)
ax2.set_title('CONSTRAINED GRID SEARCH',color='#e6f2ff',loc='left',fontsize=11,pad=15,fontweight='bold')
ax2.set_xlabel('Active days with upgrade friction (%)',color='#97aec7');ax2.set_ylabel('Upgrades / install',color='#97aec7')
ax3.axis('off')
metrics=[('affordability_gap_active_pct','Upgrade friction','pp',100,True),
         ('avg_upgrades_per_install','Upgrades / install','',1,False),
         ('source_to_sink_ratio','Sources / sinks','',1,True),
         ('surplus_active_pct','Surplus wallet days','pp',100,True)]
for i,(key,label,unit,mult,lower_better) in enumerate(metrics):
    xx=.02+i*.246
    rec_box=FancyBboxPatch((xx,.09),.225,.78,boxstyle='round,pad=.01,rounding_size=.024',transform=ax3.transAxes,
                            facecolor='#162944',edgecolor='#2c415c',lw=1)
    ax3.add_patch(rec_box)
    row=v.loc[key];change=row.paired_delta_mean*mult
    ax3.text(xx+.022,.65,label,transform=ax3.transAxes,color='#a2b7d2',fontsize=9)
    good=(change<0) if lower_better else (change>0)
    ax3.text(xx+.022,.34,f'{change:+.2f} {unit}',transform=ax3.transAxes,
             color='#59dcc8' if good else '#efb178',fontsize=18,fontweight='bold')
    ax3.text(xx+.022,.18,'paired holdout Δ',transform=ax3.transAxes,color='#8ba2ba',fontsize=8)
fig.text(.055,.035,'All outcomes are synthetic assumptions — not observed player data or measured causal effects.',color='#9bb0c8',fontsize=9)
fig.savefig(ROOT/'reports/preview.png',dpi=160,facecolor='#081221')
plt.close(fig)
print('Saved reports/preview.png')
