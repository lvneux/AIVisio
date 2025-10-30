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
    Path: root/Backend/output/E6DuimPZDz8_segments_with_subtitles.json
    """
    json_path = "./Backend/output/aircAruvnKk_segments_with_subtitles_en.json"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ["segments", "data", "items", "results"]:
                if k in data and isinstance(data[k], list):
                    return data[k]
        return []
    except Exception as e:
        st.error(f"세그먼트 파일 파싱 오류: {e}")
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
    /* 진행률 배지 */
    .progress-row { display:flex; align-items:center; gap:12px; }
    .pill {
        display:inline-flex; align-items:center; gap:8px;
        padding:6px 10px; border-radius:999px;
        background:#eef2ff; color:#1e40af; font-weight:700; font-size:13px;
        border:1px solid #dbeafe;
    }
    .qtitle{
        color:#2563eb; font-weight:800; font-size:18px; margin:8px 0 6px;
    }
    .qtext{ font-size:18px; line-height:1.55; margin-bottom:10px; }
    /* 라디오와 라벨 큰 글씨 */
    [data-testid="stRadio"] label{ font-size:17px !important; }
    .stButton>button{ border-radius:10px !important; }
    /* 알림 상자(진행률 너비와 동일하게 보이도록 왼쪽 컬럼에 넣어서 사용) */
    .alert {
        width: 100%;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 15px;
        border: 1px solid;
    }
    .alert-success { background:#eaf7ee; color:#065f46; border-color:#86efac; }
    .alert-error   { background:#fff1f2; color:#991b1b; border-color:#fecaca; }
    /* 문항 간 여백만으로 구분 */
    .qgap{ height: 18px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(f"퀴즈: {quiz_title}")

segments = load_segments()
context_text = build_context_from_segments(segments, quiz_title)
st.caption(context_text if context_text else "해당 챕터의 summary가 없어 기본 지식으로 퀴즈를 생성합니다.")

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

# 진행률/정렬용 공통 비율
PROG_RATIO = [5, 1.4]

# ---------------------- 진행률 (실시간) ----------------------
def render_progress():
    total = max(len(quizzes), 1)
    correct_cnt = sum(1 for s in states if s["is_correct"])
    progress = correct_cnt / total

    col_prog_bar, col_prog_pill = st.columns(PROG_RATIO)
    with col_prog_bar:
        st.progress(progress, text=f"진행률 {int(progress*100)}%")
    with col_prog_pill:
        st.markdown(
            f"<div class='progress-row'><span class='pill'>✅ {correct_cnt} / {total}</span></div>",
            unsafe_allow_html=True,
        )

# 상단에 진행률 표시
render_progress()

# ---------------------- 문항 렌더링 ----------------------
all_correct = True

for idx, q in enumerate(quizzes):
    # 문항 타이틀/본문 (카드 제거, 여백만)
    st.markdown(f'<div class="qtitle">문항 {idx+1}</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='qtext'>{q['question']}</div>", unsafe_allow_html=True)

    qtype = q.get("type", "short")

    if qtype == "OX":
        # 라디오도 진행률과 동일 폭으로 정렬
        left_radio, right_space = st.columns(PROG_RATIO)
        with left_radio:
            default_idx = 0 if states[idx]["answer"] in ["", "O"] else 1
            choice = st.radio(
                "정답을 선택하세요:",
                options=["O", "X"],
                index=default_idx,
                key=f"q_{idx}_choice",
                horizontal=True,
            )
            states[idx]["answer"] = choice
        with right_space:
            st.write("")
    else:
        # 입력 박스를 진행률과 동일 폭으로 정렬
        left_ans, right_space = st.columns(PROG_RATIO)
        with left_ans:
            states[idx]["answer"] = st.text_input(
                "정답을 입력하세요:",
                key=f"q_{idx}_text",
                placeholder="정답 입력",
            )
        with right_space:
            st.write("")

    # 정답 확인 버튼 (좌측 정렬)
    col_check, _ = st.columns([1, 3])
    if col_check.button("정답 확인", key=f"check_{idx}", type="primary"):
        result = check_answer(q, states[idx]["answer"])
        states[idx]["tries"] += 1
        states[idx]["is_correct"] = bool(result.get("correct", False))
        states[idx]["feedback"] = result.get("feedback", "")
        # ▶ 진행률 즉시 반영
        st.rerun()

    # 결과 표시: 진행률 레이아웃과 동일한 폭으로 배치 + 오른쪽에 '다시 시도'
    if states[idx]["is_correct"]:
        left_box, right_btn = st.columns(PROG_RATIO)
        with left_box:
            st.markdown("<div class='alert alert-success'>정답입니다! 🎉</div>", unsafe_allow_html=True)
        with right_btn:
            if st.button("다시 시도", key=f"retry_ok_{idx}"):
                states[idx]["answer"] = "" if qtype == "short" else "O"
                states[idx]["is_correct"] = False
                states[idx]["feedback"] = ""
                st.rerun()
    elif states[idx]["feedback"]:
        left_box, right_btn = st.columns(PROG_RATIO)
        with left_box:
            st.markdown(f"<div class='alert alert-error'>{states[idx]['feedback']}</div>", unsafe_allow_html=True)
        with right_btn:
            if st.button("다시 시도", key=f"retry_ng_{idx}"):
                states[idx]["answer"] = "" if qtype == "short" else "O"
                states[idx]["is_correct"] = False
                states[idx]["feedback"] = ""
                st.rerun()

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

# 하단 버튼: 한 줄 표시를 위해 첫 번째 컬럼 폭을 넓힘
col_back1, col_back2 = st.columns([3, 7])
with col_back1:
    if st.button("◀ 메인으로 돌아가기", use_container_width=True):
        try:
            st.switch_page("./main.py")
        except Exception:
            st.experimental_set_query_params()
            st.session_state.pop("quiz_title", None)
            st.rerun()
