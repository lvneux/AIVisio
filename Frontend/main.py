import streamlit as st
from streamlit_player import st_player  # 필요시 유지
from datetime import datetime
from pathlib import Path
import json
import sys
from streamlit import components  # iframe 렌더링용

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

st.set_page_config(page_title="AIVisio", layout="wide")

@st.cache_data(show_spinner=False)
def load_segments():
    try:
        root_dir = Path(__file__).resolve().parents[1]
        json_path = root_dir / "osc" / "output" / "E6DuimPZDz8_segments_with_subtitles.json"

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ["segments", "data", "items", "results"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

        def parse_timecode(ts: str):
            if ts is None:
                return None
            ts = str(ts).strip()
            try:
                parts = [int(p) for p in ts.split(":")]
                sec = 0
                for p in parts:
                    sec = sec * 60 + p
                return sec
            except Exception:
                return None

        cleaned = []
        for it in items:
            title = it.get("title")
            summary = it.get("summary")
            s_sec = parse_timecode(it.get("start_time_formatted"))
            e_sec = parse_timecode(it.get("end_time_formatted"))
            if title is not None:
                cleaned.append({
                    "title": str(title),
                    "summary": summary,
                    "start_sec": s_sec,
                    "end_sec": e_sec
                })

        return cleaned, None
    except FileNotFoundError as e:
        return [], f"파일을 찾을 수 없습니다: {e}"
    except Exception as e:
        return [], f"JSON 파싱 중 오류가 발생했습니다: {e}"

def unique_preserve_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

st.markdown("""
    <style>
    .logo-box { background-color: #fff9d6; border-radius: 10px; padding: 10px 20px; margin: 0px; position: absolute; top: 10px; left: 10px; }
    .logo-text { font-family: 'Trebuchet MS', sans-serif; font-size: 26px; font-weight: bold; color: #333; }
    .section-title { font-size: 20px !important; font-weight: 600; margin-bottom: 8px; }
    .chapter-box { padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 5px; font-size: 14px; }
    .dropdown-adjust { padding-top: 38px; }
    label[for="memo"] > div:first-child { display: none; }

    /* 완료(비활성) 버튼 공통 스타일 - 모양/간격은 기본 버튼과 동일, 색만 회색화 */
    button[disabled][data-testid="baseButton-secondary"]{
      background: #e5e7eb !important;   /* bg-gray-200 */
      border-color: #d1d5db !important;  /* border-gray-300 */
      color: #6b7280 !important;         /* text-gray-500 */
      opacity: 0.85;
      cursor: not-allowed !important;
    }
    button[disabled][data-testid="baseButton-secondary"]:hover{
      filter: none !important;
      transform: none !important;
    }

    /* (요청) 기본 사이드바/페이지 네비 숨김 */
    section[data-testid="stSidebar"] { display: none !important; }

    /* selectbox 라벨 숨김 */
    div[data-testid="stSelectbox"] > label { display:none; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="logo-box"><div class="logo-text">AIVisio</div></div>', unsafe_allow_html=True)
st.markdown("<br><br><br>", unsafe_allow_html=True)

if "selected_title" not in st.session_state:
    st.session_state.selected_title = None
if "completed_chapters" not in st.session_state:
    st.session_state.completed_chapters = []

segments, load_err = load_segments()
titles = unique_preserve_order([item["title"] for item in segments]) if segments else []

YT_EMBED_BASE = "https://www.youtube.com/embed/E6DuimPZDz8"

def render_video(start=None, end=None, height=480):
    """항상 동일 iframe 렌더러 + 고정 높이 + 자동재생(음소거)"""
    params = ["rel=0", "modestbranding=1", "autoplay=1", "mute=1"]
    if isinstance(start, int) and start >= 0:
        params.append(f"start={start}")
    if isinstance(end, int) and end > 0:
        params.append(f"end={end}")
    embed_url = f"{YT_EMBED_BASE}?{'&'.join(params)}"
    components.v1.iframe(embed_url, height=height, scrolling=False)

col1, col2, col3 = st.columns([1.5, 3.5, 2])

# 왼쪽
with col1:
    st.markdown('<div class="section-title">무엇을 공부하시겠습니까?</div>', unsafe_allow_html=True)
    subject = st.selectbox("공부할 주제를 선택하세요", ["Python", "Neural Networks", "C++"], label_visibility="collapsed")

    st.markdown('<div class="section-title" style="margin-top: 20px;">챕터 목록</div>', unsafe_allow_html=True)

    if load_err:
        st.error(load_err)
    elif not titles:
        st.warning("표시할 챕터가 없습니다. JSON에 title 항목이 있는지 확인해주세요.")
    else:
        completed_set = set(st.session_state.completed_chapters)
        for i, t in enumerate(titles):
            completed = t in completed_set
            # ✅ 완료면 비활성(button disabled), 미완료면 클릭 가능
            if st.button(f"📌 {t}", key=f"chapter_btn_{i}", use_container_width=True, disabled=completed):
                st.session_state.selected_title = t

# 중간
with col2:
    st.markdown('<div class="section-title">추천 교육 영상</div>', unsafe_allow_html=True)

    seg_to_play = None
    if st.session_state.selected_title:
        for c in (it for it in segments if it.get("title") == st.session_state.selected_title):
            if c.get("start_sec") is not None and c.get("end_sec") is not None:
                seg_to_play = c
                break

    if seg_to_play:
        render_video(start=int(seg_to_play["start_sec"]), end=int(seg_to_play["end_sec"]), height=480)
    else:
        render_video(height=480)

    st.markdown("---")
    if load_err:
        st.stop()

    if st.session_state.selected_title:
        summaries = [
            it.get("summary", "")
            for it in segments
            if it.get("title") == st.session_state.selected_title and it.get("summary")
        ]
        if summaries:
            for idx, s in enumerate(summaries, start=1):
                with st.expander("요약 보기", expanded=(len(summaries) == 1)):
                    st.markdown(s.replace("\n", "  \n"))
        else:
            st.warning("해당 챕터에 연결된 summary가 없습니다.")
    else:
        st.info("좌측에서 챕터를 선택하면 이 영역에 summary가 표시됩니다.")

    st.markdown("---")
    st.markdown('<div class="section-title">주요 개념 학습</div>', unsafe_allow_html=True)

    key_concepts = [st.session_state.selected_title] if st.session_state.selected_title else []
    for concept in key_concepts:
        col_concept, col_button = st.columns([4, 1])
        col_concept.markdown(f"- {concept}", unsafe_allow_html=True)
        if col_button.button("관련 문제 풀기", key=f"concept_quiz_{concept}"):
            st.session_state.quiz_title = concept
            try:
                st.switch_page("pages/quiz_page.py")
            except Exception:
                st.experimental_set_query_params(quiz_title=concept)
                st.rerun()

# 오른쪽
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
