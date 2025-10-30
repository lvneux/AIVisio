import streamlit as st
from pathlib import Path
import json
import sys
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from Backend.controllers.quiz import generate_quizzes, check_answer

st.set_page_config(page_title="AIVisio - Quiz", layout="wide")


def load_segments() -> List[Dict[str, Any]]:
    """
    Load the same segments JSON used by main.py.
    """
    try:
        output_dir = ROOT_DIR / "Backend" / "output"
        video_id_prefix = st.session_state.get("selected_video_id", "aircAruvnKk") 
        original_path = output_dir / f"{video_id_prefix}_segments_with_subtitles.json"

        json_path_to_load = None
        if original_path.exists():
            json_path_to_load = original_path
        else:
            pattern = f"{video_id_prefix}_segments_with_subtitles_*.json"
            found_files = list(output_dir.glob(pattern))
            if found_files:
                json_path_to_load = found_files[0]
            else:
                st.error(f"세그먼트 파일 파싱 오류: 'Backend/output/{video_id_prefix}_segments_with_subtitles.json' 또는 언어 코드가 붙은 파일을 찾을 수 없습니다.")
                return []

        with open(json_path_to_load, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ["segments", "data", "items", "results"]:
                if k in data and isinstance(data[k], list):
                    return data[k]
        return []
    except Exception as e:
        st.error(f"세그먼트 파일 로드 및 파싱 중 오류: {e}")
        return []


def build_context_from_segments(segments: List[Dict[str, Any]], title: str) -> str:
    """
    Concatenate all summaries for the selected chapter title.
    """
    if not title:
        return ""
    parts = [
        it.get("summary", "")
        for it in segments
        if it.get("title") == title and it.get("summary")
    ]
    return "\n\n".join([p for p in parts if p]).strip()


quiz_title = st.session_state.get("quiz_title")

if not quiz_title:
    qp = st.experimental_get_query_params()
    quiz_title = qp.get("quiz_title", [None])[0] if "quiz_title" in qp else None

if not quiz_title:
    st.error("퀴즈 대상 챕터 정보가 없습니다. 메인 페이지에서 챕터를 선택하고 '관련 문제 풀기'를 눌러주세요.")
    st.stop()

# ---------------------- 스타일 ----------------------
st.markdown(
    """
    <style>
    /* 사이드바 숨김 */
    section[data-testid="stSidebar"], nav[aria-label="Main navigation"], div[data-testid="stSidebarNav"] {display:none !important;}
    /* 페이지 여백 */
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    
    /* 퀴즈 제목 크기 축소 */
    h2 { 
        font-size: 28px;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }
    
    /* 메인 페이지 돌아가기 버튼의 글씨 크기 키우기 및 테두리 추가 */
    div[data-testid="stPageLink"] a { 
        display: inline-flex; /* 버튼처럼 보이게 함 */
        align-items: center;
        justify-content: center;
        padding: 6px 12px; /* 버튼의 크기(상하/좌우 여백)를 키움 */
        font-size: 16px;
        font-weight: 600;
        border: 1px solid #ccc; /* 테두리 색상 및 두께 설정 */
        border-radius: 8px; /* 둥근 모서리 */
        color: #333; /* 텍스트 색상 (기존 파란색 링크 대신) */
        text-decoration: none; /* 밑줄 제거 */
        background-color: #f0f2f6; /* 배경색 추가 */
        transition: background-color 0.1s;
    }
    div[data-testid="stPageLink"] a:hover {
        background-color: #e0e0e0; /* 마우스 오버 시 색상 변경 */
    }
    
    /* 진행률 배지 */
    .progress-row { display:flex; align-items:center; gap:12px; }
    .pill {
        display:inline-flex; align-items:center; gap:8px;
        padding:6px 10px; border-radius:999px;
        background:#eef2ff; color:#1e40af; font-weight:700; font-size:13px;
        border:1px solid #dbeafe;
        float: right; 
    }
    .qtitle{
        color:#2563eb; font-weight:800; font-size:18px; margin:8px 0 6px;
    }
    .qtext{ font-size:18px; line-height:1.55; margin-bottom:10px; }
    /* 라디오와 라벨 큰 글씨 */
    [data-testid="stRadio"] label{ font-size:17px !important; }
    /* 정답확인 버튼 스타일 */
    .stButton>button { 
        border-radius:10px !important; 
        font-weight: 700; 
        margin-top: 0;
        vertical-align: bottom;
    }
    
    /* 정답일 때 버튼 색상 (빨간색 -> 초록색) */
    .stButton>button[data-is-correct="true"] { 
        background-color: #10b981 !important; 
        color: white !important;
        border-color: #10b981 !important;
    }
    
    /* 오답 알림 박스 */
    .alert {
        width: 100%; 
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 15px;
        border: 1px solid;
    }
    .alert-success { background:#eaf7ee; color:#065f46; border-color:#86efac; }
    .alert-error   { background:#fff1f2; color:#991b1b; border-color:#fecaca; }
    /* 문항 간 여백만으로 구분 */
    .qgap{ height: 18px; }
    
    /* 정답 입력 안내 문구 삭제 */
    div[data-testid="stTextInput"] label { 
        display: none !important; 
        height: 0 !important; 
        margin: 0 !important; 
        padding: 0 !important;
    }
    /* st.text_input을 감싸는 div의 상단 패딩 제거 */
    div[data-testid="stTextInput"] { 
        padding-top: 0 !important; 
        margin-top: 0 !important;
    }

    /* st.expander 내부 텍스트 스타일 */
    .summary-text p {
        font-size: 15px; 
        line-height: 1.6; 
        color: #495057; 
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# [수정] 버튼이 잘리지 않도록 더 큰 여백을 상단에 추가
st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) 

# 메인 페이지로 돌아가기 버튼을 제목 위에 독립적인 줄에 배치
st.page_link("main.py", label="◀ 메인 페이지", help="메인 페이지로 돌아가기", icon=None) 

# [수정] 버튼과 제목 사이에 여백 추가 (아래 컨텐츠를 더 내림)
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) 

# 컬럼 분리 없이 st.header를 사용하여 제목을 출력
st.header(f"퀴즈: {quiz_title}")

segments = load_segments()
context_text = build_context_from_segments(segments, quiz_title)

# 요약 내용: 사용자가 원할 때만 보이도록 st.expander 사용
if context_text:
    html_summary = context_text.replace("\n", "<br>")
    with st.expander("해당 챕터의 요약 내용 (답을 모를 시 열어보세요.)"):
        st.markdown(
            f"<div class='summary-text'><p>{html_summary}</p></div>",
            unsafe_allow_html=True
        )

else:
    # 요약 내용이 없을 경우의 메시지
    st.caption("해당 챕터의 summary가 없어 기본 지식으로 퀴즈를 생성합니다.")


# 세션 준비
if "quizzes" not in st.session_state:
    st.session_state.quizzes = {}
if quiz_title not in st.session_state.quizzes:
    with st.spinner("퀴즈를 생성 중입니다..."):
        st.session_state.quizzes[quiz_title] = generate_quizzes(quiz_title, context_text)

quizzes = st.session_state.quizzes[quiz_title]

if "quiz_states" not in st.session_state:
    st.session_state.quiz_states = {}
if quiz_title not in st.session_state.quiz_states:
    st.session_state.quiz_states[quiz_title] = [
        {"answer": "", "is_correct": False, "tries": 0, "feedback": ""}
        for _ in quizzes
    ]

states = st.session_state.quiz_states[quiz_title]

# 진행률/정렬용 공통 비율 (우측 공백 제거)
# [수정] 진행률 바 길이 조정: [5.7, 0.7] -> [5.0, 0.4] (요약 내용 끝선과 동일하게 맞추기 위함)
PROG_RATIO = [5.9, 0.7] 
# 입력 필드 (4.5), 정답확인 버튼 (0.5) 비율
INPUT_RATIO = [4.5, 0.5] 


# ---------------------- 진행률 (실시간) ----------------------
def render_progress():
    total = max(len(quizzes), 1)
    correct_cnt = sum(1 for s in states if s["is_correct"])
    progress = correct_cnt / total

    # PROG_RATIO는 함수 외부의 전역 변수를 사용합니다.
    col_prog_bar, col_prog_pill = st.columns(PROG_RATIO)
    with col_prog_bar:
        st.progress(progress, text=f"진행률 {int(progress*100)}%")
    with col_prog_pill:
        # 진행률 배지를 오른쪽 끝에 정렬 (CSS float: right 사용)
        st.markdown(
            f"<div class='progress-row'><span class='pill'>✅ {correct_cnt} / {total}</span></div>",
            unsafe_allow_html=True,
        )

# 상단에 진행률 표시
render_progress()

# ---------------------- 문항 렌더링 ----------------------
all_correct = True

for idx, q in enumerate(quizzes):
    # 문항 타이틀/본문
    st.markdown(f'<div class="qtitle">문항 {idx+1}</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='qtext'>{q['question']}</div>", unsafe_allow_html=True)

    qtype = q.get("type", "short")

    # 입력 필드 (4.5), 정답확인 버튼 (0.5) 비율 사용
    
    if qtype == "OX":
        # 라디오와 확인 버튼을 한 줄에 배치 (우측 공백 제거)
        col_radio, col_check = st.columns(INPUT_RATIO)
        
        with col_radio:
            default_idx = 0 if states[idx]["answer"] in ["", "O"] else 1
            choice = st.radio(
                "정답을 선택하세요:",
                options=["O", "X"],
                index=default_idx,
                key=f"q_{idx}_choice",
                horizontal=True,
            )
            states[idx]["answer"] = choice

        # 정답 확인 버튼 위치 및 정렬 (입력 필드와 일직선상에 오도록)
        with col_check:
            
            # 정답 확인 버튼 출력
            if st.button("정답 확인", key=f"check_{idx}", type="primary", use_container_width=True): 
                result = check_answer(q, states[idx]["answer"])
                states[idx]["tries"] += 1
                states[idx]["is_correct"] = bool(result.get("correct", False))
                states[idx]["feedback"] = result.get("feedback", "")
                st.rerun()
            
            # 정답일 경우 버튼 색상 변경을 위한 JavaScript 삽입
            st.markdown(f"""
            <script>
                const button = document.querySelector('[key="check_{idx}"] button');
                if (button) {{
                    button.setAttribute('data-is-correct', '{str(states[idx]["is_correct"]).lower()}');
                    # OX 버튼의 수직 정렬을 위한 CSS 조정
                    const container = button.closest('div[data-testid^="stColumn"]');
                    if (container) {{
                        container.style.marginTop = '-5px'; 
                    }}
                }}
            </script>
            """, unsafe_allow_html=True)


    else: # Short Answer
        # 입력 박스와 확인 버튼을 한 줄에 배치 (우측 공백 제거)
        col_ans, col_check = st.columns(INPUT_RATIO)

        with col_ans:
            # '정답을 입력하세요:' 텍스트 삭제 및 빈 공간 채우기
            states[idx]["answer"] = st.text_input(
                "정답 입력",
                key=f"q_{idx}_text",
                placeholder="정답 입력",
                label_visibility="collapsed", # 라벨 공간을 완전히 없앰
            )

        # 정답 확인 버튼 위치 및 정렬 (입력 필드와 일직선상에 오도록)
        with col_check:
            
            # 정답 확인 버튼 출력
            if st.button("정답 확인", key=f"check_{idx}", type="primary", use_container_width=True): 
                result = check_answer(q, states[idx]["answer"])
                states[idx]["tries"] += 1
                states[idx]["is_correct"] = bool(result.get("correct", False))
                states[idx]["feedback"] = result.get("feedback", "")
                st.rerun()
                
            # 정답일 경우 버튼 색상 변경을 위한 JavaScript 삽입
            st.markdown(f"""
            <script>
                const button = document.querySelector('[key="check_{idx}"] button');
                if (button) {{
                    button.setAttribute('data-is-correct', '{str(states[idx]["is_correct"]).lower()}');
                }}
            </script>
            """, unsafe_allow_html=True)

    # 결과 표시: 정답일 시 박스 및 '다시 시도' 버튼 제거 
    if states[idx]["is_correct"]:
        pass 
    elif states[idx]["feedback"]:
        # 오답 안내 박스만 출력하고 '다시 시도' 버튼 제거
        left_box, right_btn = st.columns(INPUT_RATIO)
        with left_box:
            st.markdown(f"<div class='alert alert-error'>{states[idx]['feedback']}</div>", unsafe_allow_html=True)
        with right_btn:
            pass # '다시 시도' 버튼 제거


    # 문항 간 여백
    st.markdown('<div class="qgap"></div>', unsafe_allow_html=True)

    all_correct = all_correct and states[idx]["is_correct"]

st.markdown("---")

if all_correct and quizzes:
    st.success("축하합니다! 모든 문항을 맞췄습니다. 메인 페이지에서 해당 챕터가 완료 표시됩니다. ✅")
    if "completed_chapters" not in st.session_state:
        st.session_state.completed_chapters = []
    completed_set = set(st.session_state.completed_chapters)
    if quiz_title not in completed_set:
        completed_set.add(quiz_title)
        st.session_state.completed_chapters = list(completed_set)
