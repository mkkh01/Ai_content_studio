import pathlib, shutil, sys, pandas as pd
sys.path.insert(0,'/home/ubuntu/Ai_content_studio')
from ml_walk_forward import MLConfig, run
root=pathlib.Path('/home/ubuntu/derivatives_cost_runs'); shutil.rmtree(root,ignore_errors=True); root.mkdir(parents=True); rows=[]
for mult in [1,2,3]:
 for mode in ['baseline','derivatives']:
  out=root/f'{mode}_{mult}x'; _,s=run('/home/ubuntu/btcusdt_with_funding.csv',out,MLConfig(horizon=6,execution_delay=1,windows=8,train_bars=1440,validation_bars=240,test_bars=240,fee_bps=6*mult,slippage_bps=4*mult,feature_mode=mode)); z=s[s.model=='hist_gradient_boosting'].copy(); z.insert(0,'cost_multiple',mult); z.insert(1,'feature_mode',mode); rows.append(z)
out=pd.concat(rows,ignore_index=True); out.to_csv('/home/ubuntu/derivatives_cost_summary.csv',index=False); print(out.round(6).to_string(index=False))
