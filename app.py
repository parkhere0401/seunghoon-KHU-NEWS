import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import urllib.parse

st.set_page_config(page_title="KHU Integrated News", page_icon="🏫", layout="wide")
st.title("🏫 경희 가족 통합 뉴스 (Google + Naver)")

# 1. 네이버 뉴스 수집 함수
def get_naver_news(keywords):
    query = " OR ".join(keywords)
    # 네이버 뉴스 검색 (최신순 sort=1, 24시간 내 pd=4)
    url = f"https://search.naver.com/search.naver?where=news&query={urllib.parse.quote(query)}&sm=tab_opt&sort=1&pd=4"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    for item in soup.select("ul.list_news > li"):
        try:
            title = item.select_one("a.news_tit").text
            link = item.select_one("a.news_tit")['href']
            source = item.select_one("a.info.press").text.replace("언론사 선정", "")
            articles.append({"title": title, "link": link, "source": source, "type": "Naver"})
        except:
            continue
    return articles

# 2. 구글 뉴스 수집 함수
def get_google_news(keywords):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    query = f"({' OR '.join(keywords)}) after:{yesterday} before:{tomorrow}"
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        articles.append({"title": entry.title, "link": entry.link, "source": entry.source.title, "type": "Google"})
    return articles

# UI 부분
keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button('🗞️ 통합 뉴스 새로고침'):
    with st.spinner('구글과 네이버에서 데이터를 가져오는 중...'):
        g_news = get_google_news(keywords)
        n_news = get_naver_news(keywords)
        total_news = n_news + g_news # 네이버 뉴스를 상단에 배치
        
    if not total_news:
        st.warning("어제와 오늘자로 검색된 뉴스가 없습니다.")
    else:
        st.success(f"네이버({len(n_news)}건)와 구글({len(g_news)}건) 소식을 모두 찾았습니다.")
        
        for article in total_news:
            with st.container():
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    badge = "🟢 Naver" if article['type'] == "Naver" else "🔵 Google"
                    st.markdown(f"**{badge}** | [{article['title']}]({article['link']})")
                    st.caption(f"출처: {article['source']}")
                with col2:
                    st.link_button("기사 보기", article['link'])
                st.divider()

st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
