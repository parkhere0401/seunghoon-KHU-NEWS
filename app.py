import streamlit as st
import feedparser
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
import urllib.parse
import re
import traceback

# 1. 페이지 설정
st.set_page_config(page_title="경희대학교 뉴스 클리핑", page_icon="🏫", layout="wide")

# API 키
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

if 'news_list' not in st.session_state:
    st.session_state.news_list = []

# --- [데이터 정의] ---
TIER_DATA = {
    1: ["조선일보", "중앙일보", "동아일보", "매일경제", "한국경제", "한겨레", "경향신문", "국민일보", "연합뉴스", "YTN", "SBS", "KBS", "MBC", "JTBC"],
    2: ["문화일보", "한국일보", "서울신문", "세계일보", "머니투데이", "서울경제", "뉴시스", "뉴스1", "파이낸셜뉴스", "조선비즈", "이데일리", "한국경제TV", "아시아경제", "연합뉴스TV", "MBN", "채널A", "EBS"],
    3: ["헤럴드경제", "전자신문", "오마이뉴스", "머니S", "매일신문", "아이뉴스24", "프레시안", "부산일보", "더팩트", "노컷뉴스", "블로터", "미디어오늘", "디지털데일리", "조세일보", "디지털타임스", "SBS Biz", "데일리안", "TV조선", "강원일보", "코리아헤럴드", "쿠키뉴스", "KTV", "IT동아", "한의신문", "민족의학신문", "매일일보", "로리더", "신아일보", "시사IN", "시사저널", "경인일보", "스포츠동아", "스포츠조선", "스포츠서울", "일간스포츠"]
}

# 도메인 매핑 (네이버 원문 링크용)
TIER_MAPPER = {
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "yna.co.kr": ("연합뉴스", 1)
}

BLACKLIST_DOMAINS = ["blog.naver.com", "tistory.com", "brunch.co.kr", "egloos.com", "namu.wiki", "youtube.com", "k-club.kird.re.kr"]

# --- [유틸리티 함수] ---

def get_tier_info(url, source_name, title=""):
    """
    다음/구글 등에서 언론사명을 찾고 티어를 결정하는 통합 로직
    """
    # 1. 전처리: 소스네임이 URL 형태면 무시
    s_name = str(source_name)
    if "daum.net" in s_name or "google" in s_name.lower():
        s_name = ""

    # 2. 제목 끝의 언론사명 추출 (구글/다음 RSS 공통 패턴)
    title_press = ""
    if " - " in title:
        title_press = title.split(" - ")[-1].strip()

    # 3. 텍스트 매칭 (가장 중요): 제목 꼬리표 혹은 소스네임에서 티어 리스트 검색
    search_target = f"{s_name} {title_press}".strip()
    
    for tier, names in TIER_DATA.items():
        for name in names:
            if name in search_target:
                return name, tier

    # 4. 도메인 기반 (네이버 원문 링크 대응)
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace("m.", "")
    for sub, info in TIER_MAPPER.items():
        if sub in domain: return info

    # 5. 매칭 실패 시
    final_name = title_press if title_press else (s_name if s_name else "기타매체")
    return final_name, 4

def parse_date(date_str):
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except: continue
    return datetime.now()

def extract_professor(title):
    match = re.search(r'([가-힣]{2,4}\s?교수)', title)
    return match.group(1) if match else "-"

def fetch_news(days):
    try:
        keywords = "경희대 | 경희대학교 | 경희의료원 | 강동경희대학교병원"
        temp = []
        start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 1. 네이버 API
        n_url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keywords)}&display=100&sort=date"
        n_res = requests.get(n_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}, timeout=15).json()
        if 'items' in n_res:
            for item in n_res['items']:
                if any(b in item['link'] for b in BLACKLIST_DOMAINS): continue
                t_clean = item['title'].replace("<b>","").replace("</b>","")
                name, tier = get_tier_info(item['originallink'], "", t_clean)
                temp.append({"title": t_clean, "link": item['link'], "source": name, "date": item['pubDate'], "type": "Naver", "tier": tier})

        # 2. 구글 RSS (다음 제외)
        g_q = f"({keywords}) after:{start_date} -site:daum.net " + " ".join([f"-site:{b}" for b in BLACKLIST_DOMAINS])
        g_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(g_q)}&hl=ko&gl=KR&ceid=KR:ko")
        for entry in g_f.entries:
            s_name = entry.source.title if hasattr(entry, 'source') else ""
            name, tier = get_tier_info(entry.link, s_name, entry.title)
            temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Google", "tier": tier})

        # 3. 다음 섹션 (실제로 구글 RSS의 site:daum.net 기능을 이용해 수집)
        d_q = f"({keywords}) site:daum.net after:{start_date}"
        d_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(d_q)}&hl=ko&gl=KR&ceid=KR:ko")
        for entry in d_f.entries:
            s_name = entry.source.title if hasattr(entry, 'source') else ""
            name, tier = get_tier_info(entry.link, s_name, entry.title)
            # 제목에서 언론사 꼬리표 제거
            clean_title = entry.title.split(" - ")[0] if " - " in entry.title else entry.title
            temp.append({"title": clean_title, "link": entry.link, "source": name, "date": entry.published, "type": "Daum", "tier": tier})

        # 중복 제거
        seen, final = set(), []
        for c in temp:
            normalized_t = re.sub(r'[^가-힣0-9a-zA-Z]', '', c['title'])[:15]
            if normalized_t not in seen:
                final.append(c)
                seen.add(normalized_t)
        
        final.sort(key=lambda x: (x['tier'], -parse_date(x['date']).timestamp()))
        return final
    except Exception as e:
        st.error(f"수집 중 오류: {e}")
        return []

# --- [UI 부분] ---
st.title("🏫 경희대학교 뉴스 클리핑 시스템")

with st.sidebar:
    st.header("⚙️ 설정")
    days = st.slider("조회 기간", 1, 7, 3)
    if st.button("🔄 실시간 업데이트", use_container_width=True):
        st.session_state.news_list = fetch_news(days)
    
    st.divider()
    st.header("📊 매체 등급")
    for t in [1, 2, 3]:
        with st.expander(f"Tier {t} 매체"):
            st.write(", ".join(TIER_DATA[t]))

if st.session_state.news_list:
    n_list = [n for n in st.session_state.news_list if n['type'] == "Naver"]
    d_list = [n for n in st.session_state.news_list if n['type'] == "Daum"]
    g_list = [n for n in st.session_state.news_list if n['type'] == "Google"]
    
    tabs = st.tabs([f"전체({len(st.session_state.news_list)})", f"네이버({len(n_list)})", f"다음({len(d_list)})", f"기타/구글({len(g_list)})"])
    
    # CSS 스타일 적용
    st.markdown("""
        <style>
        .card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #ccc; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .t1 { border-left-color: #e74c3c; }
        .t2 { border-left-color: #f1c40f; }
        .t3 { border-left-color: #3498db; }
        .press { color: #e74c3c; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    def render_news(data, key):
        for i, item in enumerate(data):
            t_class = f"t{item['tier']}" if item['tier'] <= 3 else ""
            col1, col2 = st.columns([0.05, 0.95])
            with col1: st.checkbox("", key=f"chk_{key}_{i}")
            with col2:
                st.markdown(f"""
                <div class="card {t_class}">
                    <small style="color:gray;">{item['type']} | Tier {item['tier']}</small>
                    <h4 style="margin:5px 0;"><a href="{item['link']}" target="_blank" style="text-decoration:none; color:black;">{item['title']}</a></h4>
                    <small><span class="press">{item['source']}</span> | {parse_date(item['date']).strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """, unsafe_allow_html=True)

    for i, tab in enumerate(tabs):
        with tab:
            target = [st.session_state.news_list, n_list, d_list, g_list][i]
            render_news(target, ["all", "naver", "daum", "google"][i])
else:
    st.info("사이드바의 업데이트 버튼을 눌러주세요.")
