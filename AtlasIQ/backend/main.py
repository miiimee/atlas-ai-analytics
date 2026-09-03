
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import io

app=FastAPI(title="AI Analytics Platform V2")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def load_df(f):
    data=f.file.read()
    name=(f.filename or "").lower()
    if name.endswith(".csv"): return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx",".xls")):
        sheets=pd.read_excel(io.BytesIO(data), sheet_name=None)
        for _,df in sheets.items():
            if not df.empty: return df
    raise ValueError("Upload CSV or Excel with a non-empty sheet.")

def clean(df):
    df=df.copy()
    df.columns=[str(c).strip() for c in df.columns]
    for c in df.columns:
        if df[c].dtype=="object":
            parsed=pd.to_datetime(df[c], errors="coerce")
            if parsed.notna().mean()>.75: df[c]=parsed
    return df

@app.get("/api/health")
def health(): return {"status":"ok"}

@app.post("/api/analyze")
async def analyze(file: UploadFile=File(...)):
    try: df=clean(load_df(file))
    except Exception as e: raise HTTPException(400,str(e))
    numeric=df.select_dtypes(include=np.number).columns.tolist()
    dates=df.select_dtypes(include=["datetime64[ns]"]).columns.tolist()
    cats=[c for c in df.columns if c not in numeric and c not in dates and df[c].nunique(dropna=True)<=30]
    date=dates[0] if dates else None

    def pick(words, fallback=None):
        for c in numeric:
            if any(w in c.lower() for w in words): return c
        return fallback or (numeric[0] if numeric else None)
    sales=pick(["sales","revenue","amount","income"])
    profit=pick(["profit","margin","earnings"])
    qty=pick(["quantity","qty","units"])
    discount=pick(["discount"])

    kpis={
      "rows":len(df),"columns":len(df.columns),
      "sales":float(df[sales].sum()) if sales else None,
      "profit":float(df[profit].sum()) if profit else None,
      "quantity":float(df[qty].sum()) if qty else None,
      "avg_order":float(df[sales].mean()) if sales else None
    }
    charts=[]
    if date and sales:
        tmp=df.dropna(subset=[date]).copy(); tmp["period"]=tmp[date].dt.to_period("M").astype(str)
        g=tmp.groupby("period")[sales].sum().reset_index()
        charts.append({"type":"line","title":"Revenue Trend","x":"period","y":"value","data":[{"label":str(r["period"]),"value":round(float(r[sales]),2)} for _,r in g.iterrows()]})
    for c in cats[:3]:
        if sales:
            g=df.groupby(c,dropna=False)[sales].sum().nlargest(8).reset_index()
            charts.append({"type":"bar","title":f"Sales by {c}","x":c,"y":"value","data":[{"label":str(r[c]),"value":round(float(r[sales]),2)} for _,r in g.iterrows()]})
    insights=[]
    if profit and sales:
        margin=df[profit].sum()/df[sales].sum()*100 if df[sales].sum() else 0
        insights.append(f"Overall profit margin is {margin:.1f}%.")
    if discount and profit:
        high=df[discount].mean()
        insights.append(f"Average discount is {high:.1%}; review heavily discounted low-profit items.")
    miss=df.isna().mean().sort_values(ascending=False)
    for c,v in miss.head(3).items():
        if v>0: insights.append(f"{c} has {v:.1%} missing values.")
    if not insights: insights.append("Dataset loaded successfully. Explore the generated KPIs and charts.")
    metrics=[]
    for c in numeric[:12]:
        metrics.append({"name":c,"sum":round(float(df[c].sum()),2),"avg":round(float(df[c].mean()),2),"min":round(float(df[c].min()),2),"max":round(float(df[c].max()),2)})
    return {"file":file.filename,"kpis":kpis,"fields":{"numeric":numeric,"dates":dates,"categories":cats},"charts":charts,"insights":insights,"metrics":metrics}
