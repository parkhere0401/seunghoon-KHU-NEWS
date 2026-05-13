import streamlit as st
import feedparser
import requests
from datetime import datetime, date, timedelta
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="KHU News Dashboard", page_icon="🏫", layout="wide")

# API 키 (전달해주신 키 적용)
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# 도메인별 언론사명 매핑 사전 (이 목록에 있는 매체는 'Major'로 분류되어 상단에 노출됩니다)
PRESS_MAPPER = {
    "chosun.com": "조선일보",
    "m-i.kr": "매일일보",
    "lawleader.co.kr": "로리더",
    "sisajournal.com": "시사저널",
    "shinailbo.co.kr": "신아일보",
    "sisain.co.kr": "시사IN",
    "akomnews.com": "한의신문",
    "mjmedi.com": "민족의학신문",
    "khan.co.kr": "경향신문/주간경향",
    "yna.co.kr": "연합뉴스",
    "ytn.co.kr": "YTN",
    "donga.com": "동아일보",
    "joongang.co.kr": "중앙일보",
    "hani.co.kr": "한겨레",
    "kmib.co.kr": "국민일보",
    "sedaily.com": "서울경제",
    "hankyung.com": "한국경제",
    "edaily.co.kr": "이데일리",
    "mt.co.kr": "머니투데이"
}

def get_press_name(url):
    try:
        domain = urllib.parse.urlparse(url).netloc.replace("www.", "").replace("m.", "")
        return PRESS_MAPPER.get(domain, domain)
    except:
        return "Naver News"

def parse_to_datetime(date_str):
    """정확한 정렬을 위해 다양한 날짜 포맷을 datetime 객체로 변환"""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # Naver API / Google RSS 표준
        '%a, %d %b %Y %H:%M:%S GMT', # Google RSS 일부
        '%Y-%m-%d %H:%M:%S'          # 기타
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return datetime.now() # 변환 실패 시 현재 시간 반환

# CSS 스타일 (가독성 최적화 및 메이저 강조)
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #003366; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .major-card { border-left: 8px solid #d32f2f; background-color: #fff9f9; } /* 주요 언론사 강조 스타일 */
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .meta-info { color: #666; font-size: 13px; margin-top: 5px; }
    .press-name { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 뉴스 통합 브리핑")

# --- 수집 함수 (Naver API) ---
def get_naver_news_api(keywords):
    search_query = " | ".join(keywords)
    url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(search_query)}&display=50&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            for item in response.json().get('items', []):
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                press = get_press_name(item['originallink'])
                articles.append({
                    "title": title, "link": item['link'], "source": press,
                    "raw_date": item['pub
