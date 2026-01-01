"""
검색 조건 필터 모듈
시가총액, 기술적 지표, 재무 지표 등 다양한 필터 제공
"""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import ta


class FilterType(Enum):
    """필터 유형"""
    MARKET_CAP = "market_cap"          # 시가총액
    PRICE = "price"                     # 가격
    VOLUME = "volume"                   # 거래량
    CHANGE_RATE = "change_rate"         # 등락률
    PER = "per"                         # PER
    PBR = "pbr"                         # PBR
    ROE = "roe"                         # ROE
    DIVIDEND = "dividend"               # 배당수익률
    MA_CROSS = "ma_cross"               # 이동평균 교차
    RSI = "rsi"                         # RSI
    MACD = "macd"                       # MACD
    BOLLINGER = "bollinger"             # 볼린저밴드
    VOLUME_SURGE = "volume_surge"       # 거래량 급증


@dataclass
class FilterCondition:
    """필터 조건"""
    filter_type: FilterType
    operator: str  # >, <, >=, <=, ==, between
    value: Any
    value2: Any = None  # between 연산자용


class ScreenerFilter:
    """종목 스크리너 필터"""

    def __init__(self):
        self.conditions: List[FilterCondition] = []

    def add_condition(self, condition: FilterCondition) -> 'ScreenerFilter':
        """필터 조건 추가"""
        self.conditions.append(condition)
        return self

    def clear(self) -> 'ScreenerFilter':
        """모든 조건 초기화"""
        self.conditions.clear()
        return self

    # ===== 시가총액 필터 =====
    def market_cap_min(self, value: float) -> 'ScreenerFilter':
        """시가총액 최소값 (억원)"""
        self.conditions.append(FilterCondition(
            FilterType.MARKET_CAP, ">=", value * 100000000
        ))
        return self

    def market_cap_max(self, value: float) -> 'ScreenerFilter':
        """시가총액 최대값 (억원)"""
        self.conditions.append(FilterCondition(
            FilterType.MARKET_CAP, "<=", value * 100000000
        ))
        return self

    def market_cap_between(self, min_val: float, max_val: float) -> 'ScreenerFilter':
        """시가총액 범위 (억원)"""
        self.conditions.append(FilterCondition(
            FilterType.MARKET_CAP, "between",
            min_val * 100000000, max_val * 100000000
        ))
        return self

    # ===== 가격 필터 =====
    def price_min(self, value: int) -> 'ScreenerFilter':
        """가격 최소값"""
        self.conditions.append(FilterCondition(FilterType.PRICE, ">=", value))
        return self

    def price_max(self, value: int) -> 'ScreenerFilter':
        """가격 최대값"""
        self.conditions.append(FilterCondition(FilterType.PRICE, "<=", value))
        return self

    # ===== 등락률 필터 =====
    def change_rate_min(self, value: float) -> 'ScreenerFilter':
        """등락률 최소값 (%)"""
        self.conditions.append(FilterCondition(FilterType.CHANGE_RATE, ">=", value))
        return self

    def change_rate_max(self, value: float) -> 'ScreenerFilter':
        """등락률 최대값 (%)"""
        self.conditions.append(FilterCondition(FilterType.CHANGE_RATE, "<=", value))
        return self

    # ===== 거래량 필터 =====
    def volume_min(self, value: int) -> 'ScreenerFilter':
        """거래량 최소값"""
        self.conditions.append(FilterCondition(FilterType.VOLUME, ">=", value))
        return self

    def volume_surge(self, ratio: float = 2.0) -> 'ScreenerFilter':
        """거래량 급증 (평균 대비 배율)"""
        self.conditions.append(FilterCondition(FilterType.VOLUME_SURGE, ">=", ratio))
        return self

    # ===== 재무 지표 필터 =====
    def per_between(self, min_val: float, max_val: float) -> 'ScreenerFilter':
        """PER 범위"""
        self.conditions.append(FilterCondition(
            FilterType.PER, "between", min_val, max_val
        ))
        return self

    def pbr_max(self, value: float) -> 'ScreenerFilter':
        """PBR 최대값"""
        self.conditions.append(FilterCondition(FilterType.PBR, "<=", value))
        return self

    def dividend_min(self, value: float) -> 'ScreenerFilter':
        """배당수익률 최소값 (%)"""
        self.conditions.append(FilterCondition(FilterType.DIVIDEND, ">=", value))
        return self

    # ===== 기술적 지표 필터 =====
    def golden_cross(self, short_period: int = 5, long_period: int = 20) -> 'ScreenerFilter':
        """골든크로스 (단기 이평선이 장기 이평선 상향 돌파)"""
        self.conditions.append(FilterCondition(
            FilterType.MA_CROSS, "golden", (short_period, long_period)
        ))
        return self

    def death_cross(self, short_period: int = 5, long_period: int = 20) -> 'ScreenerFilter':
        """데드크로스 (단기 이평선이 장기 이평선 하향 돌파)"""
        self.conditions.append(FilterCondition(
            FilterType.MA_CROSS, "death", (short_period, long_period)
        ))
        return self

    def rsi_oversold(self, threshold: float = 30) -> 'ScreenerFilter':
        """RSI 과매도 구간"""
        self.conditions.append(FilterCondition(FilterType.RSI, "<=", threshold))
        return self

    def rsi_overbought(self, threshold: float = 70) -> 'ScreenerFilter':
        """RSI 과매수 구간"""
        self.conditions.append(FilterCondition(FilterType.RSI, ">=", threshold))
        return self

    def macd_bullish(self) -> 'ScreenerFilter':
        """MACD 상승 신호 (MACD > Signal)"""
        self.conditions.append(FilterCondition(FilterType.MACD, "bullish", None))
        return self

    def macd_bearish(self) -> 'ScreenerFilter':
        """MACD 하락 신호 (MACD < Signal)"""
        self.conditions.append(FilterCondition(FilterType.MACD, "bearish", None))
        return self

    def bollinger_lower(self) -> 'ScreenerFilter':
        """볼린저밴드 하단 터치"""
        self.conditions.append(FilterCondition(FilterType.BOLLINGER, "lower", None))
        return self

    def bollinger_upper(self) -> 'ScreenerFilter':
        """볼린저밴드 상단 터치"""
        self.conditions.append(FilterCondition(FilterType.BOLLINGER, "upper", None))
        return self

    def to_dict(self) -> List[Dict[str, Any]]:
        """필터 조건을 딕셔너리로 변환"""
        return [
            {
                "type": c.filter_type.value,
                "operator": c.operator,
                "value": c.value,
                "value2": c.value2
            }
            for c in self.conditions
        ]

    @classmethod
    def from_dict(cls, conditions: List[Dict[str, Any]]) -> 'ScreenerFilter':
        """딕셔너리에서 필터 생성"""
        screener = cls()
        for c in conditions:
            screener.conditions.append(FilterCondition(
                filter_type=FilterType(c["type"]),
                operator=c["operator"],
                value=c["value"],
                value2=c.get("value2")
            ))
        return screener


class TechnicalIndicators:
    """기술적 지표 계산"""

    @staticmethod
    def calculate_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """이동평균"""
        return df['종가'].rolling(window=period).mean()

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index)"""
        return ta.momentum.RSIIndicator(df['종가'], window=period).rsi()

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """MACD"""
        macd_indicator = ta.trend.MACD(df['종가'])
        return {
            'macd': macd_indicator.macd(),
            'signal': macd_indicator.macd_signal(),
            'histogram': macd_indicator.macd_diff()
        }

    @staticmethod
    def calculate_bollinger(df: pd.DataFrame, period: int = 20) -> Dict[str, pd.Series]:
        """볼린저 밴드"""
        bb = ta.volatility.BollingerBands(df['종가'], window=period)
        return {
            'upper': bb.bollinger_hband(),
            'middle': bb.bollinger_mavg(),
            'lower': bb.bollinger_lband()
        }

    @staticmethod
    def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
        """거래량 비율 (현재 거래량 / 평균 거래량)"""
        avg_volume = df['거래량'].rolling(window=period).mean().iloc[-1]
        current_volume = df['거래량'].iloc[-1]
        return current_volume / avg_volume if avg_volume > 0 else 0

    @staticmethod
    def check_golden_cross(df: pd.DataFrame, short: int = 5, long: int = 20) -> bool:
        """골든크로스 확인"""
        if len(df) < long + 1:
            return False

        ma_short = df['종가'].rolling(window=short).mean()
        ma_long = df['종가'].rolling(window=long).mean()

        # 현재: 단기 > 장기, 이전: 단기 <= 장기
        current = ma_short.iloc[-1] > ma_long.iloc[-1]
        previous = ma_short.iloc[-2] <= ma_long.iloc[-2]

        return current and previous

    @staticmethod
    def check_death_cross(df: pd.DataFrame, short: int = 5, long: int = 20) -> bool:
        """데드크로스 확인"""
        if len(df) < long + 1:
            return False

        ma_short = df['종가'].rolling(window=short).mean()
        ma_long = df['종가'].rolling(window=long).mean()

        # 현재: 단기 < 장기, 이전: 단기 >= 장기
        current = ma_short.iloc[-1] < ma_long.iloc[-1]
        previous = ma_short.iloc[-2] >= ma_long.iloc[-2]

        return current and previous
