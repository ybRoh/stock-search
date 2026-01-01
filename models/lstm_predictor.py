"""
LSTM 주가 예측 모델
과거 데이터를 기반으로 향후 주가 방향을 예측
"""
import os
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler


class LSTMModel(nn.Module):
    """LSTM 신경망 모델"""

    def __init__(
        self,
        input_size: int = 5,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2
    ):
        super(LSTMModel, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, output_size)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # LSTM
        lstm_out, _ = self.lstm(x)
        # 마지막 시점의 출력만 사용
        last_output = lstm_out[:, -1, :]
        # Fully connected
        out = self.fc(last_output)
        return out


class StockPredictor:
    """주가 예측기"""

    def __init__(
        self,
        sequence_length: int = 20,
        hidden_size: int = 64,
        num_layers: int = 2,
        model_dir: Optional[str] = None
    ):
        """
        Args:
            sequence_length: 입력 시퀀스 길이 (몇 일치 데이터를 사용할지)
            hidden_size: LSTM 히든 레이어 크기
            num_layers: LSTM 레이어 수
            model_dir: 모델 저장 경로
        """
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        if model_dir is None:
            home = os.path.expanduser("~")
            model_dir = os.path.join(home, ".stock_search", "models")
        os.makedirs(model_dir, exist_ok=True)
        self.model_dir = model_dir

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = MinMaxScaler()
        self.model: Optional[LSTMModel] = None

    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str = "종가"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        데이터 전처리

        Args:
            df: OHLCV DataFrame
            target_col: 예측 대상 컬럼

        Returns:
            X, y 배열
        """
        # 사용할 특성 선택
        features = ['시가', '고가', '저가', '종가', '거래량']
        available_features = [f for f in features if f in df.columns]

        if len(available_features) < 2:
            raise ValueError("데이터에 충분한 특성이 없습니다")

        data = df[available_features].values
        scaled_data = self.scaler.fit_transform(data)

        X, y = [], []
        target_idx = available_features.index(target_col)

        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i - self.sequence_length:i])
            # 다음날 종가가 오늘보다 높으면 1, 아니면 0 (상승/하락 예측)
            if i < len(scaled_data) - 1:
                y.append(1 if scaled_data[i + 1, target_idx] > scaled_data[i, target_idx] else 0)
            else:
                y.append(0)

        return np.array(X), np.array(y)

    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, List[float]]:
        """
        모델 학습

        Args:
            df: OHLCV DataFrame
            epochs: 학습 에포크 수
            batch_size: 배치 크기
            learning_rate: 학습률
            validation_split: 검증 데이터 비율
            progress_callback: 진행 콜백

        Returns:
            학습 히스토리 (loss, accuracy)
        """
        X, y = self.prepare_data(df)

        # 학습/검증 분리
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # 텐서 변환
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        X_val_tensor = torch.FloatTensor(X_val).to(self.device)
        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)

        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        # 모델 초기화
        input_size = X_train.shape[2]
        self.model = LSTMModel(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            output_size=1
        ).to(self.device)

        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)

        history = {"loss": [], "val_loss": [], "accuracy": [], "val_accuracy": []}

        for epoch in range(epochs):
            self.model.train()
            total_loss = 0
            correct = 0
            total = 0

            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                predicted = (torch.sigmoid(outputs) > 0.5).float()
                correct += (predicted == batch_y).sum().item()
                total += batch_y.size(0)

            avg_loss = total_loss / len(train_loader)
            accuracy = correct / total

            # 검증
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor)
                val_loss = criterion(val_outputs, y_val_tensor).item()
                val_predicted = (torch.sigmoid(val_outputs) > 0.5).float()
                val_accuracy = (val_predicted == y_val_tensor).sum().item() / len(y_val)

            history["loss"].append(avg_loss)
            history["val_loss"].append(val_loss)
            history["accuracy"].append(accuracy)
            history["val_accuracy"].append(val_accuracy)

            if progress_callback and (epoch + 1) % 10 == 0:
                progress_callback(
                    f"Epoch {epoch + 1}/{epochs} - "
                    f"Loss: {avg_loss:.4f}, Acc: {accuracy:.4f}, "
                    f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}"
                )

        return history

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        주가 방향 예측

        Args:
            df: 최근 OHLCV 데이터

        Returns:
            예측 결과 딕셔너리
        """
        if self.model is None:
            return {"error": "모델이 학습되지 않았습니다"}

        try:
            features = ['시가', '고가', '저가', '종가', '거래량']
            available_features = [f for f in features if f in df.columns]

            data = df[available_features].values[-self.sequence_length:]
            if len(data) < self.sequence_length:
                return {"error": f"최소 {self.sequence_length}일 데이터가 필요합니다"}

            scaled_data = self.scaler.transform(data)
            X = torch.FloatTensor(scaled_data).unsqueeze(0).to(self.device)

            self.model.eval()
            with torch.no_grad():
                output = self.model(X)
                prob = torch.sigmoid(output).item()

            direction = "상승" if prob > 0.5 else "하락"
            confidence = prob if prob > 0.5 else 1 - prob

            return {
                "direction": direction,
                "probability": round(prob * 100, 2),
                "confidence": round(confidence * 100, 2),
                "signal": "매수" if direction == "상승" else "매도"
            }
        except Exception as e:
            return {"error": str(e)}

    def save_model(self, code: str) -> str:
        """모델 저장"""
        if self.model is None:
            raise ValueError("저장할 모델이 없습니다")

        path = os.path.join(self.model_dir, f"lstm_{code}.pt")
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "scaler": self.scaler,
            "sequence_length": self.sequence_length,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "input_size": self.model.lstm.input_size
        }, path)
        return path

    def load_model(self, code: str) -> bool:
        """모델 로드"""
        path = os.path.join(self.model_dir, f"lstm_{code}.pt")
        if not os.path.exists(path):
            print(f"[LSTM] {code} 모델 파일 없음: {path}")
            return False

        try:
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)
            self.scaler = checkpoint["scaler"]
            self.sequence_length = checkpoint["sequence_length"]
            self.hidden_size = checkpoint["hidden_size"]
            self.num_layers = checkpoint["num_layers"]

            self.model = LSTMModel(
                input_size=checkpoint["input_size"],
                hidden_size=self.hidden_size,
                num_layers=self.num_layers
            ).to(self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.eval()
            print(f"[LSTM] {code} 모델 로드 성공")
            return True
        except Exception as e:
            print(f"[LSTM] {code} 모델 로드 에러: {e}")
            return False

    def has_model(self, code: str) -> bool:
        """저장된 모델 존재 여부 확인"""
        path = os.path.join(self.model_dir, f"lstm_{code}.pt")
        return os.path.exists(path)


class LSTMScreener:
    """LSTM 기반 종목 스크리너"""

    def __init__(self):
        self.predictor = StockPredictor()

    def screen_bullish(
        self,
        codes: List[str],
        min_confidence: float = 60.0,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        상승 예측 종목 스크리닝

        Args:
            codes: 종목 코드 리스트
            min_confidence: 최소 신뢰도 (%)
            progress_callback: 진행 콜백

        Returns:
            상승 예측 종목 리스트
        """
        from pykrx import stock as krx

        results = []
        total = len(codes)

        for i, code in enumerate(codes):
            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(f"LSTM 분석 중... {i + 1}/{total}")

            try:
                # 저장된 모델이 있으면 로드
                if self.predictor.has_model(code):
                    self.predictor.load_model(code)
                else:
                    # 모델이 없으면 학습
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)
                    df = krx.get_market_ohlcv(
                        start_date.strftime("%Y%m%d"),
                        end_date.strftime("%Y%m%d"),
                        code
                    )

                    if len(df) < 100:
                        continue

                    self.predictor.train(df, epochs=30)
                    self.predictor.save_model(code)

                # 예측
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                recent_df = krx.get_market_ohlcv(
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    code
                )

                prediction = self.predictor.predict(recent_df)

                if "error" not in prediction:
                    if prediction["direction"] == "상승" and prediction["confidence"] >= min_confidence:
                        results.append({
                            "code": code,
                            "name": krx.get_market_ticker_name(code),
                            **prediction
                        })

            except Exception:
                continue

        # 신뢰도 순으로 정렬
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results


# 싱글톤 인스턴스
_predictor: Optional[StockPredictor] = None
_screener: Optional[LSTMScreener] = None


def get_predictor() -> StockPredictor:
    """StockPredictor 싱글톤 인스턴스 반환"""
    global _predictor
    if _predictor is None:
        _predictor = StockPredictor()
    return _predictor


def get_lstm_screener() -> LSTMScreener:
    """LSTMScreener 싱글톤 인스턴스 반환"""
    global _screener
    if _screener is None:
        _screener = LSTMScreener()
    return _screener
