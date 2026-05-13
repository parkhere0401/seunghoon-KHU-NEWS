import streamlit as st
import feedparser
import requests
from datetime import date, timedelta
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="KHU News Dashboard", page_icon="🏫", layout="wide")

# 보내주신 네이버 API 키 반영
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# CSS 스타일 (가독성 최적화)
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #003366; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .source-text { color: #888; font-size: 13px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 통합 뉴스 모니터링")

# --- 수집 함수 (Naver API 방식: IP 차단 없음) ---
def get_naver_news_api(keywords):
    # API 검색어 조합 (띄어쓰기로 구분하면 관련성 높은 뉴스를 가져옵니다)
    search_query = " ".join(keywords)
    # 최신순(date)으로 30개 수집
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
                # HTML 태그 제거 및 특수문자 치환
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                articles.append({
                    "title": title,
                    "link": item['link'],
                    "source": "Naver News",
                    "type": "Naver"
                })
        else:
            st.error(f"Naver API 연결 실패 (코드: {response.status_code})")
    except Exception as e:
        st.error(f"네이버 수집 중 오류: {e}")
    return articles

# --- 수집 함수 (Google RSS 방식) ---
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
                "type": "Google"
            })
    except:
        return []
    return articles

# --- 메인 UI 실행부 ---
target_keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 최신 뉴스 통합 업데이트"):
    with st.spinner('구글과 네이버의 데이터를 동기화 중입니다...'):
        n_news = get_naver_news_api(target_keywords)
        g_news = get_google_news(target_keywords)
        
        # 중복 제거 및 합치기
        all_news = n_news + g_news
        seen_titles = set()
        final_news = []
        for article in all_news:
            # 제목 앞부분 20자만 비교하여 중복 제거 (뉴스 매체별 제목 미세 차이 방지)
            title_id = article['title'][:20]
            if title_id not in seen_titles:
                final_news.append(article)
                seen_titles.add(title_id)

    if not final_news:
        st.warning("어제와 오늘자로 검색된 뉴스가 없습니다.")
    else:
        st.info(f"수집 결과 - Naver: {len(n_news)}건 / Google: {len(g_news)}건 (중복 제외 총 {len(final_news)}건)")
        for article in final_news:
            badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
            st.markdown(f"""
                <div class="news-card">
                    <span class="{badge_class}">{article['type']}</span>
                    <h4 style="margin: 8px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                    <p class="source-text">출처: {article['source']}</p>
                </div>
            """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
