"""
재무정보 명령 - 재무 지표 조회
"""
import click
from services.stock_data import get_stock_service
from utils.display import (
    print_fundamental, print_market_cap, print_header, print_error
)


@click.command("finance")
@click.argument("code")
def finance_command(code: str):
    """재무 지표 조회 (PER, PBR, 시가총액 등)

    예시:
        python main.py finance 005930
        python main.py finance 035720
    """
    print_header("주식 검색기 - 재무정보")

    service = get_stock_service()

    # 종목 정보 확인
    info = service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    name = info["name"]

    # 재무 지표 조회
    fundamental = service.get_fundamental(code)
    print_fundamental(fundamental, name)

    print()

    # 시가총액 조회
    market_cap = service.get_market_cap(code)
    print_market_cap(market_cap, name)
