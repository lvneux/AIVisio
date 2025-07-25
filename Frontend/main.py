import streamlit as st
from streamlit_player import st_player
from datetime import datetime

st.set_page_config(page_title="AIVisio", layout="wide")

# 사용자 정의 스타일
st.markdown("""
    <style>
    /* 로고 박스 위치 조정 */
    .logo-box {
        background-color: #fff9d6;
        border-radius: 10px;
        padding: 10px 20px;
        margin: 0px;
        position: absolute;
        top: 10px;
        left: 10px;
    }

    .logo-text {
        font-family: 'Trebuchet MS', sans-serif;
        font-size: 26px;
        font-weight: bold;
        color: #333;
    }

    /* 제목 크기 조정 */
    .section-title {
        font-size: 20px !important;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .chapter-box {
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin-bottom: 5px;
        font-size: 14px;
    }

    /* 드롭다운 버튼 위치 여백 조정 */
    .dropdown-adjust {
        padding-top: 38px;
    }

    /* 메모 상자와 라벨 분리 */
    label[for="memo"] > div:first-child {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# 로고는 상단 가장 왼쪽에 고정 배치
st.markdown('<div class="logo-box"><div class="logo-text">AIVisio</div></div>', unsafe_allow_html=True)

# 공간 확보용 빈 줄
st.markdown("<br><br><br>", unsafe_allow_html=True)

# 레이아웃 정의
col1, col2, col3 = st.columns([1.5, 3.5, 2])

# -------------------- 좌측 영역 --------------------
with col1:
    st.markdown('<div class="section-title">무엇을 공부하시겠습니까?</div>', unsafe_allow_html=True)
    subject = st.selectbox("공부할 주제를 선택하세요", ["Python", "Neural Networks", "C++"], label_visibility="collapsed")

    st.markdown('<div class="section-title" style="margin-top: 20px;">▶ 챕터 목록</div>', unsafe_allow_html=True)
    for i in range(1, 6):
        st.markdown(f'<div class="chapter-box">📌 챕터 {i} - 구현 예정</div>', unsafe_allow_html=True)

# -------------------- 가운데 영역 --------------------
with col2:
    st.markdown('<div class="section-title">추천 교육 영상</div>', unsafe_allow_html=True)
    st_player("https://youtu.be/aircAruvnKk?si=36OqaTVVxkmms_q3")

    st.markdown("---")
    st.markdown('<div class="section-title">주요 개념 학습</div>', unsafe_allow_html=True)

    key_concepts = [
        "뇌와 신경망의 유사점",
        "신경망의 입력층",
        "출력층과 뉴런"
    ]

    for concept in key_concepts:
        col_concept, col_button = st.columns([4, 1])
        col_concept.markdown(f"- {concept}", unsafe_allow_html=True)
        if col_button.button("관련 문제 풀기", key=concept):
            st.warning(f"🔁 '{concept}'에 대한 문제풀이 페이지로 이동 예정입니다 (구현 예정).")

# -------------------- 우측 영역 --------------------
with col3:
    st.markdown('<div class="section-title">✏️ 학습 메모</div>', unsafe_allow_html=True)
    memo_text = st.text_area("memo", placeholder="학습 내용을 메모하세요.", height=300, label_visibility="collapsed")

    st.markdown('<div class="section-title">💾 메모 저장</div>', unsafe_allow_html=True)
    filename = st.text_input("저장 파일명 (확장자 제외)", value=f"memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    file_format = st.radio("파일 형식 선택", ["txt", "pdf"])

    if st.button("저장하기"):
        if memo_text.strip() == "":
            st.error("메모 내용이 비어 있습니다.")
        else:
            if file_format == "txt":
                filepath = f"{filename}.txt"
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(memo_text)
                with open(filepath, "rb") as f:
                    st.download_button("📥 메모 파일 다운로드", f, file_name=filepath)
            elif file_format == "pdf":
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                for line in memo_text.split("\n"):
                    pdf.cell(200, 10, txt=line, ln=True)
                filepath = f"{filename}.pdf"
                pdf.output(filepath)
                with open(filepath, "rb") as f:
                    st.download_button("📥 메모 파일 다운로드", f, file_name=filepath)
