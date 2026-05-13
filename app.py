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
st.set_page_config(page_title="경희대학교 및 의료기관 뉴스 클리핑", page_icon="🏫", layout="wide")

# API 키
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# 세션 상태 초기화
if 'news_list' not in st.session_state:
    st.session_state.news_list = []

# --- [데이터 정의: 티어 및 매퍼] ---
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
}

BLACKLIST_DOMAINS = ["blog.naver.com", "tistory.com", "brunch.co.kr", "namu.wiki", "contents.premium.naver.com", "youtube.com", "facebook.com", "instagram.com"]

# --- [유틸리티 함수] ---
def get_tier_info(url, source_name):
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "").replace("m.", "")
        if "nate.com" in domain:
            cpcd = urllib.parse.parse_qs(parsed.query).get('cpcd', [''])[0]
            codes = {"sed": ("서울경제", 2), "chosun": ("조선일보", 1), "joongang": ("중앙일보", 1)}
            if cpcd in codes: return codes[cpcd]
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        parts = domain.split('.')
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in TIER_MAPPER: return TIER_MAPPER[sub]
        return domain, 4
    except: return str(source_name), 4

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
        keywords = "경희대 | 경희대학교 | 경희의료원 | 강동경희대학교병원 | 강동경희"
        n_url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keywords)}&display=100&sort=date"
        n_res = requests.get(n_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}, timeout=15).json()
        start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        g_q = f"(\"경희대\" OR \"경희대학교\") after:{start} " + " ".join([f"-site:{b}" for b in BLACKLIST_DOMAINS])
        g_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(g_q)}&hl=ko&gl=KR&ceid=KR:ko")

        temp = []
        if 'items' in n_res:
            for item in n_res['items']:
                if any(b in item['link'] for b in BLACKLIST_DOMAINS): continue
                name, tier = get_tier_info(item['originallink'], "Naver News")
                temp.append({"title": item['title'].replace("<b>","").replace("</b>",""), "link": item['link'], "source": name, "date": item['pubDate'], "type": "Naver", "tier": tier})
        for entry in g_f.entries:
            if not hasattr(entry, 'source') or "Google News" in entry.source.title: continue
            name, tier = get_tier_info(entry.link, entry.source.title)
            temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Google", "tier": tier})

        seen, final = set(), []
        for c in temp:
            if c['title'][:20] not in seen:
                final.append(c)
                seen.add(c['title'][:20])
        final.sort(key=lambda x: (x['tier'], -parse_date(x['date']).timestamp()))
        return final
    except Exception as e:
        st.error(f"수집 오류: {e}")
        return []

# --- [UI 시작] ---
try:
    st.title("경희대학교 및 의료기관 뉴스 클리핑")

    st.markdown("""
        <style>
        .news-card { background-color: white; padding: 15px; border-radius: 0 0 10px 10px; border-left: 6px solid #bdc3c7; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); }
        .source-ribbon { height: 5px; border-radius: 10px 10px 0 0; margin-bottom: -5px; }
        .naver-ribbon { background-color: #03cf5d; }
        .google-ribbon { background-color: #4285f4; }
        .tier-1 { border-left-color: #d32f2f !important; }
        .tier-2 { border-left-color: #f39c12 !important; }
        .tier-3 { border-left-color: #3498db !important; }
        .badge { padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; display: inline-block; margin-bottom: 8px; }
        .naver-badge { background-color: #03cf5d; }
        .google-badge { background-color: #4285f4; }
        .press-label { color: #d32f2f; font-weight: bold; font-size: 15px; }
        </style>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 컨트롤 타워")
        days = st.slider("조회 기간 (일)", 1, 7, 3)
        if st.button("🔄 실시간 데이터 업데이트", use_container_width=True):
            st.session_state.news_list = fetch_news(days)
        st.caption("※ 유튜브, SNS, 나무위키, 블로그 제외")
        
        # 엑셀 다운로드 버튼 (기사 선택 시 동적 표시)
        selected_to_export = []
        if st.session_state.news_list:
            unique_links = set()
            for key, value in st.session_state.items():
                if key.startswith("chk_") and value:
                    parts = key.split('_')
                    tab_type = parts[1]
                    idx = int(parts[2])
                    
                    target_list = st.session_state.news_list
                    if tab_type == "naver": target_list = [n for n in st.session_state.news_list if n['type'] == "Naver"]
                    elif tab_type == "google": target_list = [n for n in st.session_state.news_list if n['type'] == "Google"]
                    
                    if idx < len(target_list):
                        item = target_list[idx]
                        if item['link'] not in unique_links:
                            selected_to_export.append({"매체명": item['source'], "기사 제목": item['title'], "저자(교수)": extract_professor(item['title']), "URL": item['link']})
                            unique_links.add(item['link'])

        if selected_to_export:
            st.divider()
            st.subheader(f"📥 {len(selected_to_export)}개 선택됨")
            df = pd.DataFrame(selected_to_export)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button(label="엑셀 파일 다운로드", data=output.getvalue(), file_name=f"KHU_News_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        st.divider()
        st.header("📊 매체 등급 정보")
        for tier in [1, 2, 3]:
            with st.expander(f"Tier {tier} 리스트", expanded=False):
                st.write(", ".join(TIER_DATA[tier]))

    # 메인 뉴스 리스트 출력
    if not st.session_state.news_list:
        st.info("왼쪽 사이드바의 [업데이트] 버튼을 눌러주세요.")
    else:
        # [업데이트] 탭 타이틀에 기사 수 표시
        naver_list = [n for n in st.session_state.news_list if n['type'] == "Naver"]
        google_list = [n for n in st.session_state.news_list if n['type'] == "Google"]
        
        tab_all, tab_naver, tab_google = st.tabs([
            f"📋 전체 보기 ({len(st.session_state.news_list)})", 
            f"🟢 네이버 뉴스 ({len(naver_list)})", 
            f"🔵 구글 뉴스 ({len(google_list)})"
        ])
        
        def display_news_tab(news_data, tab_key):
            for i, art in enumerate(news_data):
                col_check, col_card = st.columns([0.04, 0.96])
                with col_check:
                    st.checkbox("", key=f"chk_{tab_key}_{i}")
                with col_card:
                    ribbon = "naver-ribbon" if art['type'] == "Naver" else "google-ribbon"
                    badge = "naver-badge" if art['type'] == "Naver" else "google-badge"
                    t_class = f"tier-{art['tier']}" if art['tier'] < 4 else ""
                    st.markdown(f"""
                        <div class="source-ribbon {ribbon}"></div>
                        <div class="news-card {t_class}">
                            <div class="badge {badge}">{art['type']} | Tier {art['tier']}</div>
                            <h4 style="margin:5px 0;"><a href="{art['link']}" target="_blank" style="text-decoration:none; color:#1a1a1a;">{art['title']}</a></h4>
                            <div style="font-size:13px; color:#666;">
                                <span class="press-label">{art['source']}</span> | {parse_date(art['date']).strftime('%Y-%m-%d %H:%M')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

        with tab_all: display_news_tab(st.session_state.news_list, "all")
        with tab_naver: display_news_tab(naver_list, "naver")
        with tab_google: display_news_tab(google_list, "google")

    st.divider()
    st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")

except Exception as main_e:
    st.error("치명적 오류 발생")
    st.code(traceback.format_exc())
