"""
검색 명령 - 종목 검색 기능
"""
import click
from services.stock_data import get_stock_service
from utils.display import print_stock_table, print_header


@click.command("search")
@click.argument("keyword")
@click.option(
    "--market", "-m",
    type=click.Choice(["ALL", "KOSPI", "KOSDAQ"]),
    default="ALL",
    help="시장 선택 (ALL, KOSPI, KOSDAQ)"
)
def search_command(keyword: str, market: str):
    """종목 검색 (종목명 또는 종목코드)

    예시:
        python main.py search 삼성
        python main.py search 005930
        python main.py search 카카오 -m KOSPI
    """
    print_header("주식 검색기 - 종목 검색")

    service = get_stock_service()
    results = service.search_stock(keyword, market)

    stocks = results.to_dict("records")
    print_stock_table(stocks, f"'{keyword}' 검색 결과")
