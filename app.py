import pandas as pd
from io import BytesIO

# --- 엑셀 생성 함수 ---
def to_excel(df):
    output = BytesIO()
    # 엑셀 스타일 적용을 위해 pandas의 ExcelWriter 사용
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='News_Clipping')
        workbook = writer.book
        worksheet = writer.sheets['News_Clipping']
        
        # 헤더 스타일 및 열 너비 조정 로직 추가 가능
    return output.getvalue()

# --- 뉴스 출력 부분 수정 ---
selected_articles = [] # 선택된 기사를 담을 리스트

for i, article in enumerate(final_list):
    col_check, col_card = st.columns([0.05, 0.95])
    
    with col_check:
        # 각 기사마다 체크박스 추가
        is_selected = st.checkbox(f"sel_{i}", label_visibility="collapsed")
        if is_selected:
            # 저자 정보는 제목이나 본문에서 추출하는 로직이 필요하거나 직접 입력할 수 있습니다.
            selected_articles.append({
                "매체명": article['source'],
                "기사 제목": article['title'],
                "저자(교수)": "-", # 자동 수집 시에는 비워두거나 수동 입력
                "URL": article['link']
            })
            
    with col_card:
        # 기존 뉴스 카드 디자인 출력
        st.markdown(f"""
            <div class="news-card">...기존 코드...</div>
        """, unsafe_allow_html=True)

# --- 하단 다운로드 버튼 ---
if selected_articles:
    st.divider()
    df_selected = pd.DataFrame(selected_articles)
    
    # 엑셀 파일 생성
    excel_data = to_excel(df_selected)
    
    st.download_button(
        label="📥 선택한 기사 엑셀로 추출하기",
        data=excel_data,
        file_name=f"KHU_News_Clipping_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
