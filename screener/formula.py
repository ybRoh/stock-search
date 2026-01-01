"""
고수 검색식 모듈
사용자 정의 검색식 저장, 불러오기, 관리 기능
"""
import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SearchFormula:
    """검색식 정의"""
    name: str                           # 검색식 이름
    description: str                    # 설명
    conditions: List[Dict[str, Any]]    # 필터 조건들
    created_at: str                     # 생성일
    updated_at: str                     # 수정일
    author: str = "user"                # 작성자


# 기본 고수 검색식 템플릿
DEFAULT_FORMULAS = [
    SearchFormula(
        name="저PER 가치주",
        description="PER 10 이하, PBR 1 이하의 저평가 종목",
        conditions=[
            {"type": "per", "operator": "<=", "value": 10, "value2": None},
            {"type": "pbr", "operator": "<=", "value": 1, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="배당 우량주",
        description="배당수익률 3% 이상, 시가총액 1조 이상",
        conditions=[
            {"type": "dividend", "operator": ">=", "value": 3, "value2": None},
            {"type": "market_cap", "operator": ">=", "value": 1000000000000, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="골든크로스 발생",
        description="5일선이 20일선을 상향 돌파한 종목",
        conditions=[
            {"type": "ma_cross", "operator": "golden", "value": [5, 20], "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="RSI 과매도 반등",
        description="RSI 30 이하 과매도 구간 진입 종목",
        conditions=[
            {"type": "rsi", "operator": "<=", "value": 30, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="거래량 급증",
        description="거래량이 20일 평균 대비 3배 이상 증가",
        conditions=[
            {"type": "volume_surge", "operator": ">=", "value": 3.0, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="소형 성장주",
        description="시가총액 500억~3000억, PER 5~15 성장 가능성 있는 소형주",
        conditions=[
            {"type": "market_cap", "operator": "between", "value": 50000000000, "value2": 300000000000},
            {"type": "per", "operator": "between", "value": 5, "value2": 15},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="MACD 매수 신호",
        description="MACD가 시그널선 상향 돌파",
        conditions=[
            {"type": "macd", "operator": "bullish", "value": None, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="볼린저밴드 하단 터치",
        description="볼린저밴드 하단에 근접한 종목 (반등 기대)",
        conditions=[
            {"type": "bollinger", "operator": "lower", "value": None, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="대형 우량주",
        description="시가총액 10조 이상 대형주",
        conditions=[
            {"type": "market_cap", "operator": ">=", "value": 10000000000000, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
    SearchFormula(
        name="급등주",
        description="당일 등락률 5% 이상 상승 종목",
        conditions=[
            {"type": "change_rate", "operator": ">=", "value": 5, "value2": None},
        ],
        created_at="2024-01-01",
        updated_at="2024-01-01",
        author="system"
    ),
]


class FormulaManager:
    """검색식 관리자"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Args:
            storage_path: 검색식 저장 경로 (기본: ~/.stock_search/formulas.json)
        """
        if storage_path is None:
            home = os.path.expanduser("~")
            storage_dir = os.path.join(home, ".stock_search")
            os.makedirs(storage_dir, exist_ok=True)
            storage_path = os.path.join(storage_dir, "formulas.json")

        self.storage_path = storage_path
        self.formulas: Dict[str, SearchFormula] = {}
        self._load()

    def _load(self) -> None:
        """저장된 검색식 불러오기"""
        # 기본 검색식 먼저 로드
        for formula in DEFAULT_FORMULAS:
            self.formulas[formula.name] = formula

        # 사용자 정의 검색식 불러오기
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        formula = SearchFormula(**item)
                        self.formulas[formula.name] = formula
            except Exception:
                pass

    def _save(self) -> None:
        """검색식 저장"""
        # 사용자 정의 검색식만 저장
        user_formulas = [
            asdict(f) for f in self.formulas.values()
            if f.author != "system"
        ]

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(user_formulas, f, ensure_ascii=False, indent=2)

    def list_formulas(self) -> List[SearchFormula]:
        """모든 검색식 목록 반환"""
        return list(self.formulas.values())

    def get_formula(self, name: str) -> Optional[SearchFormula]:
        """검색식 조회"""
        return self.formulas.get(name)

    def add_formula(
        self,
        name: str,
        description: str,
        conditions: List[Dict[str, Any]]
    ) -> SearchFormula:
        """새 검색식 추가"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formula = SearchFormula(
            name=name,
            description=description,
            conditions=conditions,
            created_at=now,
            updated_at=now,
            author="user"
        )
        self.formulas[name] = formula
        self._save()
        return formula

    def update_formula(
        self,
        name: str,
        description: Optional[str] = None,
        conditions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[SearchFormula]:
        """검색식 수정"""
        if name not in self.formulas:
            return None

        formula = self.formulas[name]
        if formula.author == "system":
            # 시스템 검색식은 복사하여 사용자 검색식으로 저장
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_formula = SearchFormula(
                name=f"{name} (사용자)",
                description=description or formula.description,
                conditions=conditions or formula.conditions,
                created_at=now,
                updated_at=now,
                author="user"
            )
            self.formulas[new_formula.name] = new_formula
            self._save()
            return new_formula

        # 사용자 검색식 수정
        if description:
            formula.description = description
        if conditions:
            formula.conditions = conditions
        formula.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        return formula

    def delete_formula(self, name: str) -> bool:
        """검색식 삭제 (사용자 정의만 가능)"""
        if name not in self.formulas:
            return False

        if self.formulas[name].author == "system":
            return False

        del self.formulas[name]
        self._save()
        return True

    def export_formula(self, name: str, file_path: str) -> bool:
        """검색식 내보내기"""
        if name not in self.formulas:
            return False

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.formulas[name]), f, ensure_ascii=False, indent=2)
        return True

    def import_formula(self, file_path: str) -> Optional[SearchFormula]:
        """검색식 가져오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                formula = SearchFormula(**data)
                formula.author = "user"  # 가져온 검색식은 사용자 것으로 설정
                formula.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.formulas[formula.name] = formula
                self._save()
                return formula
        except Exception:
            return None


# 싱글톤 인스턴스
_formula_manager: Optional[FormulaManager] = None


def get_formula_manager() -> FormulaManager:
    """FormulaManager 싱글톤 인스턴스 반환"""
    global _formula_manager
    if _formula_manager is None:
        _formula_manager = FormulaManager()
    return _formula_manager
