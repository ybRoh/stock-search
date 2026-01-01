"""
LSTM 예측 명령
"""
import click
from rich.console import Console

from services.stock_data import get_stock_service
from models.lstm_predictor import get_predictor, get_lstm_screener
from utils.display import (
    print_prediction, print_lstm_screener_result, print_header,
    print_error, print_success, print_progress, print_info
)

console = Console()


@click.group("predict")
def predict_group():
    """LSTM 예측 명령 그룹"""
    pass


@predict_group.command("run")
@click.argument("code")
@click.option("--train", is_flag=True, help="모델 재학습")
@click.option("--epochs", default=50, help="학습 에포크 (기본: 50)")
def run_predict(code: str, train: bool, epochs: int):
    """종목 주가 방향 예측

    예시:
        python main.py predict run 005930
        python main.py predict run 035720 --train --epochs 100
    """
    print_header("주식 검색기 - LSTM 예측")

    stock_service = get_stock_service()
    predictor = get_predictor()

    # 종목 정보 확인
    info = stock_service.get_stock_info(code)
    if not info.get("name"):
        print_error(f"종목코드 '{code}'를 찾을 수 없습니다.")
        return

    name = info["name"]

    # 학습 또는 로드
    if train or not predictor.has_model(code):
        print_info(f"'{name}' 모델 학습 중...")

        # 학습 데이터 로드
        df = stock_service.get_price_history(code, "1y", "d")
        if df.empty or len(df) < 100:
            print_error("학습에 충분한 데이터가 없습니다. (최소 100일)")
            return

        history = predictor.train(
            df, epochs=epochs,
            progress_callback=print_progress
        )

        final_acc = history["val_accuracy"][-1] * 100
        print_success(f"학습 완료 (검증 정확도: {final_acc:.1f}%)")

        predictor.save_model(code)
        print_success(f"모델 저장됨")
    else:
        print_info(f"저장된 모델 로드 중...")
        predictor.load_model(code)

    # 예측
    print_info("예측 수행 중...")
    df = stock_service.get_price_history(code, "3m", "d")
    prediction = predictor.predict(df)

    print()
    print_prediction(prediction, name)


@predict_group.command("screen")
@click.option(
    "--market", "-m",
    type=click.Choice(["ALL", "KOSPI", "KOSDAQ"]),
    default="ALL",
    help="시장 선택"
)
@click.option("--confidence", "-c", default=60.0, help="최소 신뢰도 (%)")
@click.option("--top", "-n", default=20, help="상위 N개 종목만 분석")
def screen_predict(market: str, confidence: float, top: int):
    """LSTM 상승 예측 종목 스크리닝

    예시:
        python main.py predict screen
        python main.py predict screen -m KOSPI -c 70 -n 50
    """
    print_header("주식 검색기 - LSTM 스크리닝")

    stock_service = get_stock_service()
    screener = get_lstm_screener()

    # 시가총액 상위 종목 선정 (전체 스캔은 시간이 오래 걸림)
    print_info(f"시가총액 상위 {top}개 종목 선정 중...")

    stocks = stock_service.get_stock_list(market)
    if stocks.empty:
        print_error("종목 리스트를 가져올 수 없습니다.")
        return

    # 시가총액 정보 추가 및 정렬
    market_caps = []
    for _, row in stocks.head(top * 2).iterrows():
        cap_info = stock_service.get_market_cap(row["code"])
        if "error" not in cap_info:
            market_caps.append({
                "code": row["code"],
                "cap": cap_info.get("시가총액", 0)
            })

    market_caps.sort(key=lambda x: x["cap"], reverse=True)
    codes = [x["code"] for x in market_caps[:top]]

    print_info(f"LSTM 분석 시작... (신뢰도 {confidence}% 이상)")

    results = screener.screen_bullish(
        codes, confidence,
        progress_callback=print_progress
    )

    print()
    print_lstm_screener_result(results)
