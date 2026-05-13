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

TIER_MAPPER = {
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "hani.co.kr": ("한겨레", 1),
    "khan.co.kr": ("경향신문", 1), "kmib.co.kr": ("국민일보", 1), "yna.co.kr": ("연합뉴스", 1),
    "ytn.co.kr": ("YTN", 1), "sbs.co.kr": ("SBS", 1), "kbs.co.kr": ("KBS", 1),
    "imbc.com": ("MBC", 1), "jtbc.co.kr": ("JTBC", 1),
    "hankookilbo.com": ("한국일보", 2), "newsis.com": ("뉴시스", 2), "news1.kr": ("뉴스1", 2),
    "edaily.co.kr": ("이데일리", 2), "mt.co.kr": ("머니투데이", 2), "sedaily.com": ("서울경제", 2),
    "akomnews.com": ("한의신문", 3), "mjmedi.com": ("민족의학신문", 3)
}

def get_tier_info(url, source_name):
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").replace("m.", "")
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        parts = domain.split('.')
        for i in range(len(parts)):
            sub_domain = ".".join(parts[i:])
            if sub_domain in TIER_MAPPER:
                return TIER_MAPPER[sub_domain][0], TIER_MAPPER[sub_domain][1]
        if "news.google.com" in domain: return source_name, 4
        return domain, 4
    except: return source_name, 4

def parse_to_datetime(date_str):
    formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=None)
        except: continue
    return datetime.now().replace(tzinfo=None)

# --- 사이드바 구성 ---
with st.sidebar:
    st.header("📊 매체 등급 정보")
    for tier in [1, 2, 3]:
        with st.expander(f"Tier {tier} 매체 리스트", expanded=True):
            st.write(", ".join(TIER_DATA[tier]))
    st.markdown("---")
    days_to_search = st.slider("조회 기간 설정 (일)", 1, 7, 3)
    st.caption("※ 유튜브, SNS, 나무위키, 구글 기사모음 제외")

# CSS 스타일
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #bdc3c7; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tier-1 { border-left: 10px solid #d32f2f; background-color: #fff9f9; }
    .tier-2 { border-left: 10px solid #f39c12; }
    .tier-3 { border-left: 10px solid #3498db; }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .press-label { color: #d32f2f; font-weight: bold; }
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
                if "namu.wiki" in item['link']: continue
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", "&")
                name, tier = get_tier_info(item['originallink'], "Naver News")
                articles.append({
                    "title": title, "link": item['link'], "source": name,
                    "raw_date": item['pubDate'], "type": "Naver", "tier": tier
                })
    except: pass
    return articles

def get_google_news(keywords, days):
    start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    query = f"({' OR '.join([f'\"{k}\"' for k in keywords])}) after:{start_date} -site:youtube.com -site:facebook.com -site:instagram.com -site:namu.wiki"
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            # [수정] 기사 리스트(Google News 자체 링크) 필터링 로직
            # 출처가 Google News이거나 제목에 '전체 뉴스 보기'가 포함된 경우 제외
            if "Google News" in entry.source.title or "전체 뉴스 보기" in entry.title:
                continue
            
            name, tier = get_tier_info(entry.link, entry.source.title)
            articles.append({
                "title": entry.title, "link": entry.link, "source": name,
                "raw_date": entry.published, "type": "Google", "tier": tier
            })
    except: pass
    return articles

# --- 메인 실행부 ---
keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 실시간 데이터 동기화"):
    with st.spinner('뉴스를 분석 중입니다...'):
        all_news = get_naver_news_api(keywords, days_to_search) + get_google_news(keywords, days_to_search)
        
        if not all_news:
            st.warning("수집된 뉴스가 없습니다.")
        else:
            seen = set()
            final_list = []
            for n in all_news:
                title_key = n['title'][:20]
                if title_key not in seen:
                    final_list.append(n)
                    seen.add(title_key)
            
            final_list.sort(key=lambda x: (x['tier'], -parse_to_datetime(x['raw_date']).timestamp()))

            st.success(f"총 {len(final_list)}건의 소식을 찾았습니다. (조회 기간: 최근 {days_to_search}일)")
            
            for article in final_list:
                badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
                tier_class = f"tier-{article['tier']}" if article['tier'] < 4 else ""
                display_date = parse_to_datetime(article['raw_date']).strftime('%Y-%m-%d %H:%M')
                
                st.markdown(f"""
                    <div class="news-card {tier_class}">
                        <span class="{badge_class}">{article['type']}</span>
                        <span style="font-size:12px; color:#666; font-weight:bold;"> | Tier {article['tier']}</span>
                        <h4 style="margin: 8px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                        <div style="font-size: 13px; color: #666;">
                            <span class="press-label">{article['source']}</span> | {display_date}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
