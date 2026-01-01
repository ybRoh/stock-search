"""
파일 로더 서비스 - 업체명(종목) 리스트 파일 업로드 기능
"""
import os
import csv
from typing import List, Optional
import pandas as pd


class FileLoaderService:
    """CSV/TXT 파일에서 종목 리스트를 로드하는 서비스"""

    SUPPORTED_EXTENSIONS = ['.csv', '.txt', '.xlsx']

    def load_stock_list(self, file_path: str) -> List[str]:
        """
        파일에서 종목 코드/이름 리스트 로드

        Args:
            file_path: 파일 경로

        Returns:
            종목 코드 또는 이름 리스트

        지원 형식:
            - CSV: 첫 번째 열에 종목코드 또는 종목명
            - TXT: 한 줄에 하나씩 종목코드 또는 종목명
            - XLSX: 첫 번째 열에 종목코드 또는 종목명
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            return self._load_csv(file_path)
        elif ext == '.txt':
            return self._load_txt(file_path)
        elif ext == '.xlsx':
            return self._load_xlsx(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

    def _load_csv(self, file_path: str) -> List[str]:
        """CSV 파일 로드"""
        stocks = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    # 첫 번째 열의 값 사용
                    value = row[0].strip()
                    if value and not value.startswith('#'):
                        stocks.append(value)
        return stocks

    def _load_txt(self, file_path: str) -> List[str]:
        """TXT 파일 로드"""
        stocks = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                value = line.strip()
                if value and not value.startswith('#'):
                    stocks.append(value)
        return stocks

    def _load_xlsx(self, file_path: str) -> List[str]:
        """Excel 파일 로드"""
        df = pd.read_excel(file_path, header=None)
        stocks = []
        for value in df.iloc[:, 0]:
            if pd.notna(value):
                value = str(value).strip()
                if value and not value.startswith('#'):
                    stocks.append(value)
        return stocks

    def save_stock_list(self, stocks: List[str], file_path: str) -> None:
        """
        종목 리스트를 파일로 저장

        Args:
            stocks: 종목 코드 리스트
            file_path: 저장할 파일 경로
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                for stock in stocks:
                    writer.writerow([stock])
        elif ext == '.txt':
            with open(file_path, 'w', encoding='utf-8') as f:
                for stock in stocks:
                    f.write(f"{stock}\n")
        else:
            # 기본적으로 CSV로 저장
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                for stock in stocks:
                    writer.writerow([stock])


# 싱글톤 인스턴스
_file_loader: Optional[FileLoaderService] = None


def get_file_loader() -> FileLoaderService:
    """FileLoaderService 싱글톤 인스턴스 반환"""
    global _file_loader
    if _file_loader is None:
        _file_loader = FileLoaderService()
    return _file_loader
