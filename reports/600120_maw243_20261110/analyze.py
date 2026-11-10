"""Reproduce close/MAW243 deviation distribution using the app's local history."""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, MultipleLocator
from matplotlib.font_manager import FontProperties

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.indicators import calc_maw

source = ROOT / 'data/600120.csv'
df = pd.read_csv(source, dtype={'股票代码': str})
df['日期'] = pd.to_datetime(df['日期'], errors='raise')
assert not df['日期'].duplicated().any()
assert set(df['股票代码']) == {'600120'}
df = df.sort_values('日期').reset_index(drop=True)
for col in ['收盘', '收盘_未复权', '成交量', '成交额', '换手率']:
    df[col] = pd.to_numeric(df[col], errors='raise')
    assert np.isfinite(df[col]).all(), col
    assert (df[col] > 0).all(), col
assert set(df['volume_unit']) == {'shares'}
# Calculate on full history first: the first year of the requested window is NOT lost.
df['MAW243'] = calc_maw(df, 243)
end = pd.Timestamp('2026-11-10')
start = end - pd.DateOffset(years=10)
window = df.loc[df['日期'].between(start, end)].copy()
valid = window['MAW243'].notna() & (window['MAW243'] > 0)
sample = window.loc[valid].copy()
sample['偏离率'] = (sample['收盘'] - sample['MAW243']) / sample['MAW243']
sample['偏离率(%)'] = sample['偏离率'] * 100
x = sample['偏离率(%)']
assert len(sample) > 2000 and np.isfinite(x).all()
# Independent formula check, including full 243-row warm-up.
vwap = (df['成交额'] / df['成交量']) * df['收盘'] / df['收盘_未复权']
independent = (vwap * df['换手率']).rolling(243).sum() / df['换手率'].rolling(243).sum()
np.testing.assert_allclose(df['MAW243'], independent, rtol=1e-12, equal_nan=True)
last_idx = sample.index[-1]
w = df.loc[last_idx-242:last_idx]
manual_last = np.average((w['成交额']/w['成交量'])*(w['收盘']/w['收盘_未复权']), weights=w['换手率'])
assert np.isclose(manual_last, sample.iloc[-1]['MAW243'], rtol=1e-12)
quantiles = {f'p{p:02d}': float(x.quantile(p/100)) for p in [1,5,10,25,50,75,90,95,99]}
# Fixed 5-percentage-point bins, retaining both tails without clipping.
lo = int(np.floor(x.min()/5)*5)
hi = int(np.ceil(x.max()/5)*5)
edges = np.arange(lo, hi+5, 5, dtype=float)
counts, _ = np.histogram(x, bins=edges)
assert counts.sum() == len(sample)
bins = pd.DataFrame({'left_pct':edges[:-1], 'right_pct':edges[1:], 'count':counts, 'share':counts/len(sample)})
mode_idx = int(counts.argmax())
coarse_edges = [-np.inf,-30,-20,-10,0,10,20,30,np.inf]
coarse = []
for a,b in zip(coarse_edges[:-1],coarse_edges[1:]):
    c = int(((x >= a) & (x < b)).sum())
    coarse.append({'lower_pct':None if not np.isfinite(a) else a,'upper_pct':None if not np.isfinite(b) else b,'count':c,'share':c/len(x)})
assert sum(r['count'] for r in coarse) == len(x)
latest = sample.iloc[-1]
minrow = sample.loc[x.idxmin()]
maxrow = sample.loc[x.idxmax()]
summary = {
    'stock_code':'600120', 'formula':'(close - MAW243) / MAW243',
    'requested_start':str(start.date()),'requested_end':str(end.date()),
    'first_date':str(sample['日期'].min().date()),'last_date':str(sample['日期'].max().date()),
    'source_first':str(df['日期'].min().date()),'source_last':str(df['日期'].max().date()),
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'sample_size':len(sample),'excluded_invalid_maw':int((~valid).sum()),
    'mean_pct':float(x.mean()),'median_pct':float(x.median()),'std_pct':float(x.std(ddof=1)),
    'skewness':float(x.skew()),'excess_kurtosis':float(x.kurt()),
    'positive_share':float((x>0).mean()),'negative_share':float((x<0).mean()),'zero_share':float((x==0).mean()),
    'within_10pct_share':float((x.abs()<=10).mean()),'within_20pct_share':float((x.abs()<=20).mean()),
    'quantiles_pct':quantiles,
    'min':{'date':str(minrow['日期'].date()),'deviation_pct':float(minrow['偏离率(%)'])},
    'max':{'date':str(maxrow['日期'].date()),'deviation_pct':float(maxrow['偏离率(%)'])},
    'latest':{'date':str(latest['日期'].date()),'close':float(latest['收盘']),'maw243':float(latest['MAW243']),'deviation_pct':float(latest['偏离率(%)']),'historical_percentile':float((x<=latest['偏离率(%)']).mean()*100)},
    'modal_bin_pct':[float(edges[mode_idx]),float(edges[mode_idx+1])],
    'modal_bin_count':int(counts[mode_idx]),'modal_bin_share':float(counts[mode_idx]/len(x)),
    'coarse_bins':coarse,
    'maw_method':'243交易日每日前复权VWAP按换手率加权；使用窗口前历史预热；未四舍五入后计算',
    'notes':['目标窗口2016-11-10至2026-11-10；实际数据截至2026-11-05，未补造缺失日期。','本地缓存数据，与当前系统MAW计算口径一致；未独立核验供应商全量数据。','每个有效交易日等权，非自然日；区间两端均含。','经验分布不等于未来概率，滚动窗口重叠且日间观测不独立；不构成买卖阈值或均值回归保证。']
}
export = sample[['日期','收盘','收盘_未复权','MAW243','偏离率','偏离率(%)']].copy()
export['日期'] = export['日期'].dt.strftime('%Y-%m-%d')
export.to_csv(OUT/'daily_deviation.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
bins.to_csv(OUT/'histogram_bins.csv',index=False,encoding='utf-8-sig')
yearly = sample.assign(year=sample['日期'].dt.year).groupby('year')['偏离率(%)'].agg(['count','mean','median','min','max'])
yearly.to_csv(OUT/'yearly_summary.csv',encoding='utf-8-sig')
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

font_path = Path('C:/Windows/Fonts/msyh.ttc')
assert font_path.exists(), 'Chinese font unavailable'
font = FontProperties(fname=str(font_path))
plt.rcParams['font.family'] = font.get_name()
plt.rcParams['axes.unicode_minus'] = False
fig = plt.figure(figsize=(14,9),facecolor='#f6f8fc')
gs = fig.add_gridspec(2,1,height_ratios=[3.1,1.35],hspace=.48,left=.08,right=.96,top=.81,bottom=.15)
ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
for axis in [ax,ax2]:
    axis.set_facecolor('#ffffff')
    axis.spines[['top','right']].set_visible(False)
    axis.spines[['bottom','left']].set_color('#cbd5e1')
    axis.tick_params(colors='#475569',labelsize=10)
fig.text(.08,.95,'600120  |  收盘价相对 MAW243 的十年偏离分布',fontsize=21,weight='bold',color='#14263d',fontproperties=font)
fig.text(.08,.905,f'{sample["日期"].min().date()} — {sample["日期"].max().date()} · {len(x):,} 个有效交易日 · 偏离率 = (收盘价 − MAW243) / MAW243 × 100%',fontsize=11,color='#52647b',fontproperties=font)
fig.text(.08,.857,f'均值 {x.mean():+.2f}%     中位数 {x.median():+.2f}%     低于 MAW243 {(x<0).mean():.1%}     ±10% 内 {(x.abs()<=10).mean():.1%}',fontsize=12,color='#243b53',fontproperties=font)
centers=(edges[:-1]+edges[1:])/2
colors=['#cf8b45' if c<0 else '#397c96' for c in centers]
ax.bar(centers,counts/len(x),width=4.65,color=colors,edgecolor='white',linewidth=.5,zorder=3)
ax.axvline(0,color='#334155',linewidth=1.2,label='MAW243 基准（0%）')
ax.axvline(x.median(),color='#7b4ab3',linestyle='--',linewidth=1.7,label=f'中位数 {x.median():+.2f}%')
ax.axvline(x.mean(),color='#c44d69',linestyle=':',linewidth=1.7,label=f'均值 {x.mean():+.2f}%')
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.xaxis.set_major_formatter(PercentFormatter(100,decimals=0))
ax.xaxis.set_major_locator(MultipleLocator(10 if hi-lo<150 else 20))
ax.set_xlim(lo-1,hi+1)
ax.set_ylabel('交易日占比',fontproperties=font)
ax.set_title('频率直方图｜每档 5 个百分点，完整保留左右尾部',loc='left',fontsize=12,pad=12,fontproperties=font)
ax.grid(axis='y',alpha=.15,zorder=0)
ax.legend(frameon=False,prop=font,loc='upper right')
ax2.plot(np.sort(x),np.arange(1,len(x)+1)/len(x),color='#397c96',linewidth=2)
ax2.axhline(.5,color='#94a3b8',linestyle=':',linewidth=1)
ax2.axvspan(quantiles['p05'],quantiles['p95'],color='#397c96',alpha=.10,label=f'中央90%区间：{quantiles["p05"]:+.1f}% 至 {quantiles["p95"]:+.1f}%')
ax2.axvline(0,color='#334155',linewidth=1)
ax2.set_xlim(ax.get_xlim()); ax2.set_ylim(0,1.02)
ax2.yaxis.set_major_formatter(PercentFormatter(1));ax2.xaxis.set_major_formatter(PercentFormatter(100,decimals=0))
ax2.set_ylabel('累计交易日占比',fontproperties=font)
ax2.set_xlabel('收盘价相对 MAW243 的偏离率（%）',fontproperties=font,labelpad=8)
ax2.legend(frameon=False,prop=font,loc='lower right');ax2.grid(alpha=.12)
fig.text(.08,.065,'口径：系统本地日线；前复权 VWAP 按换手率加权；243 交易日滚动；使用十年窗口之前的数据预热。',fontsize=10,color='#64748b',fontproperties=font)
fig.text(.08,.033,'说明：历史频率不等于未来概率；每日样本相互关联，偏离本身不代表必然回归或买卖信号。',fontsize=10,color='#64748b',fontproperties=font)
fig.savefig(OUT/'histogram.png',dpi=180,facecolor=fig.get_facecolor())
plt.close(fig)
print(json.dumps(summary,ensure_ascii=True,indent=2))
print('VERIFIED: independent MAW formula, last-window weighted average, complete histogram counts.')
