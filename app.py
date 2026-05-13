import streamlit as st
import feedparser
import requests
from datetime import datetime, date, timedelta
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="KHU News Dashboard", page_icon="🏫", layout="wide")

# API 키
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# 주요 언론사 매핑 사전
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
    """타임존 갈등으로 인한 TypeError 방지를 위해 모든 날짜를 Naive 상태로 변환"""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # Naver API / Google RSS 표준
        '%a, %d %b %Y %H:%M:%S GMT', # Google RSS 일부
        '%Y-%m-%d %H:%M:%S'
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # [핵심 수정] 타임존 정보를 강제로 제거하여 비교 에러 방지
            return dt.replace(tzinfo=None)
        except:
            continue
    return datetime.now().replace(tzinfo=None) # 실패 시 현재 시간(Naive) 반환

# CSS 스타일
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #003366; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .major-card { border-left: 8px solid #d32f2f; background-color: #fff9f9; }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .meta-info { color: #666; font-size: 13px; margin-top: 5px; }
    .press-name { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 뉴스 통합 브리핑")

# --- 수집 함수 ---
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
                    "raw_date": item['pubDate'], "type": "Naver",
                    "is_major": press in PRESS_MAPPER.values()
                })
    except: return []
    return articles

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
                "title": entry.title, "link": entry.link, "source": entry.source.title,
                "raw_date": entry.published, "type": "Google",
                "is_major": entry.source.title in PRESS_MAPPER.values()
            })
    except: return []
    return articles

# --- UI 실행 ---
target_keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 최신 뉴스 통합 업데이트"):
    with st.spinner('데이터를 분석 중입니다...'):
        all_news = get_naver_news_api(target_keywords) + get_google_news(target_keywords)
        
        if not all_news:
            st.warning("검색된 뉴스가 없습니다.")
        else:
            # Major 기사와 일반 기사 분리 후 각각 최신순 정렬
            major_news = sorted([n for n in all_news if n['is_major']], 
                                key=lambda x: parse_to_datetime(x['raw_date']), reverse=True)
            other_news = sorted([n for n in all_news if not n['is_major']], 
                                key=lambda x: parse_to_datetime(x['raw_date']), reverse=True)
            final_list = major_news + other_news

            st.success(f"주요 언론사({len(major_news)}건) + 기타 매체({len(other_news)}건) 총 {len(final_list)}건")
            
            for article in final_list:
                badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
                major_class = "major-card" if article['is_major'] else ""
                display_date = parse_to_datetime(article['raw_date']).strftime('%Y-%m-%d %H:%M')
                
                st.markdown(f"""
                    <div class="news-card {major_class}">
                        <span class="{badge_class}">{article['type']}</span>
                        <h4 style="margin: 8px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                        <div class="meta-info">
                            <span class="press-name">출처: {article['source']}</span> | 
                            <span>게재일: {display_date}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
