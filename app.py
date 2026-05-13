import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import urllib.parse

# 1. 페이지 환경 설정
st.set_page_config(page_title="KHU News Dashboard", page_icon="🏫", layout="wide")

# 스타일 커스텀 (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #003366; color: white; }
    .news-card { background-color: white; padding: 20px; border-radius: 15px; border-left: 5px solid #003366; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 통합 뉴스 모니터링")

# --- 수집 함수 정의 ---

def get_naver_news(keywords):
    search_keyword = " | ".join(keywords)
    start_date = (date.today() - timedelta(days=1)).strftime('%Y.%m.%d')
    end_date = date.today().strftime('%Y.%m.%d')
    
    url = f"https://search.naver.com/search.naver?where=news&query={urllib.parse.quote(search_keyword)}&sm=tab_opt&sort=1&pd=3&ds={start_date}&de={end_date}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Referer": "https://www.naver.com"
    }
    
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select("ul.list_news > li")
        
        for item in items:
            title_el = item.select_one("a.news_tit")
            press_el = item.select_one("a.info.press")
            if title_el and press_el:
                articles.append({
                    "title": title_el.text,
                    "link": title_el['href'],
                    "source": press_el.text.replace("언론사 선정", "").strip(),
                    "type": "Naver"
                })
    except:
        return []
    return articles

def get_google_news(keywords):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    keyword_query = " OR ".join([f'"{k}"' for k in keywords])
    query = f"({keyword_query}) after:{yesterday} before:{tomorrow}"
    
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

# --- 메인 UI 로직 ---

keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 뉴스 새로고침"):
    with st.spinner('수집 중...'):
        n_news = get_naver_news(keywords)
        g_news = get_google_news(keywords)
        
        all_news = n_news + g_news
        seen_titles = set()
        final_news = []
        for article in all_news:
            if article['title'] not in seen_titles:
                final_news.append(article)
                seen_titles.add(article['title'])

    if not final_news:
        st.warning("검색된 뉴스가 없습니다.")
    else:
        st.info(f"Naver: {len(n_news)} / Google: {len(g_news)}")
        
        for article in final_news:
            badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
            badge_text = article['type']
            
            st.markdown(f"""
                <div class="news-card">
                    <span class="{badge_class}">{badge_text}</span>
                    <h4 style="margin: 10px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                    <p style="color: #666; font-size: 14px; margin-bottom: 0;">출처: {article['source']}</p>
                </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
