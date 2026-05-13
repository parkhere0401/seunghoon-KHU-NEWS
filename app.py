import streamlit as st
import feedparser
import requests
from datetime import datetime, date, timedelta
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="KHU News Tier Dashboard", page_icon="🏫", layout="wide")

# API 키 (전달해주신 키 적용)
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# --- [이미지 기반 티어 정보 및 언론사 매핑] ---
# 도메인을 키로, (언론사명, 티어)를 저장합니다.
TIER_MAPPER = {
    # 티어 1
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "hani.co.kr": ("한겨레", 1),
    "khan.co.kr": ("경향신문", 1), "kmib.co.kr": ("국민일보", 1), "yna.co.kr": ("연합뉴스", 1),
    "ytn.co.kr": ("YTN", 1), "sbs.co.kr": ("SBS", 1), "kbs.co.kr": ("KBS", 1),
    "imbc.com": ("MBC", 1), "jtbc.co.kr": ("JTBC", 1),
    
    # 티어 2
    "hankookilbo.com": ("한국일보", 2), "munhwa.com": ("문화일보", 2), "seoul.co.kr": ("서울신문", 2),
    "segye.com": ("세계일보", 2), "mt.co.kr": ("머니투데이", 2), "sedaily.com": ("서울경제", 2),
    "newsis.com": ("뉴시스", 2), "news1.kr": ("뉴스1", 2), "fnnews.com": ("파이낸셜뉴스", 2),
    "biz.chosun.com": ("조선비즈", 2), "edaily.co.kr": ("이데일리", 2), "wowtv.co.kr": ("한국경제TV", 2),
    "asiae.co.kr": ("아시아경제", 2), "yonhapnewstv.co.kr": ("연합뉴스TV", 2), "mbn.co.kr": ("MBN", 2),
    "ichannela.com": ("채널A", 2), "ebs.co.kr": ("EBS", 2),

    # 티어 3
    "heraldbiz.com": ("헤럴드경제", 3), "etnews.com": ("전자신문", 3), "ohmynews.com": ("오마이뉴스", 3),
    "moneys.co.kr": ("머니S", 3), "imaeil.com": ("매일신문", 3), "inews24.com": ("아이뉴스24", 3),
    "pressian.com": ("프레시안", 3), "busan.com": ("부산일보", 3), "tf.co.kr": ("더팩트", 3),
    "nocutnews.co.kr": ("노컷뉴스", 3), "bloter.net": ("블로터", 3), "mediatoday.co.kr": ("미디어오늘", 3),
    "ddaily.co.kr": ("디지털데일리", 3), "joseilbo.com": ("조세일보", 3), "digitaltimes.co.kr": ("디지털타임스", 3),
    "sbsbiz.oc.kr": ("SBS CNBC", 3), "dailian.co.kr": ("데일리안", 3), "tvchosun.com": ("TV조선", 3),
    "kwnews.co.kr": ("강원일보", 3), "koreaherald.com": ("코리아헤럴드", 3), "kukinews.com": ("쿠키뉴스", 3),
    "ktv.go.kr": ("KTV", 3), "itdonga.com": ("IT동아", 3), "akomnews.com": ("한의신문", 3), "mjmedi.com": ("민족의학신문", 3),
    "m-i.kr": ("매일일보", 3), "lawleader.co.kr": ("로리더", 3), "shinailbo.co.kr": ("신아일보", 3), "sisain.co.kr": ("시사IN", 3)
}

def extract_press_info(url, fallback_name):
    """URL에서 도메인을 추출하여 언론사명과 티어를 결정합니다."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").replace("m.", "")
        
        # 1. 티어 매퍼에서 도메인 검색
        if domain in TIER_MAPPER:
            return TIER_MAPPER[domain][0], TIER_MAPPER[domain][1]
        
        # 2. 서브도메인 처리 (예: news.naver.com -> naver.com)
        base_domain = ".".join(domain.split(".")[-2:])
        if base_domain in TIER_MAPPER:
            return TIER_MAPPER[base_domain][0], TIER_MAPPER[base_domain][1]
            
        # 3. 매핑되지 않은 경우 도메인 이름을 출처로 사용 (Naver News 방지)
        return domain, 4
    except:
        return fallback_name, 4

def parse_to_datetime(date_str):
    formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except: continue
    return datetime.now().replace(tzinfo=None)

# --- 사이드바 구성 ---
with st.sidebar:
    st.header("📊 미디어 분류 시스템")
    st.markdown("---")
    st.success("**Tier 1**: 중앙 일간지 및 지상파 방송사")
    st.warning("**Tier 2**: 경제지 및 뉴스통신사")
    st.info("**Tier 3**: IT/전문지 및 지역 일간지")
    st.write("**Tier 4**: 기타 온라인 매체")
    st.markdown("---")
    st.caption("※ 유튜브, SNS 매체는 Tier 4로 자동 분류됩니다.")

# CSS 스타일
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 18px; border-radius: 12px; border-left: 5px solid #bdc3c7; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
    .tier-1 { border-left: 10px solid #d32f2f; background-color: #fff9f9; }
    .tier-2 { border-left: 10px solid #f39c12; }
    .tier-3 { border-left: 10px solid #3498db; }
    .naver-badge { background-color: #03cf5d; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .google-badge { background-color: #4285f4; color: white; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; }
    .press-name { color: #d32f2f; font-weight: bold; font-size: 14px; }
    .date-text { color: #888; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 경희 가족 지능형 뉴스 대시보드")

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
                # [수정] originallink를 분석하여 실제 언론사명 추출
                press, tier = extract_press_info(item['originallink'], "네이버 뉴스")
                articles.append({
                    "title": title, "link": item['link'], "source": press,
                    "raw_date": item['pubDate'], "type": "Naver", "tier": tier
                })
    except: return []
    return articles

def get_google_news(keywords):
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    # SNS 매체 제외 쿼리
    query = f"({' OR '.join([f'\"{k}\"' for k in keywords])}) after:{yesterday} before:{tomorrow} -site:youtube.com -site:facebook.com -site:instagram.com"
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    articles = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            press, tier = extract_press_info(entry.link, entry.source.title)
            articles.append({
                "title": entry.title, "link": entry.link, "source": press,
                "raw_date": entry.published, "type": "Google", "tier": tier
            })
    except: return []
    return articles

# --- 실행부 ---
target_keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]

if st.button("🔄 실시간 뉴스 데이터 동기화"):
    with st.spinner('티어별 기사를 분석 중입니다...'):
        all_news = get_naver_news_api(target_keywords) + get_google_news(target_keywords)
        
        if not all_news:
            st.warning("어제와 오늘자로 검색된 뉴스가 없습니다.")
        else:
            # 1. 티어순(낮은 숫자 우선) 2. 날짜순(최신순) 정렬
            all_news.sort(key=lambda x: (x['tier'], -parse_to_datetime(x['raw_date']).timestamp()))

            st.success(f"총 {len(all_news)}건의 소식을 수집했습니다.")
            
            for article in all_news:
                badge_class = "naver-badge" if article['type'] == "Naver" else "google-badge"
                tier_class = f"tier-{article['tier']}" if article['tier'] < 4 else ""
                display_date = parse_to_datetime(article['raw_date']).strftime('%Y-%m-%d %H:%M')
                
                st.markdown(f"""
                    <div class="news-card {tier_class}">
                        <span class="{badge_class}">{article['type']}</span>
                        <span style="font-size:12px; color:#666; font-weight:bold;"> | Tier {article['tier']}</span>
                        <h4 style="margin: 10px 0;"><a href="{article['link']}" target="_blank" style="text-decoration: none; color: #1a1a1a;">{article['title']}</a></h4>
                        <div class="meta-info">
                            <span class="press-name">{article['source']}</span> | 
                            <span class="date-text">{display_date}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
