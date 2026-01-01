"""
스크리닝 명령 - 조건 검색 기능
"""
import click
from rich.console import Console

from screener.engine import get_screener_engine
from screener.formula import get_formula_manager
from screener.filters import ScreenerFilter
from services.file_loader import get_file_loader
from services.stock_data import get_stock_service
from utils.display import (
    print_screener_result, print_formulas, print_header,
    print_error, print_success, print_progress, print_info
)

console = Console()


@click.group("screen")
def screen_group():
    """조건 검색 명령 그룹"""
    pass


@screen_group.command("run")
@click.option("--formula", "-f", help="사용할 검색식 이름")
@click.option(
    "--market", "-m",
    type=click.Choice(["ALL", "KOSPI", "KOSDAQ"]),
    default="ALL",
    help="시장 선택"
)
@click.option("--cap-min", type=float, help="시가총액 최소 (억원)")
@click.option("--cap-max", type=float, help="시가총액 최대 (억원)")
@click.option("--per-min", type=float, help="PER 최소")
@click.option("--per-max", type=float, help="PER 최대")
@click.option("--pbr-max", type=float, help="PBR 최대")
@click.option("--div-min", type=float, help="배당수익률 최소 (%)")
@click.option("--rsi-max", type=float, help="RSI 과매도 기준")
@click.option("--golden-cross", is_flag=True, help="골든크로스 발생 종목")
@click.option("--volume-surge", type=float, help="거래량 급증 배율")
def run_screen(
    formula, market, cap_min, cap_max, per_min, per_max,
    pbr_max, div_min, rsi_max, golden_cross, volume_surge
):
    """조건 검색 실행

    예시:
        # 저장된 검색식 사용
        python main.py screen run -f "저PER 가치주"

        # 직접 조건 지정
        python main.py screen run --cap-min 1000 --per-max 10 --pbr-max 1

        # 골든크로스 + 거래량 급증
        python main.py screen run --golden-cross --volume-surge 2
    """
    print_header("주식 검색기 - 조건 검색")

    engine = get_screener_engine()

    # 저장된 검색식 사용
    if formula:
        print_info(f"검색식 '{formula}' 실행 중...")
        results = engine.screen_by_formula(
            formula, market,
            progress_callback=print_progress
        )
        results_list = results.to_dict("records") if not results.empty else []
        print_screener_result(results_list, f"'{formula}' 검색 결과")
        return

    # 직접 조건 지정
    screener = ScreenerFilter()

    if cap_min:
        screener.market_cap_min(cap_min)
    if cap_max:
        screener.market_cap_max(cap_max)
    if per_min and per_max:
        screener.per_between(per_min, per_max)
    elif per_max:
        screener.conditions.append(
            screener.conditions.__class__(
                screener.conditions[0].filter_type if screener.conditions else None,
                "<=", per_max
            ) if screener.conditions else None
        )
    if pbr_max:
        screener.pbr_max(pbr_max)
    if div_min:
        screener.dividend_min(div_min)
    if rsi_max:
        screener.rsi_oversold(rsi_max)
    if golden_cross:
        screener.golden_cross()
    if volume_surge:
        screener.volume_surge(volume_surge)

    if not screener.conditions:
        print_error("검색 조건을 지정해주세요. --help로 옵션을 확인하세요.")
        return

    print_info("조건 검색 실행 중...")
    results = engine.screen(
        screener.conditions, market,
        progress_callback=print_progress
    )
    results_list = results.to_dict("records") if not results.empty else []
    print_screener_result(results_list)


@screen_group.command("list")
def list_formulas():
    """저장된 검색식 목록 보기

    예시:
        python main.py screen list
    """
    print_header("주식 검색기 - 검색식 목록")

    manager = get_formula_manager()
    formulas = manager.list_formulas()
    print_formulas(formulas)


@screen_group.command("add")
@click.option("--name", "-n", required=True, help="검색식 이름")
@click.option("--desc", "-d", required=True, help="검색식 설명")
@click.option("--cap-min", type=float, help="시가총액 최소 (억원)")
@click.option("--cap-max", type=float, help="시가총액 최대 (억원)")
@click.option("--per-min", type=float, help="PER 최소")
@click.option("--per-max", type=float, help="PER 최대")
@click.option("--pbr-max", type=float, help="PBR 최대")
@click.option("--div-min", type=float, help="배당수익률 최소 (%)")
def add_formula(name, desc, cap_min, cap_max, per_min, per_max, pbr_max, div_min):
    """새 검색식 추가

    예시:
        python main.py screen add -n "내 검색식" -d "시총 1조 이상" --cap-min 10000
    """
    print_header("주식 검색기 - 검색식 추가")

    conditions = []

    if cap_min:
        conditions.append({
            "type": "market_cap", "operator": ">=",
            "value": cap_min * 100000000, "value2": None
        })
    if cap_max:
        conditions.append({
            "type": "market_cap", "operator": "<=",
            "value": cap_max * 100000000, "value2": None
        })
    if per_min and per_max:
        conditions.append({
            "type": "per", "operator": "between",
            "value": per_min, "value2": per_max
        })
    if pbr_max:
        conditions.append({
            "type": "pbr", "operator": "<=",
            "value": pbr_max, "value2": None
        })
    if div_min:
        conditions.append({
            "type": "dividend", "operator": ">=",
            "value": div_min, "value2": None
        })

    if not conditions:
        print_error("최소 하나의 조건을 지정해주세요.")
        return

    manager = get_formula_manager()
    manager.add_formula(name, desc, conditions)
    print_success(f"검색식 '{name}' 추가 완료")


@screen_group.command("delete")
@click.argument("name")
def delete_formula(name: str):
    """검색식 삭제 (사용자 정의만)

    예시:
        python main.py screen delete "내 검색식"
    """
    print_header("주식 검색기 - 검색식 삭제")

    manager = get_formula_manager()
    if manager.delete_formula(name):
        print_success(f"검색식 '{name}' 삭제 완료")
    else:
        print_error(f"검색식 '{name}'를 삭제할 수 없습니다. (시스템 검색식이거나 존재하지 않음)")


@screen_group.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--market", "-m",
    type=click.Choice(["ALL", "KOSPI", "KOSDAQ"]),
    default="ALL",
    help="시장 선택"
)
def upload_stocks(file_path: str, market: str):
    """업체명 파일 업로드하여 일괄 조회

    지원 형식: CSV, TXT, XLSX

    예시:
        python main.py screen upload stocks.csv
        python main.py screen upload watchlist.txt
    """
    print_header("주식 검색기 - 업체명 업로드")

    loader = get_file_loader()
    stock_service = get_stock_service()

    try:
        stocks = loader.load_stock_list(file_path)
        print_info(f"{len(stocks)}개 항목 로드됨")

        results = []
        for item in stocks:
            # 코드인지 이름인지 판단
            if item.isdigit() and len(item) == 6:
                # 종목코드
                info = stock_service.get_stock_info(item)
                if info.get("name"):
                    quote = stock_service.get_current_price(item)
                    results.append({
                        "code": item,
                        "name": info["name"],
                        "market": info["market"],
                        "종가": quote.get("현재가", 0),
                        "등락률": quote.get("등락률", 0)
                    })
            else:
                # 종목명으로 검색
                search_results = stock_service.search_stock(item, market)
                if not search_results.empty:
                    row = search_results.iloc[0]
                    code = row["code"]
                    quote = stock_service.get_current_price(code)
                    results.append({
                        "code": code,
                        "name": row["name"],
                        "market": row["market"],
                        "종가": quote.get("현재가", 0),
                        "등락률": quote.get("등락률", 0)
                    })

        print_screener_result(results, "업로드 종목 현황")

    except Exception as e:
        print_error(f"파일 로드 실패: {e}")
