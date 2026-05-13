import streamlit as st
import feedparser
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
import urllib.parse
import re

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="경희대학교 및 의료기관 뉴스 클리핑", page_icon="🏫", layout="wide")

# API 키 (기존 키 유지)
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

# 세션 상태 초기화 (재실행 시 데이터 유지용)
if 'news_list' not in st.session_state:
    st.session_state.news_list = []

# --- [고정 데이터: 티어 및 매퍼] ---
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
}

BLACKLIST_DOMAINS = ["blog.naver.com", "tistory.com", "brunch.co.kr", "namu.wiki", "contents.premium.naver.com", "youtube.com", "facebook.com", "instagram.com"]

# --- [유틸리티 함수] ---
def get_tier_info(url, source_name):
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "").replace("m.", "")
        # 네이트 cpcd 분석
        if "nate.com" in domain:
            cpcd = urllib.parse.parse_qs(parsed.query).get('cpcd', [''])[0]
            codes = {"sed": ("서울경제", 2), "chosun": ("조선일보", 1), "joongang": ("중앙일보", 1)}
            if cpcd in codes: return codes[cpcd]
        # 이름 매칭
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        # 도메인 역추적
        parts = domain.split('.')
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in TIER_MAPPER: return TIER_MAPPER[sub]
        return domain, 4
    except: return source_name, 4

def parse_date(date_str):
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except: continue
    return datetime.now()

def extract_professor(title):
    match = re.search(r'([가-힣]{2,4}\s?교수)', title)
    return match.group(1) if match else "-"

# --- [핵심 수집 함수] ---
def fetch_news(days):
    keywords = "경희대 | 경희대학교 | 경희의료원 | 강동경희대학교병원 | 강동경희"
    # Naver
    n_url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keywords)}&display=100&sort=date"
    n_res = requests.get(n_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}, timeout=10).json()
    
    # Google
    start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    g_q = f"(\"경희대\" OR \"경희대학교\") after:{start} " + " ".join([f"-site:{b}" for b in BLACKLIST_DOMAINS])
    g_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(g_q)}&hl=ko&gl=KR&ceid=KR:ko")

    temp = []
    for item in n_res.get('items', []):
        if any(b in item['link'] for b in BLACKLIST_DOMAINS): continue
        name, tier = get_tier_info(item['originallink'], "Naver News")
        temp.append({"title": item['title'].replace("<b>","").replace("</b>",""), "link": item['link'], "source": name, "date": item['pubDate'], "type": "Naver", "tier": tier})
    
    for entry in g_f.entries:
        if "Google News" in entry.source.title: continue
        name, tier = get_tier_info(entry.link, entry.source.title)
        temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Google", "tier": tier})

    seen, final = set(), []
    for c in temp:
        if c['title'][:20] not in seen:
            final.append(c)
            seen.add(c['title'][:20])
    final.sort(key=lambda x: (x['tier'], -parse_date(x['date']).timestamp()))
    return final

# --- [메인 UI 시작] ---
st.title("경희대학교 및 의료기관 뉴스 클리핑")

with st.sidebar:
    st.header("⚙️ 컨트롤 타워")
    days = st.slider("조회 기간 (일)", 1, 7, 3)
    if st.button("🔄 실시간 데이터 업데이트", use_container_width=True):
        with st.spinner('뉴스를 수집 중입니다...'):
            st.session_state.news_list = fetch_news(days)
            st.success('수집 완료!')
    
    st.divider()
    st.subheader("📊 매체 정보")
    for t in [1, 2, 3]:
        with st.expander(f"Tier {t} 리스트"):
            st.write(", ".join(TIER_DATA[t]))

# CSS
st.markdown("""
    <style>
    .news-card { background-color: white; padding: 12px; border-radius: 8px; border-left: 5px solid #bdc3c7; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .tier-1 { border-left-color: #d32f2f; background-color: #fff9f9; }
    .tier-2 { border-left-color: #f39c12; }
    .tier-3 { border-left-color: #3498db; }
    .press-label { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 기사 출력 및 선택 섹션
if not st.session_state.news_list:
    st.info("왼쪽 사이드바의 [업데이트] 버튼을 눌러 뉴스를 불러와 주세요.")
else:
    selected_indices = []
    st.subheader(f"📅 오늘의 뉴스 ({len(st.session_state.news_list)}건)")
    
    # 엑셀 추출용 리스트
    for i, art in enumerate(st.session_state.news_list):
        col_check, col_card = st.columns([0.05, 0.95])
        with col_check:
            # 체크박스 상태 유지
            if st.checkbox("", key=f"chk_{i}"):
                selected_indices.append(i)
        
        with col_card:
            t_class = f"tier-{art['tier']}" if art['tier'] < 4 else ""
            st.markdown(f"""
                <div class="news-card {t_class}">
                    <span style="font-size:11px; color:#888;">{art['type']} | Tier {art['tier']}</span>
                    <h4 style="margin:5px 0;"><a href="{art['link']}" target="_blank" style="text-decoration:none; color:#1a1a1a;">{art['title']}</a></h4>
                    <div style="font-size:13px; color:#666;"><span class="press-label">{art['source']}</span> | {parse_date(art['date']).strftime('%Y-%m-%d %H:%M')}</div>
                </div>
            """, unsafe_allow_html=True)

    # 하단 고정 플로팅 바 대신 사이드바에 다운로드 버튼 배치
    if selected_indices:
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"✅ {len(selected_indices)}개 선택됨")
        
        # 엑셀 데이터 생성
        export_data = []
        for idx in selected_indices:
            item = st.session_state.news_list[idx]
            export_data.append({
                "매체명": item['source'],
                "기사 제목": item['title'],
                "저자(교수)": extract_professor(item['title']),
                "URL": item['link']
            })
        
        df = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.sidebar.download_button(
            label="📥 엑셀 파일 다운로드",
            data=output.getvalue(),
            file_name=f"KHU_Clipping_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

st.divider()
st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
