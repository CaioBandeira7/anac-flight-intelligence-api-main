"""Charts for the portfolio. Every value is copied from a cited source; nothing is computed beyond sums."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["Regular","Medium","SemiBold","Bold"]:
    fm.fontManager.addfont(f"/usr/share/fonts/opentype/inter/Inter-{f}.otf")
plt.rcParams.update({"font.family":"Inter","font.size":13,"axes.spines.top":False,"axes.spines.right":False,
    "axes.edgecolor":"#9aa6b8","axes.labelcolor":"#3b4658","xtick.color":"#56627a","ytick.color":"#56627a",
    "axes.titleweight":"semibold","axes.titlesize":15})
INK="#16213a"; MUTED="#56627a"; BLUE="#1f5fd6"; GRAY="#9aa6b8"; LIGHT="#c9d4ea"
OUT=Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SRC="Fonte: API pública /v2/analytics/routes/monthly (2000-01 a 2025-12), consultada em 2026-11-08"

# 1. Annual paid passengers. Source: sums of the monthly points served by the live API.
raw="2000,44241313,12;2001,46210058,12;2002,45477067,12;2003,42785542,12;2004,46508195,12;2005,55340700,12;2006,60301724,12;2007,65542528,12;2008,69136889,12;2009,75805715,12;2010,91786042,12;2011,107204996,12;2012,114068363,12;2013,115078651,12;2014,122440050,12;2015,112084161,11;2016,102707260,11;2017,114319888,12;2018,108191714,11;2019,120692377,12;2020,49453767,11;2021,67772887,12;2022,98610803,12;2023,113739831,12;2024,119933691,12;2025,131593763,12"
rows=[r.split(",") for r in raw.split(";")]
years=[int(r[0]) for r in rows]; pax=[int(r[1])/1e6 for r in rows]; months=[int(r[2]) for r in rows]
fig,ax=plt.subplots(figsize=(12,5.6),dpi=160)
colors=[BLUE if m==12 else LIGHT for m in months]
bars=ax.bar(years,pax,color=colors,width=0.72,edgecolor="white",linewidth=1)
for b,m in zip(bars,months):
    if m<12: b.set_hatch("///"); b.set_edgecolor(BLUE)
ax.set_ylabel("Passageiros pagos (milhões)")
ax.set_title("Passageiros pagos por ano no Brasil, 2000–2025",loc="left",color=INK,pad=14)
ax.grid(axis="y",color="#e3e8f2",linewidth=1); ax.set_axisbelow(True)
ax.set_xticks(years[::5]+[2025])
ax.annotate("131,6 mi em 2025",(2025,pax[-1]),xytext=(2019.2,141),fontsize=12,color=INK,
            arrowprops=dict(arrowstyle="-",color=MUTED,lw=1))
ax.set_ylim(0,150)
ax.text(0,-0.16,"Barras hachuradas: anos com um mês ausente na fonte (2015-08, 2016-02, 2018-07, 2020-08), somados sobre 11 meses.\n"+SRC,
        transform=ax.transAxes,fontsize=10,color=MUTED,va="top")
fig.tight_layout(); fig.savefig(OUT/"annual-paid-passengers-2000-2025.png",bbox_inches="tight"); plt.close(fig)

# 2. Validation 2023: selected/LightGBM vs best baseline. Source: research/ml-showcase/REPORT.md, summary table.
tasks=[("A · Movimentos por aeroporto/dia","WAPE (%)",10.10,10.30,"Sem ganho conclusivo\n(IC 95% −0,84 a +0,35)"),
       ("B · Ocupação por rota/empresa","MAE ponderado (pts)",6.06,6.54,"Ganho conclusivo\n−0,48 pts (−0,94 a −0,04)"),
       ("D · Passageiros por rota/mês","WAPE (%)",22.24,25.31,"Ganho conclusivo, −3,07 pts\nviés ≈ −12%"),
       ("D · Assentos por rota/mês","WAPE (%)",22.40,25.73,"Ganho conclusivo, −3,33 pts")]
fig,axes=plt.subplots(1,4,figsize=(15,5.2),dpi=160)
for ax,(t,unit,m,b,verdict) in zip(axes,tasks):
    bs=ax.bar([0,1],[m,b],color=[BLUE,GRAY],width=0.6)
    for x,v in zip([0,1],[m,b]):
        ax.text(x,v*1.02,f"{v:.2f}".replace(".",","),ha="center",va="bottom",fontsize=13,color=INK,fontweight="semibold")
    ax.set_xticks([0,1],["LightGBM","Melhor\nbaseline"]); ax.set_ylim(0,max(m,b)*1.32)
    ax.set_title(t,loc="left",fontsize=12.5,color=INK); ax.set_ylabel(unit,fontsize=11)
    ax.text(0.5,-0.24,verdict,transform=ax.transAxes,ha="center",fontsize=10.5,color=MUTED,va="top")
    ax.grid(axis="y",color="#e3e8f2"); ax.set_axisbelow(True)
fig.suptitle("Validação 2023 (dados não vistos no treino): menor é melhor",x=0.01,ha="left",fontsize=16,fontweight="semibold",color=INK)
fig.text(0.01,-0.02,"Fonte: research/ml-showcase/REPORT.md e results/analysis.json. Resultados de validação, não previsões; o teste 2024–2025 não foi executado. "
         "No módulo A o baseline é o método adotado.",fontsize=10,color=MUTED)
fig.tight_layout(); fig.savefig(OUT/"ml-validation-2023-vs-baselines.png",bbox_inches="tight"); plt.close(fig)

# 3. Model D (passengers) by horizon. Source: results/analysis.json tasks.d_pax.by_horizon.
a=json.load(open(sys.argv[2]))["tasks"]["d_pax"]["by_horizon"]
h=[r["horizon"] for r in a]; model=[r["model"]*100 for r in a]; best=[min(r["baselines"].values())*100 for r in a]
fig,ax=plt.subplots(figsize=(9,5.2),dpi=160)
ax.plot(h,model,color=BLUE,lw=2.4,marker="o",ms=9,label="LightGBM")
ax.plot(h,best,color=GRAY,lw=2.4,marker="o",ms=9,ls="--",label="Melhor baseline")
for x,v,bb in zip(h,model,best): ax.text(x,(v+0.9) if v>bb else (v-1.3),f"{v:.1f}%".replace(".",","),ha="center",va="bottom" if v>bb else "top",color=BLUE,fontsize=12,fontweight="semibold")
for x,v,mm in zip(h,best,model): ax.text(x,(v-1.0) if mm>v else (v+0.9),f"{v:.1f}%".replace(".",","),ha="center",va="top" if mm>v else "bottom",color=MUTED,fontsize=12)
ax.set_xticks(h,[f"{x} {'mês' if x==1 else 'meses'}" for x in h]); ax.set_xlim(0.5,6.5); ax.set_ylim(14,30)
ax.set_ylabel("WAPE (%)"); ax.grid(axis="y",color="#e3e8f2"); ax.set_axisbelow(True)
ax.set_title("Módulo D: demanda por rota, erro por horizonte (validação 2023)",loc="left",color=INK,pad=12)
ax.legend(frameon=False,loc="upper left")
ax.text(0,-0.17,"Melhor baseline em cada horizonte (mesmo mês do ano anterior, com ou sem tendência).\nGanha em 1 e 3 meses; em 6 meses fica pior.\nFonte: research/ml-showcase/results/analysis.json (tasks.d_pax.by_horizon).",
        transform=ax.transAxes,fontsize=10,color=MUTED,va="top")
fig.tight_layout(); fig.savefig(OUT/"ml-model-d-error-by-horizon.png",bbox_inches="tight"); plt.close(fig)
print([ (x,round(m,2),round(b,2)) for x,m,b in zip(h,model,best)])
