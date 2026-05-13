import streamlit as st
import feedparser
import requests
from datetime import datetime, date, timedelta
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="경희대학교 및 의료기관 뉴스 클리핑", page_icon="🏫", layout="wide")

# API 키
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# --- [매체 티어 정보 고정 데이터] ---
TIER_DATA = {
    1: ["조선일보", "중앙일보", "동아일보", "매일경제", "한국경제", "한겨레", "경향신문", "국민일보", "연합뉴스", "YTN", "SBS", "KBS", "MBC", "JTBC"],
    2: ["한국일보", "문화일보", "서울신문", "세계일보", "머니투데이", "서울경제", "뉴시스", "뉴스1", "파이낸셜뉴스", "조선비즈", "이데일리", "한국경제TV", "아시아경제", "연합뉴스TV", "MBN", "채널A", "EBS"],
    3: ["헤럴드경제", "전자신문", "오마이뉴스", "머니S", "매일신문", "아이뉴스24", "프레시안", "부산일보", "더팩트", "노컷뉴스", "블로터", "미디어오늘", "디지털데일리", "조세일보", "디지털타임스", "SBS Biz", "데일리안", "TV조선", "강원일보", "코리아헤럴드", "쿠키뉴스", "KTV", "IT동아", "한의신문", "민족의학신문", "매일일보", "로리더", "신아일보", "시사IN", "시사저널"]
}

# 도메인 기반 매핑 사전 (중앙일보 등 핵심 매체 포함)
TIER_MAPPER = {
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "hani.co.kr": ("한겨레", 1),
    "khan.co.kr": ("경향신문", 1), "kmib.co.kr": ("국민일보", 1), "yna.co.kr": ("연합뉴스", 1),
    "ytn.co.kr": ("YTN", 1), "sbs.co.kr": ("SBS", 1), "kbs.co.kr": ("KBS", 1),
    "imbc.com": ("MBC", 1), "jtbc.co.kr": ("JTBC", 1),
    "hankookilbo.com": ("한국일보", 2), "newsis.com": ("뉴시스", 2), "news1.kr": ("뉴스1", 2),
    "edaily.co.kr": ("이데일리", 2), "mt.co.kr": ("머니투데이", 2), "sedaily.com": ("서울경제", 2),
    "akomnews.com": ("한의신문", 3), "mjmedi.com": ("민족의학신문", 3), "dailypop.kr": ("데일리팝", 4)
}

def get_tier_info(url, source_name):
    """URL 도메인을 분석하여 언론사명과 티어를 결정합니다."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").replace("m.", "")
        
        # 1. 티어 매퍼에서 도메인 검색
        if domain in TIER_MAPPER:
            return TIER_MAPPER[domain][0], TIER_MAPPER[domain][1]
        
        # 2. 매체명 텍스트 매칭 (티어 1~3)
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        
        # 3. 매핑되지 않은 경우 도메인 이름을 출처로 사용 (4티어)
        return domain, 4
    except:
        return source_name, 4

def parse_to_datetime(date_str):
    formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=None)
        except: continue
    return datetime.now().replace(tzinfo=None)

# --- 사이드바: 매체 정보 상시 노출 ---
with st.sidebar:
    st.header("📊 매체 등급 정보")
    for tier in [1, 2, 3]:
        with st.expander(f"Tier {tier} 매체 리스트", expanded=True):
            st.write(", ".join(TIER_DATA[tier]))
    st.markdown("---")
    days_to_search = st.slider("조회 기간 설정 (일)", 1, 7, 3, help="중앙일보 등 과거 기사가 안 보일 경우 기간을 늘려보세요.")
    st.caption("※ 유튜브, 페이스북, 인스타그램 제외")

# 스타일 설정
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #bdc3c7; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tier-1 { border-left: 10px solid #d32f2f; background-color: #fff9f9; }
    .tier-2 { border-left: 10px solid #f39c12; }
    .tier-3 { border-left: 10px solid #3498db; }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .press-label { color: #d32f2f; font-weight: bold; }
    .tier-label { font-size: 12px; color: #666; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("경희대학교 및 의료기관 뉴스 클리핑")

# --- 수집 함수 ---
def get_naver_news_api(keywords, days):
    search_query = " | ".join(keywords)
    url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(search_query)}&display=100&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            for item in response.json().get('items', []):
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                name, tier = get_tier_info(item['originallink'], "Naver News")
