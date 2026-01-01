"""
주식 데이터 서비스 - pykrx를 이용한 한국 주식 데이터 조회
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pykrx import stock as krx


class StockDataService:
    """한국 주식 데이터 조회 서비스"""

    def __init__(self):
        self._stock_list_cache: Optional[pd.DataFrame] = None
        self._cache_date: Optional[str] = None

    def get_stock_list(self, market: str = "ALL") -> pd.DataFrame:
        """
        종목 리스트 조회

        Args:
            market: "KOSPI", "KOSDAQ", "ALL"

        Returns:
            종목코드, 종목명이 포함된 DataFrame
        """
        today = datetime.now().strftime("%Y%m%d")

        # 캐시 확인
        if self._stock_list_cache is not None and self._cache_date == today:
            df = self._stock_list_cache
        else:
            # 코스피, 코스닥 종목 조회
            kospi_tickers = krx.get_market_ticker_list(today, market="KOSPI")
            kosdaq_tickers = krx.get_market_ticker_list(today, market="KOSDAQ")

            stocks = []
            for ticker in kospi_tickers:
                name = krx.get_market_ticker_name(ticker)
                stocks.append({"code": ticker, "name": name, "market": "KOSPI"})

            for ticker in kosdaq_tickers:
                name = krx.get_market_ticker_name(ticker)
                stocks.append({"code": ticker, "name": name, "market": "KOSDAQ"})

            df = pd.DataFrame(stocks)
            self._stock_list_cache = df
            self._cache_date = today

        if market == "ALL":
            return df
        return df[df["market"] == market]

    def search_stock(self, keyword: str, market: str = "ALL") -> pd.DataFrame:
        """
        종목 검색 (종목명 또는 종목코드로 검색)

        Args:
            keyword: 검색어 (종목명 또는 코드)
            market: "KOSPI", "KOSDAQ", "ALL"

        Returns:
            매칭된 종목 DataFrame
        """
        stocks = self.get_stock_list(market)

        # 코드 또는 이름으로 검색
        mask = (
            stocks["code"].str.contains(keyword, case=False, na=False) |
            stocks["name"].str.contains(keyword, case=False, na=False)
        )
        return stocks[mask]

    def get_stock_info(self, code: str) -> Dict[str, Any]:
        """
        종목 기본 정보 조회

        Args:
            code: 종목코드 (6자리)

        Returns:
            종목 정보 딕셔너리
        """
        name = krx.get_market_ticker_name(code)
        stocks = self.get_stock_list()
        market_info = stocks[stocks["code"] == code]
        market = market_info["market"].values[0] if len(market_info) > 0 else "UNKNOWN"

        return {
            "code": code,
            "name": name,
            "market": market
        }

    def get_current_price(self, code: str) -> Dict[str, Any]:
        """
        현재가 및 시세 정보 조회

        Args:
            code: 종목코드 (6자리)

        Returns:
            시세 정보 딕셔너리
        """
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        try:
            # 최근 거래일 데이터 조회
            df = krx.get_market_ohlcv(yesterday, today, code)
            if df.empty:
                return {"error": "데이터를 가져올 수 없습니다"}

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            close = int(latest["종가"])
            prev_close = int(prev["종가"])
            change = close - prev_close
            change_rate = (change / prev_close * 100) if prev_close > 0 else 0

            return {
                "현재가": close,
                "전일대비": change,
                "등락률": round(change_rate, 2),
                "시가": int(latest["시가"]),
                "고가": int(latest["고가"]),
                "저가": int(latest["저가"]),
                "거래량": int(latest["거래량"]),
                "거래대금": int(latest.get("거래대금", 0)),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_price_history(
        self,
        code: str,
        period: str = "3m",
        interval: str = "d"
    ) -> pd.DataFrame:
        """
        가격 히스토리 조회

        Args:
            code: 종목코드
            period: 기간 (1m, 3m, 6m, 1y, 3y)
            interval: 간격 (d: 일봉, w: 주봉, m: 월봉)

        Returns:
            OHLCV DataFrame
        """
        period_map = {
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "3y": 365 * 3
        }
        days = period_map.get(period, 90)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        if interval == "d":
            df = krx.get_market_ohlcv(start_str, end_str, code)
        elif interval == "w":
            df = krx.get_market_ohlcv(start_str, end_str, code, freq="w")
        elif interval == "m":
            df = krx.get_market_ohlcv(start_str, end_str, code, freq="m")
        else:
            df = krx.get_market_ohlcv(start_str, end_str, code)

        return df

    def get_fundamental(self, code: str) -> Dict[str, Any]:
        """
        재무 지표 조회 (PER, PBR, 배당수익률 등)

        Args:
            code: 종목코드

        Returns:
            재무 지표 딕셔너리
        """
        today = datetime.now().strftime("%Y%m%d")

        try:
            df = krx.get_market_fundamental(today, today, code)
            if df.empty:
                # 최근 거래일 찾기
                for i in range(1, 10):
                    check_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                    df = krx.get_market_fundamental(check_date, check_date, code)
                    if not df.empty:
                        break

            if df.empty:
                return {"error": "재무 데이터를 가져올 수 없습니다"}

            latest = df.iloc[-1]

            return {
                "PER": round(latest.get("PER", 0), 2),
                "PBR": round(latest.get("PBR", 0), 2),
                "배당수익률": round(latest.get("DIV", 0), 2),
                "EPS": int(latest.get("EPS", 0)),
                "BPS": int(latest.get("BPS", 0)),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_market_cap(self, code: str) -> Dict[str, Any]:
        """
        시가총액 정보 조회

        Args:
            code: 종목코드

        Returns:
            시가총액 정보 딕셔너리
        """
        today = datetime.now().strftime("%Y%m%d")

        try:
            df = krx.get_market_cap(today, today, code)
            if df.empty:
                for i in range(1, 10):
                    check_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                    df = krx.get_market_cap(check_date, check_date, code)
                    if not df.empty:
                        break

            if df.empty:
                return {"error": "시가총액 데이터를 가져올 수 없습니다"}

            latest = df.iloc[-1]

            market_cap = int(latest.get("시가총액", 0))
            shares = int(latest.get("상장주식수", 0))

            return {
                "시가총액": market_cap,
                "시가총액_억": round(market_cap / 100000000, 0),
                "상장주식수": shares,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_all_market_cap(self, market: str = "ALL") -> pd.DataFrame:
        """
        전체 종목 시가총액 조회

        Args:
            market: "KOSPI", "KOSDAQ", "ALL"

        Returns:
            시가총액 정보 DataFrame
        """
        today = datetime.now().strftime("%Y%m%d")

        dfs = []
        if market in ["ALL", "KOSPI"]:
            try:
                df_kospi = krx.get_market_cap(today, market="KOSPI")
                df_kospi["market"] = "KOSPI"
                dfs.append(df_kospi)
            except:
                pass

        if market in ["ALL", "KOSDAQ"]:
            try:
                df_kosdaq = krx.get_market_cap(today, market="KOSDAQ")
                df_kosdaq["market"] = "KOSDAQ"
                dfs.append(df_kosdaq)
            except:
                pass

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs)

    def get_all_fundamental(self, market: str = "ALL") -> pd.DataFrame:
        """
        전체 종목 재무지표 조회

        Args:
            market: "KOSPI", "KOSDAQ", "ALL"

        Returns:
            재무지표 DataFrame
        """
        today = datetime.now().strftime("%Y%m%d")

        dfs = []
        if market in ["ALL", "KOSPI"]:
            try:
                df_kospi = krx.get_market_fundamental(today, market="KOSPI")
                df_kospi["market"] = "KOSPI"
                dfs.append(df_kospi)
            except:
                pass

        if market in ["ALL", "KOSDAQ"]:
            try:
                df_kosdaq = krx.get_market_fundamental(today, market="KOSDAQ")
                df_kosdaq["market"] = "KOSDAQ"
                dfs.append(df_kosdaq)
            except:
                pass

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs)

    def get_sample_stocks(self, limit: int = 100) -> pd.DataFrame:
        """
        샘플 종목 조회 (시가총액 상위 종목)

        Args:
            limit: 반환할 종목 수

        Returns:
            샘플 종목 DataFrame
        """
        stocks = self.get_stock_list()
        # 대표 종목들 반환 (알파벳순으로 정렬하여 다양한 종목 포함)
        return stocks.head(limit)


# 싱글톤 인스턴스
_stock_service: Optional[StockDataService] = None


def get_stock_service() -> StockDataService:
    """StockDataService 싱글톤 인스턴스 반환"""
    global _stock_service
    if _stock_service is None:
        _stock_service = StockDataService()
    return _stock_service
