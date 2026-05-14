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

# API 키 (유지)
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# 세션 상태 초기화
if 'news_list' not in st.session_state:
    st.session_state.news_list = []

# --- [데이터 정의: 티어 및 매퍼] ---
TIER_DATA = {
    1: ["조선일보", "중앙일보", "동아일보", "매일경제", "한국경제", "한겨레", "경향신문", "국민일보", "연합뉴스", "YTN", "SBS", "KBS", "MBC", "JTBC"],
    2: ["문화일보", "한국일보", "서울신문", "세계일보", "머니투데이", "서울경제", "뉴시스", "뉴스1", "파이낸셜뉴스", "조선비즈", "이데일리", "한국경제TV", "아시아경제", "연합뉴스TV", "MBN", "채널A", "EBS"],
    3: ["헤럴드경제", "전자신문", "오마이뉴스", "머니S", "매일신문", "아이뉴스24", "프레시안", "부산일보", "더팩트", "노컷뉴스", "블로터", "미디어오늘", "디지털데일리", "조세일보", "디지털타임스", "SBS Biz", "데일리안", "TV조선", "강원일보", "코리아헤럴드", "쿠키뉴스", "KTV", "IT동아", "한의신문", "민족의학신문", "매일일보", "로리더", "신아일보", "시사IN", "시사저널", "경인일보", "스포츠동아", "스포츠조선", "스포츠서울", "일간스포츠"]
}

TIER_MAPPER = {
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "hani.co.kr": ("한겨레", 1),
    "khan.co.kr": ("경향신문", 1), "kmib.co.kr": ("국민일보", 1), "yna.co.kr": ("연합뉴스", 1),
    "ytn.co.kr": ("YTN", 1), "sbs.co.kr": ("SBS", 1), "kbs.co.kr": ("KBS", 1),
    "imbc.com": ("MBC", 1), "jtbc.co.kr": ("JTBC", 1),
    "munhwa.com": ("문화일보", 2), "newsis.com": ("뉴시스", 2), "news1.kr": ("뉴스1", 2),
    "ohmynews.com": ("오마이뉴스", 3), "kyeongin.com": ("경인일보", 3)
}

CP_CODE_MAPPER = {
    "nws": ("뉴시스", 2), "newsis": ("뉴시스", 2), "news1": ("뉴스1", 2),
    "spo": ("스포츠동아", 3), "chosun_s": ("스포츠조선", 3), "ss": ("스포츠서울", 3),
    "sed": ("서울경제", 2), "mk": ("매일경제", 1), "chosun": ("조선일보", 1),
    "joongang": ("중앙일보", 1), "donga": ("동아일보", 1), "yna": ("연합뉴스", 1),
    "edaily": ("이데일리", 2), "mt": ("머니투데이", 2)
}

BLACKLIST_DOMAINS = [
    "blog.naver.com", "tistory.com", "brunch.co.kr", "egloos.com", 
    "contents.premium.naver.com", "namu.wiki", "youtube.com", 
    "facebook.com", "instagram.com", "k-club.kird.re.kr",
    "news.daum.net", "v.daum.net" # 구글 결과에서 다음 뉴스 제외를 위해 추가
]

# --- [유틸리티 함수] ---
def get_tier_info(url, source_name, title=""):
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        cpcd = params.get('cpcd', [None])[0]
        if cpcd and cpcd in CP_CODE_MAPPER: return CP_CODE_MAPPER[cpcd]

        title_source = title.split(" - ")[-1].strip() if " - " in title else ""
        target_name = str(source_name).split(' - ')[0].strip()
        search_target = f"{target_name} {title_source}".strip()

        for tier, names in TIER_DATA.items():
            for name in names:
                if name in search_target: return name, tier
        
        domain = parsed.netloc.replace("www.", "").replace("m.", "")
        parts = domain.split('.')
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in TIER_MAPPER: return TIER_MAPPER[sub]
            
        final_name = title_source if title_source and title_source != "네이트" else (target_name if target_name else domain)
        return final_name, 4
    except: return "출처 확인 불가", 4

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
        temp = []
        
        # 1. 네이버 수집
        n_url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keywords)}&display=100&sort=date"
        n_res = requests.get(n_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}, timeout=15).json()
        if 'items' in n_res:
            for item in n_res['items']:
                if any(b in item['link'] for b in BLACKLIST_DOMAINS): continue
                t_clean = item['title'].replace("<b>","").replace("</b>","")
                name, tier = get_tier_info(item['originallink'], "", t_clean)
                temp.append({"title": t_clean, "link": item['link'], "source": name, "date": item['pubDate'], "type": "Naver", "tier": tier})

        # 2. 다음 수집 (RSS)
        d_q = "경희대학교" # 다음은 단순 키워드로 검색
        d_f = feedparser.parse(f"https://search.daum.net/search?w=news&nil_search=btn&DA=STC&enc=utf8&cluster=y&cluster_page=1&q={urllib.parse.quote(d_q)}&sort=recency")
        # 다음 뉴스 RSS는 크롤링 제한이 있을 수 있어 구글/네이버와 병행이 좋습니다.
        # 여기서는 웹 검색결과 RSS 기반 예시를 작성합니다.
        
        # 3. 구글 수집
        start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        # BLACKLIST_DOMAINS에 다음(daum.net)이 포함되어 구글 결과에서 자동 제외됩니다.
        g_q = f"(\"경희대\" OR \"경희대학교\") after:{start} " + " ".join([f"-site:{b}" for b in BLACKLIST_DOMAINS])
        g_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(g_q)}&hl=ko&gl=KR&ceid=KR:ko")
        
        for entry in g_f.entries:
            if not hasattr(entry, 'source') or "Google News" in entry.source.title: s_name = ""
            else: s_name = entry.source.title
            name, tier = get_tier_info(entry.link, s_name, entry.title)
            temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Google", "tier": tier})

        # 다음(Daum) 검색 결과 보완 (구글 검색에 포함되지 않은 실시간성 다음 링크 수집 시 유용)
        # 단, Daum 전용 탭 구분을 위해 검색 필터링 강화
        daum_search_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote('경희대 site:daum.net')}?hl=ko&gl=KR&ceid=KR:ko")
        for entry in daum_search_f.entries:
            name, tier = get_tier_info(entry.link, "다음뉴스", entry.title)
            temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Daum", "tier": tier})

        seen, final = set(), []
        for c in temp:
            clean_t = re.sub(r'[^가-힣0-9a-zA-Z]', '', c['title'])[:15]
            if clean_t not in seen:
                final.append(c)
                seen.add(clean_t)
        
        final.sort(key=lambda x: (x['tier'], -parse_date(x['date']).timestamp()))
        return final
    except Exception as e:
        st.error(f"수집 오류: {e}")
        return []

# --- [UI 메인 실행] ---
try:
    st.title("경희대학교 및 의료기관 뉴스 클리핑")

    st.markdown("""
        <style>
        .news-card { background-color: white; padding: 15px; border-radius: 0 0 10px 10px; border-left: 6px solid #bdc3c7; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); }
        .source-ribbon { height: 5px; border-radius: 10px 10px 0 0; margin-bottom: -5px; }
        .naver-ribbon { background-color: #03cf5d; }
        .google-ribbon { background-color: #4285f4; }
        .daum-ribbon { background-color: #fae100; }
        .tier-1 { border-left-color: #d32f2f !important; }
        .tier-2 { border-left-color: #f39c12 !important; }
        .tier-3 { border-left-color: #3498db !important; }
        .badge { padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; display: inline-block; margin-bottom: 8px; }
        .naver-badge { background-color: #03cf5d; }
        .google-badge { background-color: #4285f4; }
        .daum-badge { background-color: #ffbb00; color: #3c1e1e; }
        .press-label { color: #d32f2f; font-weight: bold; font-size: 15px; }
        </style>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 컨트롤 타워")
        days = st.slider("조회 기간 (일)", 1, 7, 3)
        if st.button("🔄 실시간 데이터 업데이트", use_container_width=True):
            st.session_state.news_list = fetch_news(days)
        st.caption("※ 유튜브, SNS, 나무위키, 블로그, K-Club 제외")
        
        selected_to_export = []
        if st.session_state.news_list:
            unique_links = set()
            for key, value in st.session_state.items():
                if key.startswith("chk_") and value:
                    parts = key.split('_')
                    t_type, idx = parts[1], int(parts[2])
                    
                    if t_type == "all": target = st.session_state.news_list
                    elif t_type == "naver": target = [n for n in st.session_state.news_list if n['type'] == "Naver"]
                    elif t_type == "google": target = [n for n in st.session_state.news_list if n['type'] == "Google"]
                    elif t_type == "daum": target = [n for n in st.session_state.news_list if n['type'] == "Daum"]
                    else: target = []

                    if idx < len(target):
                        item = target[idx]
                        if item['link'] not in unique_links:
                            selected_to_export.append({"매체명": item['source'], "기사 제목": item['title'], "저자(교수)": extract_professor(item['title']), "URL": item['link']})
                            unique_links.add(item['link'])

        if selected_to_export:
            st.divider()
            st.subheader(f"📥 {len(selected_to_export)}개 선택됨")
            df_ex = pd.DataFrame(selected_to_export)
            out = BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as writer:
                df_ex.to_excel(writer, index=False)
            st.download_button(label="엑셀 파일 다운로드", data=out.getvalue(), file_name=f"KHU_News_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    if not st.session_state.news_list:
        st.info("왼쪽 사이드바의 [업데이트] 버튼을 눌러주세요.")
    else:
        n_list = [n for n in st.session_state.news_list if n['type'] == "Naver"]
        g_list = [n for n in st.session_state.news_list if n['type'] == "Google"]
        d_list = [n for n in st.session_state.news_list if n['type'] == "Daum"]
        
        tab_all, tab_naver, tab_daum, tab_google = st.tabs([
            f"📋 전체 ({len(st.session_state.news_list)})", 
            f"🟢 네이버 ({len(n_list)})", 
            f"🟡 다음 ({len(d_list)})",
            f"🔵 구글 ({len(g_list)})"
        ])
        
        def display_tab(news_data, tab_key):
            if not news_data:
                st.write("수집된 뉴스가 없습니다.")
                return
            for i, art in enumerate(news_data):
                col_check, col_card = st.columns([0.04, 0.96])
                with col_check: st.checkbox("", key=f"chk_{tab_key}_{i}")
                with col_card:
                    rib = "naver-ribbon" if art['type'] == "Naver" else ("google-ribbon" if art['type'] == "Google" else "daum-ribbon")
                    bdg = "naver-badge" if art['type'] == "Naver" else ("google-badge" if art['type'] == "Google" else "daum-badge")
                    t_cl = f"tier-{art['tier']}" if art['tier'] < 4 else ""
                    st.markdown(f"""
                        <div class="source-ribbon {rib}"></div>
                        <div class="news-card {t_cl}">
                            <div class="badge {bdg}">{art['type']} | Tier {art['tier']}</div>
                            <h4 style="margin:5px 0;"><a href="{art['link']}" target="_blank" style="text-decoration:none; color:#1a1a1a;">{art['title']}</a></h4>
                            <div style="font-size:13px; color:#666;"><span class="press-label">{art['source']}</span> | {parse_date(art['date']).strftime('%Y-%m-%d %H:%M')}</div>
                        </div>
                    """, unsafe_allow_html=True)

        with tab_all: display_tab(st.session_state.news_list, "all")
        with tab_naver: display_tab(n_list, "naver")
        with tab_daum: display_tab(d_list, "daum")
        with tab_google: display_tab(g_list, "google")

    st.divider()
    st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")

except Exception as main_e:
    st.error("앱 실행 중 오류 발생")
    st.code(traceback.format_exc())
