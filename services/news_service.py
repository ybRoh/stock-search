"""
뉴스 서비스 - 종목 관련 뉴스 크롤링
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime


class NewsService:
    """네이버 금융에서 종목 뉴스를 크롤링하는 서비스"""

    NAVER_NEWS_URL = "https://finance.naver.com/item/news_news.naver"

    def _get_headers(self, code: str = "") -> Dict[str, str]:
        """요청 헤더 생성"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if code:
            headers["Referer"] = f"https://finance.naver.com/item/news.naver?code={code}"
        return headers

    def get_stock_news(self, code: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        종목 관련 뉴스 조회

        Args:
            code: 종목코드 (6자리)
            count: 가져올 뉴스 개수

        Returns:
            뉴스 리스트 [{title, date, url, source}, ...]
        """
        try:
            params = {
                "code": code,
                "page": 1,
                "sm": "title_entity_id.basic",
                "clusterId": ""
            }

            response = requests.get(
                self.NAVER_NEWS_URL,
                params=params,
                headers=self._get_headers(code),
                timeout=10
            )
            response.raise_for_status()

            # EUC-KR 인코딩 처리
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            news_list = []

            # 뉴스 테이블에서 뉴스 항목 추출
            # 모든 tr 중에서 td.title을 포함하는 것만 선택
            rows = soup.select('table.type5 tr')

            for row in rows:
                if len(news_list) >= count:
                    break

                # 제목이 있는 행만 처리
                title_elem = row.select_one('td.title a.tit')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                # HTML 엔티티 정리
                title = title.replace('\xa0', ' ')

                href = title_elem.get('href', '')
                # 네이버 뉴스 URL로 변환
                if href and '/news_read.naver' in href:
                    # article_id와 office_id 추출하여 직접 뉴스 URL 생성
                    import re
                    article_match = re.search(r'article_id=(\d+)', href)
                    office_match = re.search(r'office_id=(\d+)', href)
                    if article_match and office_match:
                        article_id = article_match.group(1)
                        office_id = office_match.group(1)
                        url = f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
                    else:
                        url = "https://finance.naver.com" + href
                else:
                    url = href if href.startswith('http') else ""

                # 날짜와 출처
                info_elem = row.select_one('td.info')
                source = info_elem.get_text(strip=True) if info_elem else ""

                date_elem = row.select_one('td.date')
                date = date_elem.get_text(strip=True) if date_elem else ""

                news_list.append({
                    "title": title,
                    "date": date,
                    "url": url,
                    "source": source
                })

            return news_list

        except Exception as e:
            return [{"error": str(e)}]

    def get_market_news(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        시장 전체 주요 뉴스 조회

        Args:
            count: 가져올 뉴스 개수

        Returns:
            뉴스 리스트
        """
        try:
            url = "https://finance.naver.com/news/mainnews.naver"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            news_list = []

            news_items = soup.select('ul.newsList li')

            for item in news_items[:count]:
                title_elem = item.select_one('a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = "https://finance.naver.com" + url

                date_elem = item.select_one('.date')
                date = date_elem.get_text(strip=True) if date_elem else ""

                news_list.append({
                    "title": title,
                    "date": date,
                    "url": url,
                    "source": "네이버 금융"
                })

            return news_list

        except Exception as e:
            return [{"error": str(e)}]


# 싱글톤 인스턴스
_news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """NewsService 싱글톤 인스턴스 반환"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
