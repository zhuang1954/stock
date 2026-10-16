"""抓取 11 大板塊 ETF 與 SPY 日線，計算報酬與 RRG，輸出 data.js。
用法：
    pip install yfinance pandas numpy
    python fetch_data.py          # 真實資料（Yahoo Finance）
    python fetch_data.py --demo   # 隨機測試資料
"""
import json
import sys
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

BENCH = "SPY"
SECTORS = {
    "XLK": "科技",
    "XLF": "金融",
    "XLV": "醫療保健",
    "XLE": "能源",
    "XLY": "非必需消費",
    "XLP": "必需消費",
    "XLI": "工業",
    "XLB": "原物料",
    "XLU": "公用事業",
    "XLRE": "房地產",
    "XLC": "通訊服務",
}
PERIODS = {"1週": 5, "1月": 21, "3月": 63, "6月": 126, "1年": 252}
RRG_TRAIL_WEEKS = 10
RS_RATIO_WINDOW = 26   # 週
RS_MOM_WINDOW = 12     # 週


def load_prices(demo: bool) -> pd.DataFrame:
    tickers = list(SECTORS) + [BENCH]
    if demo:
        idx = pd.bdate_range(end=dt.date.today(), periods=520)
        rng = np.random.default_rng(1)
        steps = rng.normal(0.0003, 0.012, (len(idx), len(tickers)))
        return pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)), index=idx, columns=tickers)
    import yfinance as yf
    df = yf.download(tickers, period="3y", auto_adjust=True, progress=False)["Close"]
    return df[tickers].dropna(how="any")


def build(px: pd.DataFrame) -> dict:
    def period_returns(col):
        return {p: round(float(px[col].iloc[-1] / px[col].iloc[-n - 1] - 1) * 100, 2)
                for p, n in PERIODS.items()}

    returns = {t: period_returns(t) for t in SECTORS}
    bench = period_returns(BENCH)

    weekly = px.resample("W-FRI").last().dropna()
    rrg = {}
    for t in SECTORS:
        rs = weekly[t] / weekly[BENCH]
        ratio = 100 * rs / rs.rolling(RS_RATIO_WINDOW).mean()
        mom = 100 * ratio / ratio.rolling(RS_MOM_WINDOW).mean()
        pts = pd.concat([ratio, mom], axis=1).dropna().tail(RRG_TRAIL_WEEKS)
        rrg[t] = [[round(float(a), 2), round(float(b), 2)] for a, b in pts.values]

    return {
        "asOf": px.index[-1].strftime("%Y-%m-%d"),
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "bench": BENCH,
        "periods": list(PERIODS),
        "names": SECTORS,
        "returns": returns,
        "benchReturns": bench,
        "rrg": rrg,
    }


if __name__ == "__main__":
    data = build(load_prices("--demo" in sys.argv))
    out = Path(__file__).with_name("data.js")
    out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"已輸出 {out}（資料日期 {data['asOf']}）")
