# -*- coding: utf-8 -*-
import time
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Keep & Grow Screener Backend - S&P 50 Premium")

# 🔒 [CORS 해결 장치] 브라우저 보안 차단을 완벽하게 해제하는 승인 장치
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🇺🇸 S&P 500 지수를 대표하는 글로벌 탑티어 우량 기업 티커 명단 (50개 한정)
SP500_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "LLY", "AVGO", "V",
    "JPM", "UNH", "WMT", "MA", "XOM", "JNJ", "PG", "HD", "ORCL", "COST",
    "ABBV", "MRK", "BAC", "AMD", "CVX", "NFLX", "PEP", "ADBE", "KO", "TMO",
    "WFC", "QCOM", "CSCO", "CRM", "ACN", "GE", "LIN", "NKE", "DHR", "INTC",
    "DIS", "INTU", "TXN", "PM", "COP", "UNP", "AMGN", "VZ", "IBM", "CAT"
]

# S&P 데이터 무결성을 위한 정렬 및 중복 티커 클렌징
SP500_TICKERS = sorted(list(set(SP500_TICKERS)))

@app.get("/")
def read_root():
    return {
        "status": "active",
        "market": "S&P 50 Index (Top 50)",
        "total_supported_stocks": len(SP500_TICKERS),
        "message": "킵앤그로우 S&P 50 프리미엄 리팩토링 백엔드가 안정적으로 구동 중입니다!"
    }


# 📊 [API] S&P 50 종목 역사적 일봉 타임라인 차트 수집용 단일 라우트
@app.get("/api/candle")
def get_stock_candle(
    symbol: str = Query(..., description="조회할 S&P 티커 (예: LLY)"),
    period_months: int = Query(12, description="관찰 개월 수")
):
    symbol = symbol.upper()
    range_str = "1y" if period_months >= 12 else f"{period_months}mo"
    yf_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_str}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        yf_res = requests.get(yf_url, headers=headers, timeout=5)
        if yf_res.status_code != 200:
            raise HTTPException(status_code=yf_res.status_code, detail=f"야후 파이낸스 통신 거부 (티커: {symbol})")
            
        yf_data = yf_res.json()
        chart_result = yf_data.get("chart", {}).get("result")
        if not chart_result:
            raise HTTPException(status_code=404, detail=f"{symbol}에 대한 거래 시세 결과가 존재하지 않습니다.")

        res = chart_result[0]
        timestamps = res.get("timestamp", [])
        indicators = res.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]
        adjclose = indicators.get("adjclose", [{}])[0].get("adjclose", [])
        
        # 수정 종가(adjclose)가 누락되었을 경우 기본 종가(close)로 유연하게 보완
        closes = adjclose if adjclose else quote.get("close", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        opens = quote.get("open", [])
        volumes = quote.get("volume", [])
        
        # 결측치(휴장일 데이터 오차) 자동 정화 처리 루프
        valid_t, valid_c, valid_h, valid_l, valid_o, valid_v = [], [], [], [], [], []
        for idx in range(len(timestamps)):
            if closes[idx] is not None:
                valid_t.append(timestamps[idx])
                valid_c.append(closes[idx])
                valid_h.append(highs[idx] if highs[idx] is not None else closes[idx])
                valid_l.append(lows[idx] if lows[idx] is not None else closes[idx])
                valid_o.append(opens[idx] if opens[idx] is not None else closes[idx])
                valid_v.append(volumes[idx] if volumes[idx] is not None else 0)
                
        if not valid_c:
            raise HTTPException(status_code=404, detail=f"{symbol}의 유효한 영업일 가격 배열이 비어있습니다.")

        return {
            "t": valid_t,
            "c": valid_c,
            "h": valid_h,
            "l": valid_l,
            "o": valid_o,
            "v": valid_v,
            "s": "ok"
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as yf_err:
        raise HTTPException(status_code=500, detail=f"야후 파이낸스 역사 시세 연동 치명적 오류: {str(yf_err)}")


# 🚀 Uvicorn 프로세스 강제 고정 기동
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)