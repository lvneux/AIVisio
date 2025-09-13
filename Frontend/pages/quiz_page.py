import streamlit as st
from pathlib import Path
import json
import sys
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from osc.controllers.quiz import generate_quizzes, check_answer  

st.set_page_config(page_title="AIVisio - Quiz", layout="wide")


def load_segments() -> List[Dict[str, Any]]:
    """
    Load the same segments JSON used by main.py.
    Path: root/osc/output/E6DuimPZDz8_segments_with_subtitles.json
    """
    json_path = ROOT_DIR / "osc" / "output" / "E6DuimPZDz8_segments_with_subtitles.json"
    if not json_path.exists():
        st.error(f"세그먼트 파일을 찾을 수 없습니다: {json_path}")
        return []
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

st.title(f"퀴즈: {quiz_title}")

segments = load_segments()
context_text = build_context_from_segments(segments, quiz_title)
st.write("summary :", context_text)

if not context_text:
    st.warning("해당 챕터의 summary가 없어 기본 지식으로 퀴즈를 생성합니다.")

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

st.markdown("""
    <style>
    section[data-testid="stSidebar"] { 
        display: none !important; 
    }
    nav[aria-label="Main navigation"], 
    div[data-testid="stSidebarNav"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

all_correct = True

for idx, q in enumerate(quizzes):
    st.markdown('<div class="qcard">', unsafe_allow_html=True)
    st.markdown(f'<div class="qtitle">문항 {idx+1}</div>', unsafe_allow_html=True)
    st.markdown(q["question"])

    qtype = q.get("type", "short")

    if qtype == "OX":
        default_idx = 0 if states[idx]["answer"] in ["", "O"] else 1
        choice = st.radio(
            "정답을 선택하세요:",
            options=["O", "X"],
            index=default_idx,
            key=f"q_{idx}_choice",
            horizontal=True,
        )
        states[idx]["answer"] = choice

    col_check, col_retry = st.columns([1, 1])

    if col_check.button("정답 확인", key=f"check_{idx}"):
        result = check_answer(q, states[idx]["answer"])
        states[idx]["tries"] += 1
        states[idx]["is_correct"] = bool(result.get("correct", False))
        states[idx]["feedback"] = result.get("feedback", "")

    if col_retry.button("다시 시도", key=f"retry_{idx}"):
        states[idx]["answer"] = "" if qtype == "short" else "O"
        states[idx]["is_correct"] = False
        states[idx]["feedback"] = ""

    if states[idx]["is_correct"]:
        st.success("정답입니다! 🎉")
    elif states[idx]["feedback"]:
        st.error(states[idx]["feedback"])

    st.markdown("</div>", unsafe_allow_html=True) 

    all_correct = all_correct and states[idx]["is_correct"]

st.markdown("---")

if all_correct and quizzes:
    st.success("축하합니다! 3개 문항을 모두 맞췄습니다. 메인 페이지에서 해당 챕터가 완료 표시됩니다. ✅")
    if "completed_chapters" not in st.session_state:
        st.session_state.completed_chapters = []
    completed_set = set(st.session_state.completed_chapters)
    if quiz_title not in completed_set:
        completed_set.add(quiz_title)
        st.session_state.completed_chapters = list(completed_set)

col_back1, col_back2 = st.columns([1, 9])
with col_back1:
    if st.button("◀ 메인으로 돌아가기", use_container_width=True):
        try:
            st.switch_page("./main.py")
        except Exception:
            st.experimental_set_query_params()
            st.session_state.pop("quiz_title", None)
            st.rerun()
