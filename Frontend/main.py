import streamlit as st
from streamlit_player import st_player
from datetime import datetime
from pathlib import Path
import json

st.set_page_config(page_title="AIVisio", layout="wide")

# -------------------- JSON 로딩 유틸 --------------------
@st.cache_data(show_spinner=False)
def load_segments():
    """
    root/Frontend/main.py 기준으로 프로젝트 루트(root) 경로를 계산하고
    root/osc/output/E6DuimPZDz8_segments_with_subtitles.json 파일을 읽어
    (title, summary) 항목 목록을 반환합니다.
    """
    try:
        # 현재 파일 기준으로 프로젝트 루트 계산: .../root/Frontend/main.py -> root
        root_dir = Path(__file__).resolve().parents[1]
        json_path = root_dir / "osc" / "output" / "E6DuimPZDz8_segments_with_subtitles.json"

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items =[]

        # 데이터가 list 형태 또는 dict 내부 리스트일 수 있어 최대한 유연하게 파싱
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # 흔히 쓰는 키들 후보
            for key in ["segments", "data", "items", "results"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                # dict인데 리스트가 없으면 빈 리스트로 처리
                items = []
        else:
            items = []

        def parse_timecode(ts: str):
            if ts is None:
                return None
            ts = str(ts).strip()
            # 허용 형식: "HH:MM:SS", "MM:SS", "SS"
            try:
                parts = [int(p) for p in ts.split(":")]
                sec = 0
                for p in parts:
                    sec = sec * 60 + p
                return sec
            except Exception:
                return None

        # (title, summary)만 추출
        cleaned = []
        for it in items:
            title = it.get("title")
            summary = it.get("summary")

            s_raw = it.get("start_time_formatted") 
            e_raw = it.get("end_time_formatted")

            s_sec = parse_timecode(s_raw)
            e_sec = parse_timecode(e_raw)

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
    """순서를 보존하면서 중복 제거"""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# -------------------- 사용자 정의 스타일 --------------------
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

    /* 좌측 챕터 버튼 스타일 */
    .chapter-btn {
        width: 100%;
        text-align: left;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        cursor: pointer;
    }
    .chapter-btn:hover {
        background: #f9fafb;
    }
    .chapter-btn.active {
        background: #e0f2fe;
        border-color: #93c5fd;
    }
    </style>
""", unsafe_allow_html=True)

# 로고는 상단 가장 왼쪽에 고정 배치
st.markdown('<div class="logo-box"><div class="logo-text">AIVisio</div></div>', unsafe_allow_html=True)

# 공간 확보용 빈 줄
st.markdown("<br><br><br>", unsafe_allow_html=True)

# 세션 상태 초기화
if "selected_title" not in st.session_state:
    st.session_state.selected_title = None

# JSON 로드
segments, load_err = load_segments()
titles = unique_preserve_order([item["title"] for item in segments]) if segments else []

# 레이아웃 정의
col1, col2, col3 = st.columns([1.5, 3.5, 2])

# -------------------- 좌측 영역 --------------------
with col1:
    st.markdown('<div class="section-title">무엇을 공부하시겠습니까?</div>', unsafe_allow_html=True)
    subject = st.selectbox("공부할 주제를 선택하세요", ["Python", "Neural Networks", "C++"], label_visibility="collapsed")

    st.markdown('<div class="section-title" style="margin-top: 20px;">▶ 챕터 목록</div>', unsafe_allow_html=True)

    if load_err:
        st.error(load_err)
        st.info("파일 경로를 확인해주세요: root/osc/output/E6DuimPZDz8_segments_with_subtitles.json")
    elif not titles:
        st.warning("표시할 챕터가 없습니다. JSON에 title 항목이 있는지 확인해주세요.")
    else:
        # 클릭형 챕터 목록
        for i, t in enumerate(titles):
            # 버튼 대신 HTML + st.button 조합으로 활성효과 부여
            # 버튼의 키는 고유해야 하므로 index 포함
            active = (st.session_state.selected_title == t)
            btn_label = f"📌 {t}"
            # 시각적 active 효과를 위해 container 사용
            c = st.container()
            with c:
                # 버튼
                clicked = st.button(btn_label, key=f"chapter_btn_{i}", use_container_width=True)
                # 클릭 시 선택 저장
                if clicked:
                    st.session_state.selected_title = t
            # 버튼 아래에 얇은 구분선
            st.markdown("<hr style='margin:6px 0; border: none; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)

        # 현재 선택된 챕터 표시
        if st.session_state.selected_title:
            st.info(f"선택된 챕터: **{st.session_state.selected_title}**")

# -------------------- 가운데 영역 --------------------
with col2:
    st.markdown('<div class="section-title">추천 교육 영상</div>', unsafe_allow_html=True)
    
    YT_WATCH_URL = "https://www.youtube.com/watch?v=E6DuimPZDz8"
    YT_EMBED_BASE = "https://www.youtube.com/embed/E6DuimPZDz8"

    # 선택된 챕터가 있고, 구간정보가 있으면 그 구간만 재생
    seg_to_play = None
    if st.session_state.selected_title:
        # 같은 타이틀이 여러개면 첫 구간을 기본으로 사용
        candidates = [it for it in segments if it.get("title") == st.session_state.selected_title]
        for c in candidates:
            if c.get("start_sec") is not None and c.get("end_sec") is not None:
                seg_to_play = c
                break

    if seg_to_play:
        # 1차: Streamlit 내장 플레이어 (YouTube URL + start_time/end_time)
        try:
            st.video(
                YT_WATCH_URL,
                start_time=int(seg_to_play["start_sec"]),
                end_time=int(seg_to_play["end_sec"]),
                autoplay=False,
                muted=False,
            )
        except Exception:
            # 2차: 임베드 URL 우회 (start/end 쿼리) — 일부 환경 호환용
            # 유튜브가 end 파라미터를 무시하는 경우도 있어요. 그땐 아래 iframe을 사용하세요.
            from streamlit import components
            embed_url = f"{YT_EMBED_BASE}?start={int(seg_to_play['start_sec'])}&end={int(seg_to_play['end_sec'])}&rel=0&modestbranding=1"
            components.v1.iframe(embed_url, height=360, scrolling=False)
    else:
        # 기본: 전체 영상
        st_player(YT_WATCH_URL)

    # 선택된 챕터 요약 출력 섹션
    st.markdown("---")
    if load_err:
        st.stop()  # 이미 좌측에서 에러 안내
    if st.session_state.selected_title:
        # 선택된 title에 해당하는 모든 summary 모아 출력
        matched = [it for it in segments if it.get("title") == st.session_state.selected_title]
        summaries = [it.get("summary", "") for it in matched if it.get("summary")]
        if summaries:
            # 각 summary를 expander로 보기 좋게 출력
            for idx, s in enumerate(summaries, start=1):
                with st.expander(f"요약 보기", expanded=(len(summaries) == 1)):
                    # 줄바꿈을 유지해서 표시
                    st.markdown(s.replace("\n", "  \n"))
        else:
            st.warning("해당 챕터에 연결된 summary가 없습니다.")
    else:
        st.info("좌측에서 챕터를 선택하면 이 영역에 summary가 표시됩니다.")

    st.markdown("---")
    st.markdown('<div class="section-title">주요 개념 학습</div>', unsafe_allow_html=True)

    key_concepts = [
        st.session_state.selected_title
    ]

    for concept in key_concepts:
        col_concept, col_button = st.columns([4, 1])
        col_concept.markdown(f"- {concept}", unsafe_allow_html=True)
        if col_button.button("관련 문제 풀기", key=f"concept_{concept}"):
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
                # PDF는 줄 길이 제한이 있으므로 multi_cell 사용이 안전하지만,
                # 의존성 최소화를 위해 간단히 cell로 나눠 출력
                for line in memo_text.split("\n"):
                    pdf.cell(200, 10, txt=line, ln=True)
                filepath = f"{filename}.pdf"
                pdf.output(filepath)
                with open(filepath, "rb") as f:
                    st.download_button("📥 메모 파일 다운로드", f, file_name=filepath)