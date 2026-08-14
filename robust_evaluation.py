import json, pathlib, shutil, sys
import numpy as np
import pandas as pd
sys.path.insert(0,'/home/ubuntu/Ai_content_studio')
from research_engine import Config, ResearchEngine
from ml_walk_forward import MLConfig, run, net_sharpe

root=pathlib.Path('/home/ubuntu/robust_evaluation_runs'); shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
all_summaries=[]
for mult in [1.0, 2.0, 3.0]:
    cfg=MLConfig(horizon=6, windows=8, train_bars=1440, validation_bars=240, test_bars=240,
                 fee_bps=6.0*mult, slippage_bps=4.0*mult, feature_mode='liquidity',
                 target_cost_adjusted=True, uncertainty_multiple=0.5)
    out=root/f'cost_{int(mult)}x'; _, summary=run('/home/ubuntu/btcusdt_long_sample.csv', out, cfg)
    s=summary.copy(); s.insert(0,'cost_multiple',mult); all_summaries.append(s)
summary=pd.concat(all_summaries,ignore_index=True); summary.to_csv('/home/ubuntu/robust_ml_summary.csv',index=False)
print(summary.round(6).to_string(index=False))
# Simple non-trading and buy-and-hold reference on the same independent 6-bar samples.
e=ResearchEngine(Config(feature_mode='liquidity')); raw=e.load('/home/ubuntu/btcusdt_long_sample.csv'); close=raw.close; gross=close.shift(-6)/close-1; gross=gross.dropna().iloc[::6].to_numpy()
refs=[]
for mult in [1.0,2.0,3.0]:
    cost=(6+4)*mult/10000; b=gross.copy(); b[0]-=cost
    refs.append({'cost_multiple':mult,'no_trade_sharpe':0.0,'buy_hold_sharpe_net':net_sharpe(b,24*365/6),'buy_hold_return_net':float(np.prod(1+b)-1),'observations':len(b)})
pd.DataFrame(refs).to_csv('/home/ubuntu/robust_baselines.csv',index=False); print(pd.DataFrame(refs).round(6).to_string(index=False))
