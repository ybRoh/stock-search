#!/usr/bin/env python3
"""
주식 검색기 - 한국 주식 종합 분석 CLI 프로그램

사용법:
    python main.py [명령] [옵션]

명령어:
    search      종목 검색
    quote       시세 조회
    chart       차트 보기
    news        뉴스 조회
    finance     재무정보
    info        종합 정보
    screen      조건 검색
    predict     LSTM 예측
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from commands.search import search_command
from commands.quote import quote_command
from commands.chart import chart_command
from commands.news import news_command
from commands.finance import finance_command
from commands.info import info_command
from commands.screen import screen_group
from commands.predict import predict_group


console = Console()

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██╗ ██╗██╗   ██╗ ██████╗██╗██╗  ██╗                      ║
║     ██║ ██║██║   ██║██╔════╝██║██║ ██╔╝                      ║
║     ██║ ██║██║   ██║╚█████╗ ██║█████═╝                       ║
║██╗  ██║ ██║██║   ██║ ╚═══██╗██║██╔═██╗                       ║
║╚█████╔╝ ██║╚██████╔╝██████╔╝██║██║ ╚██╗                      ║
║ ╚════╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═╝                      ║
║                                                               ║
║                    주 식 검 색 기                             ║
║           한국 주식 종합 분석 CLI 프로그램                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", "-v", is_flag=True, help="버전 정보")
def cli(ctx, version):
    """주식 검색기 - 한국 주식 종합 분석 CLI 프로그램

    \b
    사용 예시:
        python main.py search 삼성          # 종목 검색
        python main.py quote 005930         # 시세 조회
        python main.py chart 005930         # 차트 보기
        python main.py info 005930          # 종합 정보
        python main.py screen list          # 검색식 목록
        python main.py screen run -f "저PER 가치주"  # 조건 검색
        python main.py predict run 005930   # LSTM 예측
    """
    if version:
        console.print("[bold]주식 검색기[/bold] v1.0.0")
        console.print("한국 주식 종합 분석 CLI 프로그램")
        return

    if ctx.invoked_subcommand is None:
        # 명령어 없이 실행 시 도움말 표시
        console.print(BANNER, style="cyan")

        help_text = """
[bold]사용 가능한 명령어:[/bold]

  [cyan]search[/cyan]   <키워드>        종목 검색 (이름 또는 코드)
  [cyan]quote[/cyan]    <종목코드>      실시간 시세 조회
  [cyan]chart[/cyan]    <종목코드>      주가 차트 표시
  [cyan]news[/cyan]     <종목코드>      관련 뉴스 조회
  [cyan]finance[/cyan]  <종목코드>      재무 지표 조회
  [cyan]info[/cyan]     <종목코드>      종합 정보 (시세+차트+뉴스)
  [cyan]screen[/cyan]                   조건 검색 (고수검색식)
  [cyan]predict[/cyan]                  LSTM 주가 예측

[bold]예시:[/bold]

  python main.py search 삼성전자
  python main.py quote 005930
  python main.py chart 005930 --period 1y
  python main.py info 005930
  python main.py screen list
  python main.py screen run -f "저PER 가치주"
  python main.py screen upload stocks.csv
  python main.py predict run 005930

[dim]자세한 도움말: python main.py [명령] --help[/dim]
"""
        console.print(help_text)


# 명령어 등록
cli.add_command(search_command)
cli.add_command(quote_command)
cli.add_command(chart_command)
cli.add_command(news_command)
cli.add_command(finance_command)
cli.add_command(info_command)
cli.add_command(screen_group)
cli.add_command(predict_group)


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]중단됨[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
        sys.exit(1)
