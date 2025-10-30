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
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# .env 파일 로드
load_dotenv(ROOT_DIR / ".env")

from Backend import main as backend_main # Backend > main.py 호출

API_KEY = os.getenv("YOUTUBE_API_KEY", "")

st.set_page_config(page_title="AIVisio", layout="wide")

# 선택한 영상 정보를 Backend/output/selected_video.json에 저장
def save_selected_video(video_id: str, video_title: str | None = None):
    try:
        root_dir = Path(__file__).resolve().parents[1] # 프로젝트 루트
        output_dir = root_dir / "Backend" / "output"
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
def load_segments(video_id: str | None):
    if not video_id:
        return [], "video_id가 지정되지 않았습니다."
    
    try:
        root_dir = Path(__file__).resolve().parents[1]
        output_dir = root_dir / "Backend" / "output"

        # 1. 원본 파일 경로 (e.g., ..._segments_with_subtitles.json)
        original_path = output_dir / f"{video_id}_segments_with_subtitles.json"
        
        json_path_to_load = None

        if original_path.exists():
            # 1.1. 원본 파일이 있으면 사용
            json_path_to_load = original_path
        else:
            # 2. 원본 파일이 없으면, 언어 코드가 붙은 파일 검색 (e.g., ..._en.json)
            # 패턴: {video_id}_segments_with_subtitles_*.json
            pattern = f"{video_id}_segments_with_subtitles_*.json"
            
            # output 디렉토리에서 패턴에 맞는 파일 검색
            found_files = list(output_dir.glob(pattern))
            
            if found_files:
                # 2.1. 찾았으면 첫 번째 파일 사용
                json_path_to_load = found_files[0]
            else:
                # 3. 두 경우 모두 실패하면 에러 발생
                raise FileNotFoundError(
                    f"'{original_path.name}' 파일을 찾을 수 없습니다. "
                    f"또한 '{pattern}' 패턴의 파일도 찾을 수 없습니다."
                )

        # 찾은 파일 로드
        with open(json_path_to_load, "r", encoding="utf-8") as f:
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
            # [수정] bloom_category 필드 추가
            bloom_category = it.get("bloom_category")
            if title is not None:
                cleaned.append({
                    "title": str(title),
                    "summary": summary,
                    "start_sec": s_sec,
                    "end_sec": e_sec,
                    "bloom_category": bloom_category # <-- ADDED
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

def display_loading_overlay():
    st.markdown(
        """
        <style>
            .custom-loading-overlay {
                position: fixed;
                inset: 0;
                background: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                margin: 0; padding: 0;
                width: 100%; height: 100%;
            }
            .loader-wrap {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 16px;
            }
            /* 점프하는 점 3개 */
            .dots {
                display: flex;
                gap: 10px;
                height: 12px;
            }
            .dot {
                width: 10px;
                height: 10px;
                background: #4f46e5;
                border-radius: 50%;
                animation: bounce 1.2s infinite ease-in-out;
            }
            .dot:nth-child(2) { animation-delay: 0.2s; }
            .dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes bounce {
                0%, 80%, 100% { transform: translateY(0); opacity: .6; }
                40% { transform: translateY(-8px); opacity: 1; }
            }

            .loading-text {
                font-size: 14px;
                color: #475569;
                user-select: none;
            }
        </style>
        <div class="custom-loading-overlay">
            <div class="loader-wrap">
                <div class="dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <div class="loading-text">영상 분석 중입니다…</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------ 스타일 ------------------
st.markdown("""
    <style>
    /* 기본 UI 스타일 */
    .section-title { font-size: 20px !important; font-weight: 600; margin-bottom: 8px; }
    label[for="memo"] > div:first-child { display: none; }
    .video-title { font-size: 12px; font-weight: 600; line-height: 1.1; margin: 4px 0 6px; }

    /* 챕터 목록 비활성화 버튼 스타일 (회색) */
    button[disabled][data-testid="baseButton-secondary"]{
        background: #f1f3f5 !important;
        border-color: #e9ecef !important;
        color: #adb5bd !important;
        opacity: 1;
        cursor: not-allowed !important;
        filter: none !important; 
        transform: none !important;
    }
    button[disabled][data-testid="baseButton-secondary"]:hover{
        filter: none !important; transform: none !important;
    }

    /* 챕터 목록 버튼 스타일 */
    div[data-testid="stColumn"] button[data-testid="baseButton-secondary"] {
        border-color: #ccc;
        background-color: white;
        color: #333;
    }
    div[data-testid="stColumn"] button[data-testid="baseButton-secondary"]:hover:not([disabled]) {
        background-color: #f0f0f0;
        border-color: #aaa;
    }

    /* 썸네일 카드 */
    .thumb-wrap { position: relative; width: 100%; border-radius: 8px; overflow: hidden; background: #000; }
    .thumb-inner { position: relative; width: 100%; padding-bottom: 50%; background-size: cover; background-position: center; background-repeat: no-repeat; }
    .duration-badge {
        position: absolute; right: 6px; bottom: 6px;
        background: rgba(0,0,0,0.75); color: #fff;
        padding: 2px 6px; border-radius: 4px;
        font-size: 12px; font-weight: 600; line-height: 1;
    }

    /* 페이지 네비게이션 숨김 */
    div[data-testid="stSidebarNav"] { display: none !important; }

    /* ---------- 사이드바 영상 선택 카드 ---------- */
    [data-testid="stSidebar"] .pick-row {
        border: 1.5px solid transparent;
        border-radius: 10px;
        padding: 8px 10px;
        margin-bottom: 10px;
        background: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    [data-testid="stSidebar"] .pick-row:hover {
        border-color: transparent !important;
        background: transparent !important;
        cursor: default !important;
    }

    /* ---- 왼쪽 선택 버튼 정사각형 설정 ---- */
    [data-testid="stSidebar"] .pick-row > div:first-child .stElementContainer,
    [data-testid="stSidebar"] .pick-row > div:first-child .element-container {
        width: 60px !important;
        height: 60px !important;
        box-sizing: border-box !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* 버튼 래퍼도 정사각형으로 */
    [data-testid="stSidebar"] .pick-row > div:first-child .stButton {
        width: 60px !important;
        height: 60px !important;
        box-sizing: border-box !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* 실제 버튼 디자인 */
    [data-testid="stSidebar"] .pick-row .stButton > button {
        width: 60px !important;
        height: 60px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        border: 2px solid #b6b6b6 !important;
        box-sizing: border-box !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 20px !important;
        line-height: 1 !important;
        background: white !important;
        color: transparent !important; /* 기본 상태에서 V 숨김 */
    }

    /* 선택된 상태 강조 */
    [data-testid="stSidebar"] .pick-row.selected .stButton > button {
        border-color: #ef9a9a !important;
        background: #fff0f0 !important;
        color: #111 !important; /* 선택 시 V 표시 */
    }

    /* 왼쪽 컬럼 최소 너비 */
    [data-testid="stSidebar"] .pick-row .stColumn:first-child {
        min-width: 56px !important;
        padding-right: 8px !important;
        box-sizing: border-box !important;
    }

    /* 학습 시작 버튼 중앙 정렬 */
    .center-wrap { display: flex; justify-content: center; margin-top: 20px; }
    .center-wrap button { width: auto; padding: 10px 20px; font-size: 16px; }

    /* 포커스 시 outline 제거 */
    [data-testid="stSidebar"] .stButton > button:focus { outline: none !important; box-shadow: none !important; }

    /* 챕터 제목 강조 */
    .chapter-concept-title { font-size: 21px; font-weight: 600; line-height: 1.2; margin-top: 0; margin-bottom: 0; display: flex; align-items: center; height: 100%;}

    /* 블룸 단계 버튼 스타일 */
    .stage-button-style button {
        border-color: #ced4da !important;
        background-color: #f8f9fa !important;
        color: #343a40 !important;
        margin-bottom: 5px;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stage-button-style.selected button {
        border-color: #007bff !important;
        background-color: #e9f5ff !important;
        color: #007bff !important;
        font-weight: bold;
    }
    .stage-button-style button:hover:not([disabled]) {
        background-color: #e2e6ea !important;
    }

    /* 챕터 목록과 단계 버튼 간격 */
    .section-title { margin-top: 0px !important; }

    /* 가로 버튼 간 여백 제거 */
    div[data-testid="stHorizontalBlock"] .stage-button-style {
        margin-bottom: 0 !important; 
    }
    </style>
""", unsafe_allow_html=True)



# ------------------ 상태 초기화 ------------------
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
    st.session_state.selected_subject = "Deep Learning"
if "processed_video_ids" not in st.session_state:
    st.session_state.processed_video_ids = set()
# (추가) 사이드바 단일 선택 인덱스 상태
if "video_choice_idx" not in st.session_state:
    st.session_state.video_choice_idx = 0
# [추가] 선택된 블룸 단계 상태
if "selected_bloom_stage" not in st.session_state:
    st.session_state.selected_bloom_stage = None # "기억", "이해", "적용", "분석", "평가", "창조"
# [추가] 영상 분석 중 상태
if "is_analyzing" not in st.session_state:
    st.session_state.is_analyzing = False


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

# 자막 체크: 한국어 우선, 없으면 영어 / 자동 생성 자막 제외 -> 조건 생략 중
def has_pref_transcript(video_id: str) -> bool:
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)

        has_manual_ko = False
        has_manual_en = False

        for t in tl:
            if not t.is_generated: # 반드시 수동 자막만
                if t.language_code.startswith("ko"):
                    has_manual_ko = True
                    break # 한국어 수동 자막 있으면 바로 True 반환
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

        # 영상 길이 (10~30분) 필터
        if 600 <= length_sec <= 1800:
            results.append({
                "id": vid,
                "title": title,
                "duration_sec": length_sec,
                "duration_text": format_duration(length_sec),
            })

    # 상위 3개만 반환
    return results[:3]

# ------------------ 사이드바 (디자인 적용) ------------------
with st.sidebar:
    st.header("학습 준비")

    subjects = ["Python", "C", "Deep Learning", "LLM"]
    subject = st.selectbox(
        "주제 선택",
        subjects,
        index=subjects.index(st.session_state.selected_subject)
    )
    # 주제가 바뀌면 선택 인덱스 초기화
    if subject != st.session_state.selected_subject:
        st.session_state.video_choice_idx = 0
        st.session_state.selected_video_id = None
        st.session_state.selected_video_title = None
    st.session_state.selected_subject = subject

    try:
        vids = fetch_top_videos(subject)
        st.caption("학습할 영상 1개를 선택하세요.")

        if not vids:
            st.error("자막 기준(한국어 우선, 없으면 영어 / 자동 생성 제외)에 맞는 영상이 없습니다.")
            chosen_id, chosen_title = None, None
        else:
            # 현재 선택 인덱스 보정
            if st.session_state.video_choice_idx >= len(vids):
                st.session_state.video_choice_idx = 0

            # 각 항목을 카드형으로 렌더링 (버튼+썸네일+제목)
            for i, v in enumerate(vids):
                
                # selected 상태를 먼저 파악
                selected = (i == st.session_state.video_choice_idx)
                
                # div에 .selected 클래스 동적 할당
                class_name = "pick-row selected" if selected else "pick-row"
                st.markdown(f'<div class="{class_name}">', unsafe_allow_html=True)
                
                # 왼쪽 버튼 컬럼을 충분히 넓혀 정사각 버튼이 잘 보이도록 조정
                left, right = st.columns([2.0, 11.5], vertical_alignment="top")

                # 좌측 '선택' 버튼
                with left:
                    label = "V" if selected else ""
                    if st.button(label, key=f"pick_btn_{i}", help="클릭하여 영상 선택"):
                        st.session_state.video_choice_idx = i
                        st.session_state.selected_bloom_stage = None # 영상 변경 시 필터 초기화
                        st.rerun()
                
                # 우측 썸네일 + 제목
                with right:
                    st.markdown(
                        thumbnail_with_duration_html(v["id"], v["duration_text"]),
                        unsafe_allow_html=True
                    )
                    st.markdown(f'<div class="video-title">{v["title"]}</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            # 최종 선택값
            chosen_id = vids[st.session_state.video_choice_idx]["id"]
            chosen_title = vids[st.session_state.video_choice_idx]["title"]

    except Exception as e:
        st.error(f"유튜브 API 오류: {e}")
        chosen_id, chosen_title = None, None

    # 학습 시작 버튼: 가운데 정렬
    st.markdown('<div class="center-wrap">', unsafe_allow_html=True)
    start_clicked = st.button("학습 시작")
    st.markdown('</div>', unsafe_allow_html=True)

    if start_clicked:
        # 선택한 영상 정보 저장 
        if chosen_id:
            st.session_state.selected_video_id = chosen_id
            st.session_state.selected_video_title = chosen_title
            save_selected_video(chosen_id, chosen_title)

            if chosen_id not in st.session_state.processed_video_ids:
                # 기존 분석 결과 파일이 있으면 스킵 (원본 또는 언어 변형 파일)
                output_dir = ROOT_DIR / "Backend" / "output"
                base_file = output_dir / f"{chosen_id}_segments_with_subtitles.json"
                pattern_files = list(output_dir.glob(f"{chosen_id}_segments_with_subtitles_*.json"))
                if base_file.exists() or len(pattern_files) > 0:
                    st.info("이미 분석된 영상입니다. 기존 결과를 사용합니다.")
                    st.session_state.processed_video_ids.add(chosen_id)
                else:
                    # 커스텀 로딩 화면을 띄우기 위해 상태 변경 후 재실행
                    st.session_state.is_analyzing = True
                    st.rerun() # 재실행하여 로딩 화면을 먼저 띄우고 분석 시작

            # 분석이 이미 완료되었거나, 새로 시작할 경우 학습 시작 상태로 전환
            st.session_state.learning_started = True
            # 이미 처리된 영상이면, 메인 화면으로 전환
            if chosen_id in st.session_state.processed_video_ids:
                st.rerun()
        else:
            st.error("영상을 먼저 선택해주세요.")
            
# --- [추가] 영상 분석 로직 (is_analyzing 상태에서만 실행) ---
# 이 블록은 로딩 화면을 띄운 상태에서 블로킹 작업을 수행합니다.
if st.session_state.is_analyzing:
    # 1. 로딩 오버레이 표시 (애니메이션이 시작됨)
    display_loading_overlay() 
    
    chosen_id = st.session_state.selected_video_id
    
    # 선택된 영상 ID가 있고, 아직 처리되지 않은 경우에만 분석 실행
    if chosen_id and chosen_id not in st.session_state.processed_video_ids:
        # 재확인: 결과 파일 존재 시 즉시 스킵
        output_dir = ROOT_DIR / "Backend" / "output"
        base_file = output_dir / f"{chosen_id}_segments_with_subtitles.json"
        pattern_files = list(output_dir.glob(f"{chosen_id}_segments_with_subtitles_*.json"))
        if base_file.exists() or len(pattern_files) > 0:
            st.session_state.processed_video_ids.add(chosen_id)
            st.session_state.is_analyzing = False
            st.rerun()
        try:
            # 2. blocking task 실행 (이 동안 브라우저는 CSS 애니메이션 표시)
            # st.info("영상 분석 중입니다. 잠시만 기다려 주세요...") # 이 메시지를 추가하면 디버깅에 도움이 될 수 있습니다.
            backend_main.main(video_id=chosen_id) 
            
            # 3. 분석 완료 후 상태 업데이트
            st.session_state.processed_video_ids.add(chosen_id)
            st.session_state.is_analyzing = False
            st.session_state.learning_started = True 
            st.session_state.selected_video_id = chosen_id  
            st.session_state.selected_video_title = st.session_state.get("selected_video_title", "")
            st.rerun()  

            
        except Exception as e:
            # 3. 분석 실패 시 상태 업데이트
            st.session_state.is_analyzing = False
            st.session_state.learning_started = False
            st.error(f"Backend.main 실행 중 오류: {e}")
            st.stop() # 에러 발생 시 재실행 방지
    else:
        # chosen_id가 없거나 이미 처리된 경우 (예외 상황 대비)
        st.session_state.is_analyzing = False
        st.rerun()


# ------------------ 메인 화면 ------------------
# [수정] 영상 선택 / 분석 중 상태 확인
if st.session_state.is_analyzing:
    # 분석 중일 때는 메인 화면 렌더링을 중단
    st.stop()
    
if not st.session_state.learning_started:
    st.info("좌측 사이드바에서 주제를 고르고 영상 1개를 선택한 뒤 [학습 시작]을 눌러주세요.")
    # '선택 예정 영상 미리보기' 화면과 관련된 코드를 주석 처리하여 제거함 (요청 사항 반영)
    # if st.session_state.selected_video_id:
    #     st.markdown("선택 예정 영상 미리보기")
    #     render_video(st.session_state.selected_video_id, height=420)
    st.stop()
    
segments, load_err = load_segments(st.session_state.selected_video_id)
# 챕터 제목은 중복 제거 후 순서 유지
titles = unique_preserve_order([item["title"] for item in segments]) if segments else []
# 챕터 제목별 Bloom category 매핑 (첫 번째 세그먼트를 대표로 사용)
title_to_bloom = {
    item["title"]: item["bloom_category"]
    for item in segments
    if item.get("bloom_category") is not None
}


# [수정] 블룸 인지 단계 버튼 위에 '학습 단계' 제목 추가
st.markdown('<div class="section-title" style="margin-bottom: 5px;">학습 단계</div>', unsafe_allow_html=True)

# [수정] 블룸 인지 단계 버튼을 챕터 목록 위에 가로로 나열
bloom_stages = [
    ("1단계: 기억", "기억"),
    ("2단계: 이해", "이해"),
    ("3단계: 적용", "적용"),
    ("4단계: 분석", "분석"),
    ("5단계: 평가", "평가"),
    ("6단계: 창조", "창조")
]

# 6개의 컬럼을 생성하여 버튼을 가로로 나열
cols_bloom = st.columns(6) 
for i, (full_text, category_name) in enumerate(bloom_stages):
    is_selected = st.session_state.selected_bloom_stage == category_name
    btn_key = f"bloom_btn_horizontal_{category_name}"
    
    with cols_bloom[i]:
        # 커스텀 스타일 적용을 위한 HTML 래퍼 (기존 스타일 패턴 유지)
        class_name = "stage-button-style selected" if is_selected else "stage-button-style"
        st.markdown(f'<div class="{class_name}" id="wrap_{btn_key}">', unsafe_allow_html=True)
        
        # Streamlit 버튼 생성
        if st.button(full_text, key=btn_key, use_container_width=True):
            # 선택된 버튼을 다시 누르면 초기화 (None으로 돌아감)
            st.session_state.selected_bloom_stage = category_name if not is_selected else None
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True) # HTML 래퍼 닫기

st.markdown('<div style="margin-bottom: 10px;"></div>', unsafe_allow_html=True) # 추가적인 간격 조정 (없애면 딱 붙음)
st.markdown("---") 

# 기존 main 페이지
col1, col2, col3 = st.columns([1.5, 3.5, 2])

with col1:
    # 1. 챕터 목록 
    st.markdown('<div class="section-title">챕터 목록</div>', unsafe_allow_html=True)
    if load_err:
        st.error(load_err)
    elif not titles:
        st.warning("표시할 챕터가 없습니다.")
    else:
        completed_set = set(st.session_state.completed_chapters)
        
        # [추가] Bloom filter 적용
        filtered_titles = []
        target_bloom = st.session_state.selected_bloom_stage
        
        for t in titles:
            bloom_cat = title_to_bloom.get(t)
            # 1) 필터가 선택되지 않았거나 (None)
            # 2) 챕터에 bloom_category 정보가 없거나
            # 3) 챕터의 bloom_category가 선택된 필터와 일치하면 포함
            if target_bloom is None or bloom_cat is None or bloom_cat == target_bloom:
                 filtered_titles.append(t)
        
        # 챕터 버튼 렌더링
        for i, t in enumerate(titles):
            completed = t in completed_set
            
            # [수정] 필터링: 선택된 필터(target_bloom)와 챕터의 카테고리가 일치하는 경우만 활성화
            bloom_cat = title_to_bloom.get(t)
            
            # 필터가 선택되었고, 챕터의 카테고리가 필터와 일치하지 않으면 비활성화
            # 다만, 완료된 챕터는 필터와 관계없이 비활성화
            is_filtered_out = target_bloom is not None and bloom_cat != target_bloom
            disabled = completed or is_filtered_out
            
            
            if st.button(f"▶ {t}", key=f"chapter_btn_{i}", use_container_width=True, disabled=disabled):
                # 활성화된 버튼만 클릭 이벤트 발생 (disabled=False)
                if not disabled:
                    st.session_state.selected_title = t
                    st.rerun()


with col2:
    st.markdown('<div class="section-title">추천 교육 영상</div>', unsafe_allow_html=True)

    seg_to_play = None
    if st.session_state.selected_title:
        # 선택된 챕터의 세그먼트를 찾음
        for c in (it for it in segments if it.get("title") == st.session_state.selected_title):
            if c.get("start_sec") is not None and c.get("end_sec") is not None:
                seg_to_play = c
                break

    if seg_to_play and seg_to_play.get("start_sec") is not None and seg_to_play.get("end_sec") is not None:
        render_video(
            video_id=st.session_state.selected_video_id,
            start=int(seg_to_play["start_sec"]),
            end=int(seg_to_play["end_sec"]),
            height=480
        )
    else:
        # 선택된 챕터가 없으면 전체 영상 재생
        render_video(video_id=st.session_state.selected_video_id, height=480)

    st.markdown("---")
    if st.session_state.selected_title:
        # 선택된 챕터의 세그먼트들(요약 포함)을 가져오면서 블룸 단계 표시
        matched_segments = [
            it for it in segments
            if it.get("title") == st.session_state.selected_title and it.get("summary")
        ]
        if matched_segments:
            # 영어/철자 변형 → (단계번호, 한국어라벨) 매핑
            bloom_map = {
                "Remember": (1, "기억"),
                "Understand": (2, "이해"),
                "Apply": (3, "적용"),
                "Analyse": (4, "분석"),
                "Analyze": (4, "분석"),
                "Evaluate": (5, "평가"),
                "Create": (6, "창조"),
            }
            for idx, it in enumerate(matched_segments, start=1):
                cat = (it.get("bloom_category") or "").strip()
                stage, ko_label = bloom_map.get(cat, (None, None))
                exp_label = "요약 보기"
                if stage and ko_label:
                    exp_label = f"요약 보기 (블룸 단계 {stage}: {ko_label})"
                elif cat:
                    exp_label = f"요약 보기 (블룸: {cat})"
                with st.expander(exp_label, expanded=(len(matched_segments) == 1)):
                    st.markdown(str(it.get("summary", "")).replace("\n", " \n"))
        else:
            st.warning("해당 챕터에 요약 내용이 없습니다.")
    else:
        # [수정] 텍스트 변경
        st.info("단계별로 학습하세요. 챕터를 선택하면 관련 퀴즈를 풀 수 있습니다.")
        
    st.markdown("---")

    key_concepts = [st.session_state.selected_title] if st.session_state.selected_title else []
    for concept in key_concepts:
        
        col_concept, col_button = st.columns([4, 1.6], vertical_alignment="center")

        col_concept.markdown(f'<div class="chapter-concept-title">• {concept}</div>', unsafe_allow_html=True)
        
        if col_button.button("관련 문제 풀기", key=f"concept_quiz_{concept}", use_container_width=True):
            st.session_state.quiz_title = concept
            # 퀴즈 페이지로 이동 로직
            try:
                st.switch_page("pages/quiz_page.py")
            except Exception:
                # switch_page가 없을 경우 쿼리 파라미터로 대체 (Streamlit 버전 호환성)
                st.experimental_set_query_params(quiz_title=concept)
                st.rerun()

with col3:
    st.markdown('<div class="section-title">✏️ 학습 메모</div>', unsafe_allow_html=True)
    memo_text = st.text_area("memo", placeholder="학습 내용을 메모하세요.", height=300, label_visibility="collapsed")

    st.markdown('<div class="section-title">💾 메모 저장</div>', unsafe_allow_html=True)
    filename = st.text_input("저장 파일명 (확장자 제외)", value=f"memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # PDF를 제거하고 워드 파일(.doc) 옵션 추가
    file_format = st.radio(
        "파일 형식 선택", 
        ["txt", "doc"], 
        format_func=lambda x: "워드 파일 (*.doc)" if x == "doc" else "텍스트 파일 (*.txt)"
    )

    if st.button("저장하기"):
        if memo_text.strip() == "":
            st.error("메모 내용이 비어 있습니다.")
        else:
            if file_format == "txt":
                filepath = f"{filename}.txt"
                mime_type = "text/plain"
            elif file_format == "doc":
                # 워드 파일 (.doc)로 저장 (단순 텍스트를 .doc으로 저장하여 Word에서 열리도록 함)
                filepath = f"{filename}.doc"
                mime_type = "application/msword"
            
            # 파일 저장
            try:
                # Streamlit 환경에서는 파일을 로컬에 쓰는 대신, 바로 다운로드 스트림에 제공하는 것이 일반적
                # 하지만, 원본 코드가 로컬 파일 저장을 시도하므로, 해당 로직을 유지하고 다운로드 버튼으로 연결
                
                # 메모리에서 인코딩
                if file_format == "txt":
                    data_to_download = memo_text.encode("utf-8")
                elif file_format == "doc":
                    # .doc 포맷은 복잡하지만, 여기서는 단순 텍스트를 .doc으로 저장하는 원본 로직을 따름
                    data_to_download = memo_text.encode("utf-8")
                    
                st.download_button(
                    "📥 메모 파일 다운로드",
                    data=data_to_download,
                    file_name=filepath,
                    mime=mime_type
                )
                st.success("메모 파일이 준비되었습니다. 다운로드 버튼을 눌러주세요.")
            except Exception as e:
                st.error(f"파일 처리 중 오류: {e}")
