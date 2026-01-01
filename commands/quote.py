"""
시세 조회 명령
"""
import click
from services.stock_data import get_stock_service
from utils.display import print_quote, print_header, print_error


@click.command("quote")
@click.argument("code")
def quote_command(code: str):
    """종목 시세 조회

    예시:
        python main.py quote 005930
        python main.py quote 035720
    """
    print_header("주식 검색기 - 시세 조회")

    service = get_stock_service()

    # 종목 정보 확인
    info = service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    # 시세 조회
    quote = service.get_current_price(code)
    print_quote(info, quote, info["name"])
