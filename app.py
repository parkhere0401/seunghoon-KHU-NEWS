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

# 도메인별 언론사명 매핑 사전
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
    """URL 도메인을 분석하여 언론사명을 반환"""
    try:
        domain = urllib.parse.urlparse(url).netloc.replace("www.", "").replace("m.", "")
        return PRESS_MAPPER.get(domain, domain)
    except:
        return "Naver News"

def format_date(date_str):
    """날짜 형식을 읽기 편하게 변환 (YYYY-MM-DD HH:MM)"""
    try:
        # Naver API 날짜 포맷 (RFC 822) 처리
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return date_str

# CSS 스타일
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #003366; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .meta-info { color: #666; font-size: 13px; margin-top: 5px; }
    .press-name { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 통합 뉴스 모니터링")

# --- 수집 함수 (Naver API) ---
def get_naver_news_api(keywords):
    search_query = " | ".join(keywords)
    url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(search_query)}&display=30&sort=date"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            items = response.json().get('items', [])
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                press = get_press_name(item['originallink'])
                pub_date = format_date(item['pubDate'])
                articles.append({
                    "title": title,
                    "link": item['link'],
                    "source": press,
                    "date": pub_date,
                    "type": "Naver"
                })
    except:
        return []
    return articles

# --- 수집 함수 (Google RSS) ---
def get_google_news(keywords):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    query = f"({' OR '.join([f'\"{k}\"' for k in keywords])}) after:{yesterday} before:{tomorrow}"
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "source": entry.source.title,
                "date": entry.published,
                "type": "Google"
            })
    except:
        return []
    return articles

# --- UI 실행 ---
target_keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 최신 뉴스 통합 업데이트"):
    with st.spinner('뉴스를 수집 중입니다...'):
        n_news = get_naver_news_api(target_keywords)
        g_news = get_google_news(target_keywords)
        
        all_news = n_news + g_news
        seen_titles = set()
        final_news = []
        for article in all_news:
            # 제목 앞 20자를 키로 사용하여 중복 제거
            title_id = article['title'][:20]
            if title_id not in seen_titles:
                final_news.append(article)
                seen_titles.add(title_id)

    if not final_news:
        st.warning("어제와 오늘자로 검색된 뉴스가 없습니다.")
    else:
        # [수정] 네이버, 구글 각각의 건수와 중복 제외 최종 합계 표시
        st.success(f"네이버({len(n_news)}건) + 구글({len(g_news)}건) → 중복 제외 총 {len(final_news)}건의 소식을 찾았습니다.")
        
        for article in final_news:
            badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
            st.markdown(f"""
                <div class="news-card">
                    <span class="{badge_class}">{article['type']}</span>
                    <h4 style="margin: 8px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                    <div class="meta-info">
                        <span class="press-name">출처: {article['source']}</span> | 
                        <span>게재일: {article['date']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
