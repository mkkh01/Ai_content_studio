import pathlib, sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/ubuntu/Ai_content_studio')
from research_engine import Config, ResearchEngine
from ml_walk_forward import MLConfig, model_candidates, executable_target, score_predictions

def evaluate(mode):
 cfg=MLConfig(horizon=6,execution_delay=1,train_bars=1440,validation_bars=240,fee_bps=6,slippage_bps=4,feature_mode=mode,target_cost_adjusted=True,uncertainty_multiple=.5)
 e=ResearchEngine(Config(feature_mode=mode)); raw=e.load('/home/ubuntu/btcusdt_with_funding.csv'); X=e.features(raw); yg=executable_target(raw,cfg.horizon,cfg.execution_delay); cost=.001; yt=(yg-np.sign(yg)*cost).rename('target_train'); aligned=X.join(yt).join(yg).dropna(); X=aligned.drop(columns=['target_train','target_gross']); yt=aligned.target_train; yg=aligned.target_gross; cutoff=pd.Timestamp('2026-07-01',tz='UTC'); tr=np.where(X.index<cutoff)[0]; te=np.where(X.index>=cutoff)[0]; train_end=tr[-1]+1; val_start=train_end-cfg.validation_bars; train_start=train_end-cfg.validation_bars-cfg.train_bars; test_start=te[0]+cfg.horizon; best=None
 for cand in model_candidates('hist_gradient_boosting',42):
  cand.fit(X.iloc[train_start:val_start],yt.iloc[train_start:val_start]); vp=cand.predict(X.iloc[val_start:train_end]); rs=float(np.std(yt.iloc[val_start:train_end].to_numpy()-vp,ddof=1)); thr=max(cost*cfg.neutral_cost_multiple,cfg.uncertainty_multiple*rs); vs=score_predictions(vp,yg.iloc[val_start:train_end],cfg.horizon,cfg.fee_bps,cfg.slippage_bps,thr)
  if best is None or vs['relative_sharpe']>best[0]: best=(vs['relative_sharpe'],cand,thr)
 model=best[1]; model.fit(X.iloc[train_start:train_end],yt.iloc[train_start:train_end]); pred=model.predict(X.iloc[test_start:]); ts=score_predictions(pred,yg.iloc[test_start:],cfg.horizon,cfg.fee_bps,cfg.slippage_bps,best[2]); return {'feature_mode':mode,'validation_relative_sharpe':best[0],'threshold':best[2],**{f'test_{k}':v for k,v in ts.items()}}
res=pd.DataFrame([evaluate('baseline'),evaluate('derivatives')]); res.to_csv('/home/ubuntu/external_derivatives_summary.csv',index=False); print(res.round(6).to_string(index=False))
