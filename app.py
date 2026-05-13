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
    
    keywords = ["경희대", "경희대학교", "경희의료원", "강동경희대학교병원", "강동경희"]
    keyword_query = " OR ".join(keywords)
    
    # [수정] 노이즈가 많은 사이트들을 제외하여 메이저 언론사 노출 확률을 높임
    # 실무적으로 불필요한 홍보성 매체들을 제외 연산자(-)로 걸러냅니다.
    noise_filter = "-site:v.daum.net -site:blog.me -site:tistory.com -site:cafe.naver.com"
    
    # 최종 쿼리: 키워드 + 날짜 + 노이즈 필터
    query = f"({keyword_query}) after:{yesterday} before:{tomorrow} {noise_filter}"
    encoded_query = urllib.parse.quote(query)
    
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    feed = feedparser.parse(rss_url)
    return feed.entries, yesterday, date.today().strftime('%Y-%m-%d')

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
