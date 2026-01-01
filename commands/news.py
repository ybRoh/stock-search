"""
뉴스 명령 - 종목 관련 뉴스 조회
"""
import click
from services.stock_data import get_stock_service
from services.news_service import get_news_service
from utils.display import print_news, print_header, print_error


@click.command("news")
@click.argument("code")
@click.option(
    "--count", "-n",
    default=10,
    help="뉴스 개수 (기본: 10)"
)
def news_command(code: str, count: int):
    """종목 관련 뉴스 조회

    예시:
        python main.py news 005930
        python main.py news 035720 -n 20
    """
    print_header("주식 검색기 - 뉴스")

    stock_service = get_stock_service()
    news_service = get_news_service()

    # 종목 정보 확인
    info = stock_service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    # 뉴스 조회
    news_list = news_service.get_stock_news(code, count)
    print_news(news_list, f"{info['name']} 관련 뉴스")
