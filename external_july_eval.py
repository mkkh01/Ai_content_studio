import json, pathlib, sys
import numpy as np, pandas as pd
sys.path.insert(0,'/home/ubuntu/Ai_content_studio')
from research_engine import Config, ResearchEngine
from ml_walk_forward import MLConfig, model_candidates, executable_target, score_predictions

cfg=MLConfig(horizon=6, execution_delay=1, train_bars=1440, validation_bars=240, fee_bps=6, slippage_bps=4, feature_mode='liquidity', target_cost_adjusted=True, uncertainty_multiple=.5)
e=ResearchEngine(Config(feature_mode=cfg.feature_mode)); jan=e.load('/home/ubuntu/btcusdt_long_sample_normalized.csv'); jul=e.load('/home/ubuntu/btcusdt_july_normalized.csv'); raw=pd.concat([jan,jul]).sort_index(); X=e.features(raw); yg=executable_target(raw,cfg.horizon,cfg.execution_delay); cost=(cfg.fee_bps+cfg.slippage_bps)/10000; yt=(yg-np.sign(yg)*cost).rename('target_train'); aligned=X.join(yt).join(yg).dropna(); X=aligned.drop(columns=['target_train','target_gross']); yt=aligned.target_train; yg=aligned.target_gross; cutoff=pd.Timestamp('2026-07-01',tz='UTC'); train_idx=X.index<cutoff; test_idx=X.index>=cutoff; train_pos=np.where(train_idx)[0]; test_pos=np.where(test_idx)[0]; train_end=train_pos[-1]+1; val_start=train_end-cfg.validation_bars; train_start=max(0,train_end-cfg.validation_bars-cfg.train_bars); test_start=test_pos[0]+cfg.horizon; rows=[]
for kind in ['elastic_net','hist_gradient_boosting']:
    best=None
    for candidate in model_candidates(kind,42):
        candidate.fit(X.iloc[train_start:val_start],yt.iloc[train_start:val_start]); vp=candidate.predict(X.iloc[val_start:train_end]); rs=float(np.std(yt.iloc[val_start:train_end].to_numpy()-vp,ddof=1)); thr=max(cost*cfg.neutral_cost_multiple,cfg.uncertainty_multiple*rs); vs=score_predictions(vp,yg.iloc[val_start:train_end],cfg.horizon,cfg.fee_bps,cfg.slippage_bps,thr); key=vs['relative_sharpe'];
        if best is None or key>best[0]: best=(key,candidate,thr,vs)
    model=best[1]; model.fit(X.iloc[train_start:train_end],yt.iloc[train_start:train_end]); pred=model.predict(X.iloc[test_start:]); ts=score_predictions(pred,yg.iloc[test_start:],cfg.horizon,cfg.fee_bps,cfg.slippage_bps,best[2]); rows.append({'model':kind,'validation_relative_sharpe':best[0],'threshold':best[2],**{f'test_{k}':v for k,v in ts.items()}})
out=pd.DataFrame(rows); pathlib.Path('/home/ubuntu/external_july_results.json').write_text(out.to_json(orient='records',indent=2),encoding='utf-8'); print(out.round(6).to_string(index=False))
