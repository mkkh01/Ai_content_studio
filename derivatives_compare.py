import pathlib, shutil, sys
sys.path.insert(0,'/home/ubuntu/Ai_content_studio')
from ml_walk_forward import MLConfig, run
root=pathlib.Path('/home/ubuntu/derivatives_compare_runs'); shutil.rmtree(root,ignore_errors=True); root.mkdir(parents=True)
rows=[]
for mode in ['baseline','derivatives']:
    out=root/mode; _,s=run('/home/ubuntu/btcusdt_with_funding.csv',out,MLConfig(horizon=6,execution_delay=1,windows=8,train_bars=1440,validation_bars=240,test_bars=240,feature_mode=mode)); s=s[s.model=='hist_gradient_boosting'].copy(); s.insert(0,'feature_mode',mode); rows.append(s)
import pandas as pd
summary=pd.concat(rows,ignore_index=True); summary.to_csv('/home/ubuntu/derivatives_compare_summary.csv',index=False); print(summary.round(6).to_string(index=False))
