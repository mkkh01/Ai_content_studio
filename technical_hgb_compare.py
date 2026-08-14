import json, pathlib, shutil, sys
import pandas as pd
sys.path.insert(0, '/home/ubuntu/Ai_content_studio')
from ml_walk_forward import MLConfig, run

root=pathlib.Path('/home/ubuntu/technical_hgb_runs'); shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
rows=[]
for mode in ['baseline','minimal_technical','technical']:
    out=root/mode
    _, summary = run('/home/ubuntu/btcusdt_long_sample.csv', out, MLConfig(horizon=6, windows=4, feature_mode=mode))
    s=summary[summary['model']=='hist_gradient_boosting'].copy()
    s.insert(0,'feature_mode',mode); rows.append(s)
result=pd.concat(rows, ignore_index=True); result.to_csv('/home/ubuntu/technical_hgb_summary.csv',index=False)
print(result.round(6).to_string(index=False))
