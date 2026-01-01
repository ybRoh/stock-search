"""
출력 유틸리티 - Rich 라이브러리를 이용한 터미널 UI
"""
from typing import List, Dict, Any, Optional
import plotext as plt

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich import box


console = Console()


def print_header(title: str) -> None:
    """헤더 출력"""
    console.print()
    console.print(Panel(
        Text(title, style="bold white", justify="center"),
        style="blue",
        box=box.DOUBLE
    ))
    console.print()


def print_stock_table(stocks: List[Dict[str, Any]], title: str = "검색 결과") -> None:
    """종목 테이블 출력"""
    if not stocks:
        console.print("[yellow]검색 결과가 없습니다.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED)
    table.add_column("코드", style="cyan", no_wrap=True)
    table.add_column("종목명", style="white")
    table.add_column("시장", style="green")

    for stock in stocks:
        table.add_row(
            stock.get("code", ""),
            stock.get("name", ""),
            stock.get("market", "")
        )

    console.print(table)


def print_quote(info: Dict[str, Any], quote: Dict[str, Any], name: str = "") -> None:
    """시세 정보 출력"""
    if "error" in quote:
        console.print(f"[red]오류: {quote['error']}[/red]")
        return

    # 등락 색상 결정
    change = quote.get("전일대비", 0)
    change_rate = quote.get("등락률", 0)

    if change > 0:
        change_style = "red"
        change_symbol = "▲"
    elif change < 0:
        change_style = "blue"
        change_symbol = "▼"
    else:
        change_style = "white"
        change_symbol = "-"

    title = f"{name} ({info.get('code', '')})"

    table = Table(title=title, box=box.ROUNDED, show_header=False)
    table.add_column("항목", style="dim")
    table.add_column("값", justify="right")

    table.add_row("현재가", f"[bold]{quote.get('현재가', 0):,}[/bold]원")
    table.add_row(
        "전일대비",
        f"[{change_style}]{change_symbol} {abs(change):,} ({change_rate:+.2f}%)[/{change_style}]"
    )
    table.add_row("시가", f"{quote.get('시가', 0):,}원")
    table.add_row("고가", f"[red]{quote.get('고가', 0):,}[/red]원")
    table.add_row("저가", f"[blue]{quote.get('저가', 0):,}[/blue]원")
    table.add_row("거래량", f"{quote.get('거래량', 0):,}주")
    table.add_row("거래대금", f"{quote.get('거래대금', 0) // 100000000:,}억원")

    console.print(table)


def print_fundamental(data: Dict[str, Any], name: str = "") -> None:
    """재무 지표 출력"""
    if "error" in data:
        console.print(f"[red]오류: {data['error']}[/red]")
        return

    table = Table(title=f"{name} 재무 지표", box=box.ROUNDED, show_header=False)
    table.add_column("항목", style="dim")
    table.add_column("값", justify="right")

    table.add_row("PER", f"{data.get('PER', 0):.2f}")
    table.add_row("PBR", f"{data.get('PBR', 0):.2f}")
    table.add_row("배당수익률", f"{data.get('배당수익률', 0):.2f}%")
    table.add_row("EPS", f"{data.get('EPS', 0):,}원")
    table.add_row("BPS", f"{data.get('BPS', 0):,}원")

    console.print(table)


def print_market_cap(data: Dict[str, Any], name: str = "") -> None:
    """시가총액 정보 출력"""
    if "error" in data:
        console.print(f"[red]오류: {data['error']}[/red]")
        return

    cap_억 = data.get('시가총액_억', 0)
    cap_조 = cap_억 / 10000

    table = Table(title=f"{name} 시가총액", box=box.ROUNDED, show_header=False)
    table.add_column("항목", style="dim")
    table.add_column("값", justify="right")

    if cap_조 >= 1:
        table.add_row("시가총액", f"[bold]{cap_조:,.2f}조원[/bold]")
    else:
        table.add_row("시가총액", f"[bold]{cap_억:,.0f}억원[/bold]")

    table.add_row("상장주식수", f"{data.get('상장주식수', 0):,}주")

    console.print(table)


def print_chart(
    dates: List[str],
    prices: List[float],
    title: str = "주가 차트",
    height: int = 20,
    width: int = 80
) -> None:
    """터미널 차트 출력"""
    plt.clear_figure()
    plt.plot_size(width, height)

    # x축을 인덱스로, 레이블만 날짜로 표시
    x = list(range(len(prices)))
    plt.plot(x, prices, marker="braille")

    # x축 레이블 설정 (간격을 두고 표시)
    if len(dates) > 10:
        step = len(dates) // 10
        x_ticks = x[::step]
        x_labels = dates[::step]
        plt.xticks(x_ticks, x_labels)
    else:
        plt.xticks(x, dates)

    plt.title(title)
    plt.xlabel("날짜")
    plt.ylabel("가격")

    plt.show()


def print_news(news_list: List[Dict[str, Any]], title: str = "관련 뉴스") -> None:
    """뉴스 목록 출력"""
    if not news_list:
        console.print("[yellow]뉴스가 없습니다.[/yellow]")
        return

    if "error" in news_list[0]:
        console.print(f"[red]오류: {news_list[0]['error']}[/red]")
        return

    console.print(f"\n[bold]{title}[/bold]\n")

    for i, news in enumerate(news_list, 1):
        date = news.get("date", "")
        source = news.get("source", "")
        title_text = news.get("title", "")

        console.print(f"[cyan]{i}.[/cyan] {title_text}")
        console.print(f"   [dim]{source} | {date}[/dim]")
        console.print()


def print_screener_result(
    results: List[Dict[str, Any]],
    title: str = "스크리닝 결과"
) -> None:
    """스크리너 결과 출력"""
    if not results:
        console.print("[yellow]조건에 맞는 종목이 없습니다.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("코드", style="cyan", no_wrap=True)
    table.add_column("종목명", style="white")
    table.add_column("시장", style="green")
    table.add_column("현재가", justify="right")
    table.add_column("등락률", justify="right")
    table.add_column("시가총액", justify="right")

    for i, row in enumerate(results, 1):
        change_rate = row.get("등락률", 0)
        if change_rate > 0:
            rate_style = "red"
        elif change_rate < 0:
            rate_style = "blue"
        else:
            rate_style = "white"

        cap = row.get("시가총액", 0)
        cap_str = f"{cap // 100000000:,}억" if cap else "-"

        table.add_row(
            str(i),
            row.get("code", ""),
            row.get("name", ""),
            row.get("market", ""),
            f"{row.get('종가', 0):,}",
            f"[{rate_style}]{change_rate:+.2f}%[/{rate_style}]",
            cap_str
        )

    console.print(table)
    console.print(f"\n총 [bold]{len(results)}[/bold]개 종목")


def print_formulas(formulas: List[Any]) -> None:
    """검색식 목록 출력"""
    if not formulas:
        console.print("[yellow]저장된 검색식이 없습니다.[/yellow]")
        return

    table = Table(title="고수 검색식 목록", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("이름", style="cyan")
    table.add_column("설명", style="white")
    table.add_column("조건 수", justify="center")
    table.add_column("작성자", style="dim")

    for i, formula in enumerate(formulas, 1):
        table.add_row(
            str(i),
            formula.name,
            formula.description,
            str(len(formula.conditions)),
            formula.author
        )

    console.print(table)


def print_prediction(prediction: Dict[str, Any], name: str = "") -> None:
    """LSTM 예측 결과 출력"""
    if "error" in prediction:
        console.print(f"[red]오류: {prediction['error']}[/red]")
        return

    direction = prediction.get("direction", "")
    confidence = prediction.get("confidence", 0)
    signal = prediction.get("signal", "")

    direction_style = "red" if direction == "상승" else "blue"
    signal_style = "red bold" if signal == "매수" else "blue bold"

    panel_content = f"""
[bold]예측 방향:[/bold] [{direction_style}]{direction}[/{direction_style}]
[bold]확률:[/bold] {prediction.get('probability', 0):.1f}%
[bold]신뢰도:[/bold] {confidence:.1f}%
[bold]시그널:[/bold] [{signal_style}]{signal}[/{signal_style}]
    """

    console.print(Panel(
        panel_content.strip(),
        title=f"{name} LSTM 예측",
        border_style=direction_style
    ))


def print_lstm_screener_result(results: List[Dict[str, Any]]) -> None:
    """LSTM 스크리너 결과 출력"""
    if not results:
        console.print("[yellow]조건에 맞는 종목이 없습니다.[/yellow]")
        return

    table = Table(title="LSTM 상승 예측 종목", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("코드", style="cyan", no_wrap=True)
    table.add_column("종목명", style="white")
    table.add_column("예측", justify="center")
    table.add_column("확률", justify="right")
    table.add_column("신뢰도", justify="right")
    table.add_column("시그널", justify="center")

    for i, row in enumerate(results, 1):
        direction_style = "red" if row["direction"] == "상승" else "blue"
        signal_style = "red bold" if row["signal"] == "매수" else "blue bold"

        table.add_row(
            str(i),
            row.get("code", ""),
            row.get("name", ""),
            f"[{direction_style}]{row['direction']}[/{direction_style}]",
            f"{row['probability']:.1f}%",
            f"{row['confidence']:.1f}%",
            f"[{signal_style}]{row['signal']}[/{signal_style}]"
        )

    console.print(table)
    console.print(f"\n총 [bold]{len(results)}[/bold]개 종목")


def print_success(message: str) -> None:
    """성공 메시지"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """에러 메시지"""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """경고 메시지"""
    console.print(f"[yellow]![/yellow] {message}")


def print_info(message: str) -> None:
    """정보 메시지"""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_progress(message: str) -> None:
    """진행 상황 메시지"""
    console.print(f"[dim]→ {message}[/dim]")
