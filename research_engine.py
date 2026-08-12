"""Reproducible crypto forecasting research loop.

This module intentionally favors transparent baselines and strict temporal splits over
unverifiable claims. It can run with only pandas/numpy installed.
"""
from __future__ import annotations
import argparse, json, math, hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd

@dataclass
class Config:
    iterations: int = 20
    train_ratio: float = .60
    validation_ratio: float = .20
    fee_bps: float = 6.0
    slippage_bps: float = 4.0
    seed: int = 42

class ResearchEngine:
    def __init__(self, config: Config):
        self.cfg=config; self.rng=np.random.default_rng(config.seed)

    def load(self, path: str) -> pd.DataFrame:
        df=pd.read_csv(path)
        required={'timestamp','open','high','low','close','volume'}
        missing=required-set(df.columns)
        if missing: raise ValueError(f'Missing columns: {sorted(missing)}')
        df=df.copy(); df['timestamp']=pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        for c in ['open','high','low','close','volume']:
            df[c]=pd.to_numeric(df[c], errors='coerce')
        df=df.dropna(subset=['timestamp','open','high','low','close','volume']).sort_values('timestamp')
        df=df.drop_duplicates('timestamp').set_index('timestamp')
        df=df[(df[['open','high','low','close','volume']]>0).all(axis=1)]
        return df

    def features(self, df: pd.DataFrame) -> pd.DataFrame:
        x=pd.DataFrame(index=df.index)
        close=df['close']; ret=close.pct_change()
        for n in [1,3,6,12,24,48,96]: x[f'ret_{n}']=close.pct_change(n)
        for n in [6,12,24,48,96]:
            x[f'vol_{n}']=ret.rolling(n).std()
            x[f'z_{n}']=(close-close.rolling(n).mean())/(close.rolling(n).std()+1e-12)
            x[f'volume_z_{n}']=(df['volume']-df['volume'].rolling(n).mean())/(df['volume'].rolling(n).std()+1e-12)
        x['range']=((df['high']-df['low'])/close).clip(-1,1)
        x['close_location']=(close-df['low'])/(df['high']-df['low']+1e-12)
        if 'funding_rate' in df: x['funding_rate']=pd.to_numeric(df['funding_rate'],errors='coerce')
        if 'open_interest' in df: x['oi_change']=pd.to_numeric(df['open_interest'],errors='coerce').pct_change()
        return x.replace([np.inf,-np.inf],np.nan).dropna()

    def target(self, df: pd.DataFrame, horizon: int) -> pd.Series:
        return df['close'].shift(-horizon)/df['close']-1

    def score(self, pred: pd.Series, actual: pd.Series, prices: pd.Series) -> dict:
        z=pd.concat([pred.rename('pred'),actual.rename('actual'),prices.rename('price')],axis=1).dropna()
        signal=np.where(z.pred>0,1,np.where(z.pred<0,-1,0)); future=z.actual.to_numpy()
        turnover=np.abs(np.diff(np.r_[0,signal])); costs=turnover*(self.cfg.fee_bps+self.cfg.slippage_bps)/10000
        strat=signal*future-costs; equity=np.cumprod(1+strat)
        if len(strat)<2: return {'sharpe':-99,'net_return':-100,'max_drawdown':-100,'trades':0}
        sharpe=float(np.sqrt(365)*np.mean(strat)/(np.std(strat)+1e-12)); peak=np.maximum.accumulate(equity); dd=(equity/peak-1)*100
        return {'sharpe':round(sharpe,4),'net_return':round((equity[-1]-1)*100,4),'max_drawdown':round(float(dd.min()),4),'trades':int(turnover.sum())}

    def candidate(self, X: pd.DataFrame, y: pd.Series, price: pd.Series, horizon: int, i: int) -> dict:
        # Transparent ridge-like linear baseline with random feature subset. The search
        # space is deliberately explicit and reproducible; replace with torch models as needed.
        n=len(X); train_end=int(n*self.cfg.train_ratio); val_end=int(n*(self.cfg.train_ratio+self.cfg.validation_ratio))
        if n < 20 or train_end < 5 or val_end >= n:
            return {'name':f'RidgeSearch-{i:03d}','features':0,'horizon':horizon,'window':0,'feature_names':[], 'metrics':{'sharpe':-99,'net_return':-100,'max_drawdown':-100,'trades':0},'accepted':False,'failure':'insufficient rows after feature and temporal filtering'}
        cols=list(X.columns); k=min(len(cols), int(self.rng.integers(5, max(6,min(30,len(cols)+1)))))
        chosen=list(self.rng.choice(cols,size=k,replace=False)); a=X[chosen].to_numpy(); yy=y.reindex(X.index).to_numpy()
        mu=np.nanmean(a[:train_end],axis=0); sd=np.nanstd(a[:train_end],axis=0)+1e-8; a=(a-mu)/sd
        lam=float(10**self.rng.uniform(-3,1)); w=np.linalg.solve(a[:train_end].T@a[:train_end]+lam*np.eye(k),a[:train_end].T@np.nan_to_num(yy[:train_end]))
        pred=pd.Series(a@w,index=X.index)
        test_pred=pred.iloc[val_end:]; test_y=y.reindex(X.index).iloc[val_end:]; test_p=price.reindex(X.index).iloc[val_end:]
        metrics=self.score(test_pred,test_y,test_p)
        return {'name':f'RidgeSearch-{i:03d}','features':k,'horizon':horizon,'window':int(self.rng.choice([24,48,96,168,240])),'feature_names':chosen,'metrics':metrics,'accepted':metrics['sharpe']>0.5 and metrics['max_drawdown']>-35}

    def run(self, df: pd.DataFrame, out: str) -> list[dict]:
        outp=Path(out); outp.mkdir(parents=True,exist_ok=True); X=self.features(df); results=[]
        for i in range(self.cfg.iterations):
            h=int(self.rng.choice([1,3,6,12,24])); y=self.target(df,h).reindex(X.index)
            r=self.candidate(X,y,df['close'],h,i); r['config']=asdict(self.cfg); r['data_hash']=hashlib.sha256(pd.util.hash_pandas_object(df,index=True).values.tobytes()).hexdigest()[:16]; results.append(r)
            (outp/'experiment_log.jsonl').open('a',encoding='utf8').write(json.dumps(r,ensure_ascii=False)+'\n')
        results.sort(key=lambda r:r['metrics']['sharpe'],reverse=True); (outp/'model_registry.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
        summary={'best':results[0] if results else None,'experiments':len(results),'data_rows':len(df),'feature_count':X.shape[1],'failure_count':sum(not r['accepted'] for r in results)}
        (outp/'decision_history.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8'); return results

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--iterations',type=int,default=20); ap.add_argument('--output',default='runs'); args=ap.parse_args()
    e=ResearchEngine(Config(iterations=args.iterations)); df=e.load(args.csv); results=e.run(df,args.output); print(json.dumps({'experiments':len(results),'best':results[0] if results else None},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
