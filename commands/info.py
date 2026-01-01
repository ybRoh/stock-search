"""
종합 정보 명령 - 종목의 모든 정보를 한눈에
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

from services.stock_data import get_stock_service
from services.news_service import get_news_service
from utils.display import (
    print_quote, print_fundamental, print_market_cap,
    print_chart, print_news, print_header, print_error
)

console = Console()


@click.command("info")
@click.argument("code")
@click.option("--no-chart", is_flag=True, help="차트 생략")
@click.option("--no-news", is_flag=True, help="뉴스 생략")
def info_command(code: str, no_chart: bool, no_news: bool):
    """종목 종합 정보 조회

    시세, 재무지표, 차트, 뉴스를 한번에 확인

    예시:
        python main.py info 005930
        python main.py info 035720 --no-chart
    """
    print_header("주식 검색기 - 종합 정보")

    stock_service = get_stock_service()
    news_service = get_news_service()

    # 종목 정보 확인
    info = stock_service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    name = info["name"]
    console.print(f"\n[bold cyan]{name}[/bold cyan] ({code}) - {info['market']}\n")

    # 1. 시세 정보
    console.print("[bold]시세 정보[/bold]")
    console.print("-" * 40)
    quote = stock_service.get_current_price(code)
    print_quote(info, quote, name)

    # 2. 재무 지표
    console.print("\n[bold]재무 지표[/bold]")
    console.print("-" * 40)
    fundamental = stock_service.get_fundamental(code)
    print_fundamental(fundamental, name)

    # 3. 시가총액
    console.print()
    market_cap = stock_service.get_market_cap(code)
    print_market_cap(market_cap, name)

    # 4. 차트
    if not no_chart:
        console.print("\n[bold]주가 차트 (3개월)[/bold]")
        console.print("-" * 40)
        df = stock_service.get_price_history(code, "3m", "d")
        if not df.empty:
            dates = [d.strftime("%m/%d") for d in df.index]
            prices = df["종가"].tolist()
            print_chart(dates, prices, f"{name} 3개월 차트", height=15)

    # 5. 뉴스
    if not no_news:
        console.print("\n[bold]최신 뉴스[/bold]")
        console.print("-" * 40)
        news_list = news_service.get_stock_news(code, 5)
        print_news(news_list, f"{name} 관련 뉴스")
