import streamlit as st
import feedparser
from datetime import date, timedelta
import urllib.parse

# 웹 페이지 설정
st.set_page_config(page_title="KHU Family News", page_icon="🏥", layout="wide")

st.title("🏥 경희대학교 및 의료기관 실시간 주요 소식")
st.sidebar.info("경희대학교 및 경희의료원(회기/강동) 관련 어제와 오늘의 뉴스를 수집합니다.")

def get_khu_news():
    # 날짜 설정 (어제와 오늘)
    # google search 'before'는 해당 날짜를 포함하지 않으므로, '오늘' 뉴스를 포함하기 위해 '내일'을 종료일로 설정합니다.
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 1. 구글 쿼리는 최대한 핵심 위주로 유지
    keywords = ['"경희대"', '"경희대학교"', '"경희의료원"', '"강동경희"']
    keyword_query = " OR ".join(keywords)
    
    # 2. 검색 단계에서의 노이즈 필터 (도메인 중심)
    noise_filter = "-site:instagram.com -site:facebook.com -site:v.daum.net -site:blog.me"
    query = f"({keyword_query}) after:{yesterday} before:{tomorrow} {noise_filter}"
    encoded_query = urllib.parse.quote(query)
    
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    
    final_entries = []
    
    # 3. [고도화 필터] 제목과 본문을 나누어 검사
    # 제목이 타 대학/정치인이면 '노이즈'일 확률이 99%이므로 제목 중심의 블랙리스트 적용
    title_blacklist = ["성균관대", "조국혁신당", "국민의힘", "더불어민주당", "한양대", "중앙대"]

    for entry in feed.entries:
        title = entry.title
        summary = entry.summary.lower() # RSS 요약문 (본문 일부)
        
        # 필터 A: 제목에 블랙리스트 단어가 있으면 '경희'가 언급되어도 제외 (노이즈 방지)
        # 예: "성균관대-경희대 공동연구" 같은 기사는 살리고 싶다면 이 리스트를 조정하세요.
        if any(bad_word in title for bad_word in title_blacklist):
            continue
            
        # 필터 B: 제목이나 본문 요약 중 한 곳에라도 '경희'가 있으면 통과
        if "경희" in title or "경희" in summary:
            final_entries.append(entry)
            
    return final_entries, yesterday, date.today().strftime('%Y-%m-%d')

# 뉴스 불러오기 버튼
if st.button('🗞️ 최신 소식 업데이트'):
    with st.spinner('경희 가족의 최신 보도자료를 수집 중입니다...'):
        entries, start_d, end_d = get_khu_news()
        
    if not entries:
        st.warning(f"최근 2일({start_d} ~ {end_d}) 동안 보도된 뉴스가 없습니다.")
    else:
        st.success(f"📅 조회 기간: {start_d} ~ {end_d}")
        st.info(f"총 {len(entries)}건의 소식이 검색되었습니다.")
        
        for entry in entries:
            with st.container():
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    # 제목에 링크 연결
                    st.markdown(f"#### [{entry.title}]({entry.link})")
                    st.write(f"**출처:** {entry.source.title} | **보도일시:** {entry.published}")
                with col2:
                    st.write("") # 수직 간격 조절
                    st.link_button("본문 보기", entry.link)
                st.divider()

st.caption(f"Last updated: {date.today()} | Managed by Seunghoon")
