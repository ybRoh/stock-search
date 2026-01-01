"""
차트 명령 - 터미널 차트 표시
"""
import click
from services.stock_data import get_stock_service
from utils.display import print_chart, print_header, print_error


@click.command("chart")
@click.argument("code")
@click.option(
    "--period", "-p",
    type=click.Choice(["1m", "3m", "6m", "1y", "3y"]),
    default="3m",
    help="기간 (1m, 3m, 6m, 1y, 3y)"
)
@click.option(
    "--interval", "-i",
    type=click.Choice(["d", "w", "m"]),
    default="d",
    help="간격 (d: 일봉, w: 주봉, m: 월봉)"
)
def chart_command(code: str, period: str, interval: str):
    """주가 차트 표시

    예시:
        python main.py chart 005930
        python main.py chart 035720 -p 1y -i w
    """
    print_header("주식 검색기 - 주가 차트")

    service = get_stock_service()

    # 종목 정보 확인
    info = service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    # 가격 데이터 조회
    df = service.get_price_history(code, period, interval)
    if df.empty:
        print_error("가격 데이터를 가져올 수 없습니다.")
        return

    # 차트 출력
    dates = [d.strftime("%m/%d") for d in df.index]
    prices = df["종가"].tolist()

    period_names = {
        "1m": "1개월",
        "3m": "3개월",
        "6m": "6개월",
        "1y": "1년",
        "3y": "3년"
    }
    interval_names = {
        "d": "일봉",
        "w": "주봉",
        "m": "월봉"
    }

    title = f"{info['name']} ({code}) - {period_names[period]} {interval_names[interval]}"
    print_chart(dates, prices, title)
