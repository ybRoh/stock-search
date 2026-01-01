#!/usr/bin/env python3
"""
주식 검색기 - FastAPI 웹 서버
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import uvicorn
import io
import csv

from services.stock_data import get_stock_service
from services.news_service import get_news_service
from screener.formula import get_formula_manager
from models.lstm_predictor import get_predictor, StockPredictor


app = FastAPI(title="주식 검색기", version="1.0.0")

# 정적 파일 및 템플릿 설정
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

templates = Jinja2Templates(directory=templates_dir)

# static 폴더가 있을 때만 마운트
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============ API 엔드포인트 ============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search")
async def api_search(keyword: str, market: str = "ALL"):
    """종목 검색 API"""
    service = get_stock_service()
    results = service.search_stock(keyword, market)
    return {"results": results.to_dict("records")}


@app.get("/api/quote/{code}")
async def api_quote(code: str):
    """시세 조회 API"""
    service = get_stock_service()
    info = service.get_stock_info(code)
    quote = service.get_current_price(code)
    return {
        "info": info,
        "quote": quote
    }


@app.get("/api/chart/{code}")
async def api_chart(code: str, period: str = "3m"):
    """차트 데이터 API"""
    service = get_stock_service()
    info = service.get_stock_info(code)
    df = service.get_price_history(code, period, "d")

    if df.empty:
        return {"error": "데이터 없음"}

    data = {
        "name": info.get("name", ""),
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "open": df["시가"].tolist(),
        "high": df["고가"].tolist(),
        "low": df["저가"].tolist(),
        "close": df["종가"].tolist(),
        "volume": df["거래량"].tolist()
    }
    return data


@app.get("/api/finance/{code}")
async def api_finance(code: str):
    """재무정보 API"""
    service = get_stock_service()
    info = service.get_stock_info(code)
    fundamental = service.get_fundamental(code)
    market_cap = service.get_market_cap(code)
    return {
        "info": info,
        "fundamental": fundamental,
        "market_cap": market_cap
    }


@app.get("/api/news/{code}")
async def api_news(code: str, count: int = 10):
    """뉴스 API"""
    service = get_stock_service()
    news_service = get_news_service()

    info = service.get_stock_info(code)
    news = news_service.get_stock_news(code, count)
    return {
        "name": info.get("name", ""),
        "news": news
    }


@app.get("/api/formulas")
async def api_formulas():
    """검색식 목록 API"""
    manager = get_formula_manager()
    formulas = manager.list_formulas()
    return {
        "formulas": [
            {
                "name": f.name,
                "description": f.description,
                "conditions": len(f.conditions),
                "author": f.author
            }
            for f in formulas
        ]
    }


@app.get("/api/screen/multi")
async def api_screen_multi(conditions: str, mode: str = "and"):
    """복수 조건 검색 API (LSTM 포함)"""
    from datetime import datetime, timedelta
    from pykrx import stock as krx

    stock_service = get_stock_service()
    condition_ids = conditions.split(',')

    # LSTM 조건 포함 여부 확인
    use_lstm = 'lstm_bullish' in condition_ids
    other_conditions = [c for c in condition_ids if c != 'lstm_bullish']

    condition_map = {
        'rsi_oversold': {'name': 'RSI 과매도', 'type': 'rsi', 'params': {'threshold': 30}},
        'volume_surge': {'name': '거래량 급증', 'type': 'volume', 'params': {'ratio': 3.0}},
        'small_growth': {'name': '소형 성장주', 'type': 'market_cap', 'params': {'min': 500, 'max': 3000}},
        'macd_buy': {'name': 'MACD 매수', 'type': 'macd', 'params': {}},
        'bollinger_low': {'name': '볼린저 하단', 'type': 'bollinger', 'params': {}},
        'large_cap': {'name': '대형 우량주', 'type': 'market_cap', 'params': {'min': 100000}},
        'high_dividend': {'name': '고배당주', 'type': 'dividend', 'params': {'min': 3.0}},
        'rising_stocks': {'name': '급등주', 'type': 'change_rate', 'params': {'min': 5.0}},
        # 시가총액 조건
        'cap_1000_3000': {'name': '시총 1000~3000억', 'type': 'market_cap', 'params': {'min': 1000, 'max': 3000}},
        'cap_over_3000': {'name': '시총 3000억 이상', 'type': 'market_cap', 'params': {'min': 3000, 'max': float('inf')}}
    }

    try:
        predictor = None
        if use_lstm:
            predictor = get_predictor()

        sample_stocks = stock_service.get_sample_stocks(limit=100)
        results = []

        for _, row in sample_stocks.iterrows():
            code = row['code']
            name = row['name']
            market = row.get('market', 'KRX')

            try:
                quote = stock_service.get_current_price(code)
                price = quote.get('현재가', 0)
                change = quote.get('전일대비', 0)
                change_rate = quote.get('등락률', 0)

                if price <= 0:
                    continue

                condition_results = []

                # LSTM 조건 검사
                lstm_result = None
                if use_lstm:
                    try:
                        if not predictor.has_model(code):
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=365)
                            df = krx.get_market_ohlcv(
                                start_date.strftime("%Y%m%d"),
                                end_date.strftime("%Y%m%d"),
                                code
                            )
                            if len(df) >= 100:
                                predictor.train(df, epochs=20)
                                predictor.save_model(code)
                            else:
                                condition_results.append(False)
                                continue
                        else:
                            predictor.load_model(code)

                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=60)
                        recent_df = krx.get_market_ohlcv(
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d"),
                            code
                        )
                        prediction = predictor.predict(recent_df)

                        if "error" not in prediction:
                            lstm_passed = prediction.get("direction") == "상승" and prediction.get("confidence", 0) >= 55
                            condition_results.append(lstm_passed)
                            if lstm_passed:
                                lstm_result = prediction
                        else:
                            condition_results.append(False)
                    except Exception:
                        condition_results.append(False)

                # 다른 조건들 검사
                for cond_id in other_conditions:
                    if cond_id not in condition_map:
                        continue

                    cond = condition_map[cond_id]
                    passed = False

                    if cond['type'] == 'change_rate':
                        passed = change_rate >= cond['params'].get('min', 0)
                    elif cond['type'] == 'market_cap':
                        cap_info = stock_service.get_market_cap(code)
                        cap = cap_info.get('시가총액_억', 0)
                        min_cap = cond['params'].get('min', 0)
                        max_cap = cond['params'].get('max', float('inf'))
                        passed = min_cap <= cap <= max_cap
                    elif cond['type'] == 'dividend':
                        fund = stock_service.get_fundamental(code)
                        div = fund.get('배당수익률', 0) or 0
                        passed = div >= cond['params'].get('min', 0)
                    elif cond['type'] == 'volume':
                        vol = quote.get('거래량', 0)
                        passed = vol >= 100000
                    else:
                        passed = True

                    condition_results.append(passed)

                # AND/OR 모드에 따라 결과 결정
                if mode == 'and':
                    match = all(condition_results) if condition_results else False
                else:
                    match = any(condition_results) if condition_results else False

                if match:
                    result_item = {
                        'code': code,
                        'name': name,
                        'market': market,
                        'price': price,
                        'change': change,
                        'change_rate': change_rate
                    }
                    # LSTM 결과 포함
                    if lstm_result:
                        result_item['lstm'] = lstm_result

                    results.append(result_item)

                if len(results) >= 20:
                    break

            except Exception:
                continue

        return {"mode": mode, "conditions": condition_ids, "results": results, "has_lstm": use_lstm}

    except Exception as e:
        return {"error": str(e), "results": []}


@app.get("/api/screen/{condition_id}")
async def api_screen(condition_id: str):
    """조건 검색 API"""
    from screener.engine import ScreeningEngine

    stock_service = get_stock_service()
    engine = ScreeningEngine()

    # 조건 매핑
    condition_map = {
        'rsi_oversold': {'name': 'RSI 과매도', 'filters': [('rsi', {'period': 14, 'threshold': 30, 'direction': 'below'})]},
        'volume_surge': {'name': '거래량 급증', 'filters': [('volume', {'ratio': 3.0, 'days': 20})]},
        'small_growth': {'name': '소형 성장주', 'filters': [('market_cap', {'min': 500, 'max': 3000}), ('per', {'min': 5, 'max': 15})]},
        'macd_buy': {'name': 'MACD 매수', 'filters': [('macd', {'signal': 'golden_cross'})]},
        'bollinger_low': {'name': '볼린저 하단', 'filters': [('bollinger', {'position': 'lower', 'period': 20})]},
        'large_cap': {'name': '대형 우량주', 'filters': [('market_cap', {'min': 100000})]},
        'high_dividend': {'name': '고배당주', 'filters': [('dividend', {'min': 3.0})]},
        'rising_stocks': {'name': '급등주', 'filters': [('change_rate', {'min': 5.0})]}
    }

    if condition_id not in condition_map:
        return {"error": "알 수 없는 조건입니다", "results": []}

    condition = condition_map[condition_id]

    try:
        # 샘플 종목으로 스크리닝 (시간 단축을 위해)
        sample_stocks = stock_service.get_sample_stocks(limit=100)
        results = []

        for _, row in sample_stocks.iterrows():
            code = row['code']
            name = row['name']
            market = row.get('market', 'KRX')

            try:
                # 조건 검사
                passed = True
                quote = stock_service.get_current_price(code)
                price = quote.get('현재가', 0)
                change = quote.get('전일대비', 0)
                change_rate = quote.get('등락률', 0)

                for filter_type, params in condition['filters']:
                    if filter_type == 'change_rate':
                        if change_rate < params.get('min', 0):
                            passed = False
                            break
                    elif filter_type == 'market_cap':
                        cap_info = stock_service.get_market_cap(code)
                        cap = cap_info.get('시가총액_억', 0)
                        min_cap = params.get('min', 0)
                        max_cap = params.get('max', float('inf'))
                        if not (min_cap <= cap <= max_cap):
                            passed = False
                            break
                    elif filter_type == 'dividend':
                        fund = stock_service.get_fundamental(code)
                        div = fund.get('배당수익률', 0) or 0
                        if div < params.get('min', 0):
                            passed = False
                            break
                    elif filter_type == 'per':
                        fund = stock_service.get_fundamental(code)
                        per = fund.get('PER', 0)
                        if per is None or per == 0:
                            passed = False
                            break
                        min_per = params.get('min', 0)
                        max_per = params.get('max', float('inf'))
                        if not (min_per <= per <= max_per):
                            passed = False
                            break
                    # 기술적 지표는 더 복잡한 계산 필요
                    elif filter_type in ['rsi', 'macd', 'bollinger', 'volume']:
                        # 간단한 대체 조건 사용
                        if filter_type == 'volume':
                            vol = quote.get('거래량', 0)
                            if vol < 100000:  # 최소 거래량 조건
                                passed = False
                                break

                if passed and price > 0:
                    results.append({
                        'code': code,
                        'name': name,
                        'market': market,
                        'price': price,
                        'change': change,
                        'change_rate': change_rate
                    })

                if len(results) >= 20:  # 최대 20개
                    break

            except Exception as e:
                continue

        return {"condition": condition['name'], "results": results}

    except Exception as e:
        return {"error": str(e), "results": []}


@app.get("/api/info/{code}")
async def api_info(code: str):
    """종합 정보 API"""
    stock_service = get_stock_service()
    news_service = get_news_service()

    info = stock_service.get_stock_info(code)
    quote = stock_service.get_current_price(code)
    fundamental = stock_service.get_fundamental(code)
    market_cap = stock_service.get_market_cap(code)
    news = news_service.get_stock_news(code, 5)

    # 차트 데이터
    df = stock_service.get_price_history(code, "3m", "d")
    chart_data = None
    if not df.empty:
        chart_data = {
            "dates": [d.strftime("%Y-%m-%d") for d in df.index],
            "close": df["종가"].tolist()
        }

    return {
        "info": info,
        "quote": quote,
        "fundamental": fundamental,
        "market_cap": market_cap,
        "news": news,
        "chart": chart_data
    }


@app.get("/api/lstm/analyze/{code}")
async def api_lstm(code: str, train: bool = False):
    """LSTM 예측 분석 API (단일 종목)"""
    from datetime import datetime, timedelta
    from pykrx import stock as krx

    try:
        predictor = get_predictor()
        stock_service = get_stock_service()
        info = stock_service.get_stock_info(code)

        # 모델이 없거나 학습 요청시 학습
        if train or not predictor.has_model(code):
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            df = krx.get_market_ohlcv(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                code
            )

            if len(df) < 100:
                return {"error": "데이터가 부족합니다 (최소 100일 필요)", "code": code}

            # 학습
            history = predictor.train(df, epochs=30)
            predictor.save_model(code)
            trained = True
        else:
            predictor.load_model(code)
            trained = False

        # 예측을 위한 최근 데이터
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        recent_df = krx.get_market_ohlcv(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            code
        )

        prediction = predictor.predict(recent_df)

        if "error" in prediction:
            return {"error": prediction["error"], "code": code}

        return {
            "code": code,
            "name": info.get("name", ""),
            "prediction": prediction,
            "trained": trained
        }

    except Exception as e:
        return {"error": str(e), "code": code}


@app.get("/api/lstm/batch")
async def api_lstm_batch(codes: str, bullish_only: bool = False):
    """여러 종목 LSTM 분석 API"""
    from datetime import datetime, timedelta
    from pykrx import stock as krx

    code_list = codes.split(',')
    results = []

    try:
        predictor = get_predictor()
        stock_service = get_stock_service()
        print(f"[LSTM Batch] 처리 시작: {code_list}")

        for code in code_list[:10]:  # 최대 10개
            try:
                print(f"[LSTM Batch] {code} 처리 중...")
                info = stock_service.get_stock_info(code)

                # 모델 로드 또는 학습
                if not predictor.has_model(code):
                    print(f"[LSTM Batch] {code} 모델 없음, 학습 시작...")
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)
                    df = krx.get_market_ohlcv(
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d"),
                        code
                    )

                    if len(df) < 100:
                        print(f"[LSTM Batch] {code}: 데이터 부족 ({len(df)}일)")
                        continue

                    print(f"[LSTM Batch] {code} 학습 데이터: {len(df)}일")
                    predictor.train(df, epochs=20)
                    predictor.save_model(code)
                    print(f"[LSTM Batch] {code} 학습 완료")
                else:
                    print(f"[LSTM Batch] {code} 기존 모델 로드")
                    if not predictor.load_model(code):
                        print(f"[LSTM Batch] {code} 모델 로드 실패, 재학습...")
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=365)
                        df = krx.get_market_ohlcv(
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d"),
                            code
                        )
                        if len(df) < 100:
                            print(f"[LSTM Batch] {code}: 재학습 데이터 부족")
                            continue
                        predictor.train(df, epochs=20)
                        predictor.save_model(code)

                # 예측
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                recent_df = krx.get_market_ohlcv(
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    code
                )

                prediction = predictor.predict(recent_df)
                print(f"[LSTM Batch] {code} 예측 결과: {prediction}")

                if "error" not in prediction:
                    # 상승 예측만 필터링
                    if bullish_only and prediction.get("direction") != "상승":
                        print(f"[LSTM Batch] {code} 하락 예측, 스킵")
                        continue

                    results.append({
                        "code": code,
                        "name": info.get("name", ""),
                        **prediction
                    })
                    print(f"[LSTM Batch] {code} 결과 추가됨")

            except Exception as e:
                import traceback
                print(f"[LSTM Batch] {code} 오류: {e}")
                traceback.print_exc()
                continue

        # 신뢰도 순 정렬
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        print(f"[LSTM Batch] 완료, 결과 수: {len(results)}")
        return {"results": results}

    except Exception as e:
        import traceback
        print(f"[LSTM Batch] 전체 오류: {e}")
        traceback.print_exc()
        return {"error": str(e), "results": []}


@app.get("/api/lstm/screen")
async def api_lstm_screen(min_confidence: float = 55.0, limit: int = 20):
    """LSTM 상승 예측 종목 스크리닝 API"""
    from datetime import datetime, timedelta
    from pykrx import stock as krx

    predictor = get_predictor()
    stock_service = get_stock_service()
    results = []

    try:
        # 샘플 종목에서 스크리닝
        sample_stocks = stock_service.get_sample_stocks(limit=50)

        for _, row in sample_stocks.iterrows():
            code = row['code']
            name = row['name']

            try:
                # 모델 로드 또는 학습
                if not predictor.has_model(code):
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)
                    df = krx.get_market_ohlcv(
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d"),
                        code
                    )

                    if len(df) < 100:
                        continue

                    predictor.train(df, epochs=20)
                    predictor.save_model(code)
                else:
                    predictor.load_model(code)

                # 예측
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                recent_df = krx.get_market_ohlcv(
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    code
                )

                prediction = predictor.predict(recent_df)

                if "error" not in prediction:
                    if prediction.get("direction") == "상승" and prediction.get("confidence", 0) >= min_confidence:
                        # 현재가 정보 추가
                        quote = stock_service.get_current_price(code)
                        results.append({
                            "code": code,
                            "name": name,
                            "price": quote.get("현재가", 0),
                            "change_rate": quote.get("등락률", 0),
                            **prediction
                        })

                if len(results) >= limit:
                    break

            except Exception:
                continue

        # 신뢰도 순 정렬
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return {"results": results}

    except Exception as e:
        return {"error": str(e), "results": []}


@app.get("/api/export/csv")
async def api_export_csv(data: str):
    """검색 결과 CSV 내보내기"""
    import json
    from datetime import datetime

    try:
        results = json.loads(data)

        output = io.StringIO()
        writer = csv.writer(output)

        # 헤더 작성
        headers = ['종목코드', '종목명', '현재가', '등락률(%)', 'LSTM예측', '신뢰도(%)', '매매신호']
        writer.writerow(headers)

        # 데이터 작성
        for item in results:
            row = [
                item.get('code', ''),
                item.get('name', ''),
                item.get('price', ''),
                item.get('change_rate', ''),
                item.get('direction', item.get('lstm', {}).get('direction', '')),
                item.get('confidence', item.get('lstm', {}).get('confidence', '')),
                item.get('signal', item.get('lstm', {}).get('signal', ''))
            ]
            writer.writerow(row)

        output.seek(0)
        filename = f"stock_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return {"error": str(e)}


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """서버 실행"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="주식 검색기 웹 서버")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 (기본: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="포트 (기본: 8000)")
    args = parser.parse_args()

    print(f"🚀 주식 검색기 웹 서버 시작: http://{args.host}:{args.port}")
    run_server(args.host, args.port)
