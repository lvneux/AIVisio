import os
import re
import json
import sys
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path
from streamlit import components
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from osc import main as osc_main  # osc > main.py 호출

API_KEY = "AIzaSyAOwWaR6XuNF3w5YxFDSYZrPFyrEqw81UE"

st.set_page_config(page_title="AIVisio", layout="wide")

# 선택한 영상 정보를 osc/output/selected_video.json에 저장
def save_selected_video(video_id: str, video_title: str | None = None):
    try:
        root_dir = Path(__file__).resolve().parents[1]  # 프로젝트 루트
        output_dir = root_dir / "osc" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "video_id": video_id,
            "title": video_title or "",
            "saved_at": datetime.now().isoformat(timespec="seconds")
        }
        with open(output_dir / "selected_video.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"선택한 영상 정보를 저장하는 중 경고: {e}")

# JSON 로더 (기존 챕터 처리 유지)
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

# 스타일 (+ 오버레이 배지 스타일 추가)
st.markdown("""
    <style>
    .logo-box { background-color: #fff9d6; border-radius: 10px; padding: 10px 20px; margin: 0px; position: absolute; top: 10px; left: 10px; }
    .logo-text { font-family: 'Trebuchet MS', sans-serif; font-size: 26px; font-weight: bold; color: #333; }
    .section-title { font-size: 20px !important; font-weight: 600; margin-bottom: 8px; }
    .chapter-box { padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 5px; font-size: 14px; }
    label[for="memo"] > div:first-child { display: none; }
    .video-title { font-size: 13px; font-weight: 600; line-height: 1.2; margin: 4px 0 8px; }

    /* 썸네일 카드 컨테이너 */
    .thumb-wrap {
        position: relative;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        background: #000;
        margin-bottom: 6px;
    }
    /* 16:9 비율 유지 */
    .thumb-inner {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }
    /* 길이 배지 */
    .duration-badge {
        position: absolute;
        right: 6px;
        bottom: 6px;
        background: rgba(0,0,0,0.75);
        color: #fff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        line-height: 1;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="logo-box"><div class="logo-text">AIVisio</div></div>', unsafe_allow_html=True)
st.markdown("<br><br><br>", unsafe_allow_html=True)

# 상태 초기화
if "selected_title" not in st.session_state:
    st.session_state.selected_title = None
if "completed_chapters" not in st.session_state:
    st.session_state.completed_chapters = []
if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = None
if "selected_video_title" not in st.session_state:
    st.session_state.selected_video_title = None
if "learning_started" not in st.session_state:
    st.session_state.learning_started = False
if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = "Python"
if "processed_video_ids" not in st.session_state:
    st.session_state.processed_video_ids = set()

# 데이터 로딩
segments, load_err = load_segments()
titles = unique_preserve_order([item["title"] for item in segments]) if segments else []

# YouTube API/썸네일 유틸
def yt_thumb(id_: str, quality: str = "hqdefault"):
    return f"https://img.youtube.com/vi/{id_}/{quality}.jpg"

def render_video(video_id: str, start=None, end=None, height=480):
    base = f"https://www.youtube.com/embed/{video_id}"
    params = ["rel=0", "modestbranding=1", "autoplay=1", "mute=1"]
    if isinstance(start, int) and start >= 0:
        params.append(f"start={start}")
    if isinstance(end, int) and end > 0:
        params.append(f"end={end}")
    embed_url = f"{base}?{'&'.join(params)}"
    components.v1.iframe(embed_url, height=height, scrolling=False)

def parse_duration(duration_str: str) -> int:
    # 영상 길이 - 초 단위
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    return hours * 3600 + minutes * 60 + seconds

def format_duration(seconds: int) -> str:
    # 초 → 'H:MM:SS' 또는 'M:SS' 형태
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    else:
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"

def thumbnail_with_duration_html(video_id: str, duration_text: str) -> str:
    # 썸네일 및 영상 길이 html 반환
    bg = yt_thumb(video_id)
    return f"""
    <div class="thumb-wrap">
        <div class="thumb-inner" style="background-image:url('{bg}');"></div>
        <div class="duration-badge">{duration_text}</div>
    </div>
    """

# 자막 체크: 한국어 우선, 없으면 영어 / 자동 생성 자막 제외
def has_pref_transcript(video_id: str) -> bool:
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)

        has_manual_ko = False
        has_manual_en = False

        for t in tl:
            if not t.is_generated:  # 반드시 수동 자막만
                if t.language_code.startswith("ko"):
                    has_manual_ko = True
                    break  # 한국어 수동 자막 있으면 바로 True 반환
                elif t.language_code.startswith("en"):
                    has_manual_en = True

        # 한국어 수동 자막이 최우선, 없으면 영어 수동 자막 확인
        return has_manual_ko or has_manual_en

    except (TranscriptsDisabled, Exception):
        return False

# 검색 단계에서부터 "자막 있는 영상"만 추출
@st.cache_data(show_spinner=False)
def fetch_top_videos(subject: str):
    if not API_KEY:
        raise RuntimeError("YouTube API 키가 지정되지 않았습니다.")

    q = subject
    if subject in ["Python", "C"]:
        q = f"{subject} programming tutorial"

    # search API → 후보 영상 추출
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": API_KEY,
        "part": "snippet",
        "q": q,
        "type": "video",
        "maxResults": 50,
        "relevanceLanguage": "ko",
        "safeSearch": "none",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])

    # videoId 안전 추출
    video_ids = [it.get("id", {}).get("videoId") for it in items if it.get("id", {}).get("videoId")]
    if not video_ids:
        return []

    # 2) videos API → 길이/제목 가져오기
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": API_KEY,
        "part": "contentDetails,snippet",
        "id": ",".join(video_ids),
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("items", [])

    results = []
    for it in items:
        vid = it["id"]
        title = it["snippet"]["title"]
        duration_iso = it["contentDetails"]["duration"]
        length_sec = parse_duration(duration_iso)

        # 길이 (10~30분) + 자막(ko 우선, 없으면 en / 자동 생성 제외) 필터
        if 600 <= length_sec <= 1800 and has_pref_transcript(vid):
            results.append({
                "id": vid,
                "title": title,
                "duration_sec": length_sec,
                "duration_text": format_duration(length_sec),
            })

    # 상위 3개만 반환
    return results[:3]

# 사이드바: subject 선택 & 영상 선택
with st.sidebar:
    st.header("학습 준비")

    subjects = ["Python", "C", "Deep Learning", "LLM"]
    subject = st.selectbox(
        "주제 선택",
        subjects,
        index=subjects.index(st.session_state.selected_subject)
    )
    st.session_state.selected_subject = subject

    try:
        vids = fetch_top_videos(subject)
        st.caption("학습할 영상을 선택하세요.")

        options = []
        for i, v in enumerate(vids):
            # 썸네일 + 길이
            st.markdown(thumbnail_with_duration_html(v["id"], v["duration_text"]), unsafe_allow_html=True)
            st.markdown(f'<div class="video-title">{v["title"]}</div>', unsafe_allow_html=True)
            options.append(f"{i+1}. {v['title']} ({v['duration_text']})")

        if options:
            default_idx = 0 if st.session_state.selected_video_id is None else \
                next((i for i, v in enumerate(vids) if v["id"] == st.session_state.selected_video_id), 0)
            choice = st.radio("영상 선택", options, index=default_idx, label_visibility="collapsed")
            chosen_idx = options.index(choice)
            chosen_id = vids[chosen_idx]["id"]
            chosen_title = vids[chosen_idx]["title"]
        else:
            st.error("자막 기준(한국어 우선, 없으면 영어 / 자동 생성 제외)에 맞는 영상이 없습니다.")
            chosen_id, chosen_title = None, None
    except Exception as e:
        st.error(f"유튜브 API 오류: {e}")
        chosen_id, chosen_title = None, None

    if st.button("학습 시작"):
        st.session_state.selected_video_id = chosen_id
        st.session_state.selected_video_title = chosen_title

        # 선택한 영상 정보 저장 
        if chosen_id:
            save_selected_video(chosen_id, chosen_title)

            if chosen_id not in st.session_state.processed_video_ids:
                with st.spinner("선택한 영상 분석(osc) 실행 중..."):
                    try:
                        osc_main.main()
                        st.session_state.processed_video_ids.add(chosen_id)
                        st.success("영상 분석이 완료되었습니다.")
                    except Exception as e:
                        st.error(f"osc.main 실행 중 오류: {e}")

        if st.session_state["selected_video_id"]:
            st.session_state.learning_started = True

# 영상 선택
if not st.session_state.learning_started:
    st.info("👈 좌측 **사이드바**에서 주제를 고르고 영상 1개를 선택한 뒤 **[학습 시작]**을 눌러주세요.")
    if st.session_state.selected_video_id:
        st.markdown("### 선택 예정 영상 미리보기")
        render_video(st.session_state.selected_video_id, height=420)
    st.stop()

# 기존 main 페이지
col1, col2, col3 = st.columns([1.5, 3.5, 2])

with col1:
    st.markdown('<div class="section-title" style="margin-top: 20px;">챕터 목록</div>', unsafe_allow_html=True)
    if load_err:
        st.error(load_err)
    elif not titles:
        st.warning("표시할 챕터가 없습니다.")
    else:
        completed_set = set(st.session_state.completed_chapters)
        for i, t in enumerate(titles):
            completed = t in completed_set
            if st.button(f"📌 {t}", key=f"chapter_btn_{i}", use_container_width=True, disabled=completed):
                st.session_state.selected_title = t
                st.rerun()

with col2:
    st.markdown('<div class="section-title">추천 교육 영상</div>', unsafe_allow_html=True)

    seg_to_play = None
    if st.session_state.selected_title:
        for c in (it for it in segments if it.get("title") == st.session_state.selected_title):
            if c.get("start_sec") is not None and c.get("end_sec") is not None:
                seg_to_play = c
                break

    if seg_to_play and st.session_state.selected_video_id == "E6DuimPZDz8":
        render_video(
            video_id=st.session_state.selected_video_id,
            start=int(seg_to_play["start_sec"]),
            end=int(seg_to_play["end_sec"]),
            height=480
        )
    else:
        render_video(video_id=st.session_state.selected_video_id, height=480)

    st.markdown("---")
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
            st.warning("해당 챕터에 summary가 없습니다.")
    else:
        st.info("좌측에서 챕터를 선택하면 summary가 표시됩니다.")

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
