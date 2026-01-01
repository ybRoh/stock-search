"""
스크리너 엔진
검색 조건을 적용하여 종목을 필터링하는 핵심 로직
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from pykrx import stock as krx
from .filters import FilterCondition, FilterType, TechnicalIndicators, ScreenerFilter
from .formula import SearchFormula, get_formula_manager


class ScreenerEngine:
    """종목 스크리닝 엔진"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.tech_indicators = TechnicalIndicators()

    def screen(
        self,
        conditions: List[FilterCondition],
        market: str = "ALL",
        progress_callback: Optional[callable] = None
    ) -> pd.DataFrame:
        """
        조건에 맞는 종목 스크리닝

        Args:
            conditions: 필터 조건 리스트
            market: "KOSPI", "KOSDAQ", "ALL"
            progress_callback: 진행 상황 콜백 함수

        Returns:
            조건에 맞는 종목 DataFrame
        """
        today = datetime.now().strftime("%Y%m%d")

        # 1. 전체 종목 및 기본 데이터 로드
        if progress_callback:
            progress_callback("종목 데이터 로딩 중...")

        stocks_df = self._load_market_data(market, today)
        if stocks_df.empty:
            return pd.DataFrame()

        # 2. 기본 필터 적용 (시가총액, PER, PBR 등)
        if progress_callback:
            progress_callback("기본 조건 필터링 중...")

        basic_conditions = [c for c in conditions if c.filter_type in [
            FilterType.MARKET_CAP, FilterType.PRICE, FilterType.VOLUME,
            FilterType.CHANGE_RATE, FilterType.PER, FilterType.PBR,
            FilterType.DIVIDEND
        ]]

        for condition in basic_conditions:
            stocks_df = self._apply_basic_filter(stocks_df, condition)

        if stocks_df.empty:
            return pd.DataFrame()

        # 3. 기술적 지표 필터 적용 (개별 종목별 계산 필요)
        tech_conditions = [c for c in conditions if c.filter_type in [
            FilterType.MA_CROSS, FilterType.RSI, FilterType.MACD,
            FilterType.BOLLINGER, FilterType.VOLUME_SURGE
        ]]

        if tech_conditions:
            if progress_callback:
                progress_callback("기술적 지표 분석 중...")

            stocks_df = self._apply_technical_filters(
                stocks_df, tech_conditions, progress_callback
            )

        return stocks_df.reset_index(drop=True)

    def screen_by_formula(
        self,
        formula_name: str,
        market: str = "ALL",
        progress_callback: Optional[callable] = None
    ) -> pd.DataFrame:
        """
        저장된 검색식으로 스크리닝

        Args:
            formula_name: 검색식 이름
            market: 시장
            progress_callback: 진행 콜백

        Returns:
            스크리닝 결과
        """
        manager = get_formula_manager()
        formula = manager.get_formula(formula_name)

        if formula is None:
            return pd.DataFrame()

        # 조건을 FilterCondition으로 변환
        conditions = []
        for c in formula.conditions:
            conditions.append(FilterCondition(
                filter_type=FilterType(c["type"]),
                operator=c["operator"],
                value=c["value"],
                value2=c.get("value2")
            ))

        return self.screen(conditions, market, progress_callback)

    def _load_market_data(self, market: str, date: str) -> pd.DataFrame:
        """시장 데이터 로드"""
        dfs = []

        # 최근 거래일 찾기
        for i in range(10):
            check_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                if market in ["ALL", "KOSPI"]:
                    df_kospi = krx.get_market_ohlcv(check_date, market="KOSPI")
                    if not df_kospi.empty:
                        # 시가총액 데이터 추가
                        cap_kospi = krx.get_market_cap(check_date, market="KOSPI")
                        fund_kospi = krx.get_market_fundamental(check_date, market="KOSPI")
                        df_kospi = df_kospi.join(cap_kospi[['시가총액']])
                        df_kospi = df_kospi.join(fund_kospi[['PER', 'PBR', 'DIV']])
                        df_kospi['market'] = 'KOSPI'
                        dfs.append(df_kospi)

                if market in ["ALL", "KOSDAQ"]:
                    df_kosdaq = krx.get_market_ohlcv(check_date, market="KOSDAQ")
                    if not df_kosdaq.empty:
                        cap_kosdaq = krx.get_market_cap(check_date, market="KOSDAQ")
                        fund_kosdaq = krx.get_market_fundamental(check_date, market="KOSDAQ")
                        df_kosdaq = df_kosdaq.join(cap_kosdaq[['시가총액']])
                        df_kosdaq = df_kosdaq.join(fund_kosdaq[['PER', 'PBR', 'DIV']])
                        df_kosdaq['market'] = 'KOSDAQ'
                        dfs.append(df_kosdaq)

                if dfs:
                    break
            except:
                continue

        if not dfs:
            return pd.DataFrame()

        df = pd.concat(dfs)
        df = df.reset_index()
        df = df.rename(columns={'티커': 'code'})

        # 종목명 추가
        df['name'] = df['code'].apply(lambda x: krx.get_market_ticker_name(x))

        # 등락률 계산
        if '시가' in df.columns and '종가' in df.columns:
            df['등락률'] = ((df['종가'] - df['시가']) / df['시가'] * 100).round(2)

        return df

    def _apply_basic_filter(
        self,
        df: pd.DataFrame,
        condition: FilterCondition
    ) -> pd.DataFrame:
        """기본 필터 적용"""
        col_map = {
            FilterType.MARKET_CAP: '시가총액',
            FilterType.PRICE: '종가',
            FilterType.VOLUME: '거래량',
            FilterType.CHANGE_RATE: '등락률',
            FilterType.PER: 'PER',
            FilterType.PBR: 'PBR',
            FilterType.DIVIDEND: 'DIV',
        }

        col = col_map.get(condition.filter_type)
        if col is None or col not in df.columns:
            return df

        op = condition.operator
        val = condition.value
        val2 = condition.value2

        if op == ">":
            return df[df[col] > val]
        elif op == ">=":
            return df[df[col] >= val]
        elif op == "<":
            return df[df[col] < val]
        elif op == "<=":
            return df[df[col] <= val]
        elif op == "==":
            return df[df[col] == val]
        elif op == "between":
            return df[(df[col] >= val) & (df[col] <= val2)]

        return df

    def _apply_technical_filters(
        self,
        df: pd.DataFrame,
        conditions: List[FilterCondition],
        progress_callback: Optional[callable] = None
    ) -> pd.DataFrame:
        """기술적 지표 필터 적용"""
        codes = df['code'].tolist()
        passed_codes = []
        total = len(codes)

        def check_stock(code: str) -> bool:
            """개별 종목 기술적 지표 확인"""
            try:
                # 60일치 데이터 로드 (지표 계산용)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                hist = krx.get_market_ohlcv(
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    code
                )

                if hist.empty or len(hist) < 20:
                    return False

                for condition in conditions:
                    if not self._check_technical_condition(hist, condition):
                        return False

                return True
            except:
                return False

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(check_stock, code): code for code in codes}
            completed = 0

            for future in as_completed(futures):
                completed += 1
                code = futures[future]

                if progress_callback and completed % 50 == 0:
                    progress_callback(f"분석 중... {completed}/{total}")

                try:
                    if future.result():
                        passed_codes.append(code)
                except:
                    pass

        return df[df['code'].isin(passed_codes)]

    def _check_technical_condition(
        self,
        hist: pd.DataFrame,
        condition: FilterCondition
    ) -> bool:
        """기술적 지표 조건 확인"""
        try:
            if condition.filter_type == FilterType.RSI:
                rsi = TechnicalIndicators.calculate_rsi(hist)
                current_rsi = rsi.iloc[-1]

                if condition.operator == "<=":
                    return current_rsi <= condition.value
                elif condition.operator == ">=":
                    return current_rsi >= condition.value

            elif condition.filter_type == FilterType.MA_CROSS:
                periods = condition.value if isinstance(condition.value, (list, tuple)) else (5, 20)
                short, long = periods

                if condition.operator == "golden":
                    return TechnicalIndicators.check_golden_cross(hist, short, long)
                elif condition.operator == "death":
                    return TechnicalIndicators.check_death_cross(hist, short, long)

            elif condition.filter_type == FilterType.MACD:
                macd_data = TechnicalIndicators.calculate_macd(hist)
                macd = macd_data['macd'].iloc[-1]
                signal = macd_data['signal'].iloc[-1]

                if condition.operator == "bullish":
                    return macd > signal
                elif condition.operator == "bearish":
                    return macd < signal

            elif condition.filter_type == FilterType.BOLLINGER:
                bb = TechnicalIndicators.calculate_bollinger(hist)
                close = hist['종가'].iloc[-1]

                if condition.operator == "lower":
                    return close <= bb['lower'].iloc[-1]
                elif condition.operator == "upper":
                    return close >= bb['upper'].iloc[-1]

            elif condition.filter_type == FilterType.VOLUME_SURGE:
                ratio = TechnicalIndicators.calculate_volume_ratio(hist)
                return ratio >= condition.value

        except:
            return False

        return True


# 싱글톤 인스턴스
_screener_engine: Optional[ScreenerEngine] = None


def get_screener_engine() -> ScreenerEngine:
    """ScreenerEngine 싱글톤 인스턴스 반환"""
    global _screener_engine
    if _screener_engine is None:
        _screener_engine = ScreenerEngine()
    return _screener_engine
