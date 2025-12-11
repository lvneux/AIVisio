"""
Semantic Segmentation을 이용한 자동 챕터 생성 (목표 챕터 수 범위 자동조정 포함)
- centroid 기반 주제 변화 감지
- 짧은 챕터 병합
- 영상 길이에 따른 목표 챕터 수 범위 산정 및 threshold 조정(반복 탐색)
"""

from typing import List, Tuple, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
from Backend.models.video_segment import VideoSegment

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ sentence-transformers가 설치되지 않았습니다. pip install sentence-transformers를 실행해주세요.")


def compute_target_chapter_range(video_duration: float) -> Tuple[int, int]:
    """
    영상 길이(초)에 따라 권장 챕터 수 범위를 반환합니다.
    (경험적 규칙 — 필요에 따라 조정하세요)
    """
    if not video_duration or video_duration <= 0:
        return (5, 20)

    minutes = video_duration / 60.0

    if minutes <= 1:
        return (1, 3)
    if minutes <= 3:
        return (3, 6)
    if minutes <= 7:
        return (5, 10)
    if minutes <= 12:
        return (8, 18)
    if minutes <= 30:
        return (12, 30)
    if minutes <= 60:
        return (20, 50)
    # 매우 긴 영상
    return (30, 80)


def group_transcripts_by_time(transcript_data, window_seconds: int = 60) -> List[Tuple[float, float, str]]:
    if not transcript_data:
        return []

    grouped_segments = []
    current_window_start = None
    current_window_texts = []
    current_window_end = None

    for idx, transcript in enumerate(transcript_data):
        start_time = float(transcript.start)
        end_time = float(transcript.start + transcript.duration)
        text = transcript.text.strip() if getattr(transcript, "text", None) else ""

        if current_window_start is None:
            current_window_start = start_time
            current_window_end = end_time

        current_window_texts.append(text)
        if current_window_end is not None:
            current_window_end = max(current_window_end, end_time)
        else:
            current_window_end = end_time

        is_last = (idx == len(transcript_data) - 1)
        if (current_window_end - current_window_start >= window_seconds) or is_last:
            combined_text = " ".join([t for t in current_window_texts if t])
            grouped_segments.append((current_window_start, current_window_end, combined_text))
            current_window_start = None
            current_window_end = None
            current_window_texts = []

    return grouped_segments


def calculate_embeddings(text_segments: List[str], model) -> np.ndarray:
    if not text_segments:
        return np.array([])
    embeddings = model.encode(text_segments, show_progress_bar=False)
    return np.array(embeddings)


def detect_topic_changes_centroid(embeddings: np.ndarray,
                                  similarity_threshold: float = 0.75,
                                  min_segment_len: int = 1) -> List[int]:
    n = len(embeddings)
    if n == 0:
        return []
    if n == 1:
        return [0, 0]

    change_points = [0]
    current_centroid = embeddings[0].astype(np.float64).copy()
    current_count = 1

    for i in range(1, n):
        sim = float(cosine_similarity(embeddings[i:i+1], current_centroid.reshape(1, -1))[0][0])
        if sim < similarity_threshold and current_count >= min_segment_len:
            change_points.append(i)
            current_centroid = embeddings[i].astype(np.float64).copy()
            current_count = 1
        else:
            current_count += 1
            current_centroid = (current_centroid * (current_count - 1) + embeddings[i]) / current_count

    if change_points[-1] != n - 1:
        change_points.append(n - 1)

    return change_points


def merge_short_segments(grouped_segments: List[Tuple[float, float, str]],
                         change_points: List[int],
                         min_duration: float = 15.0) -> List[Tuple[int, int]]:
    if not grouped_segments or not change_points:
        return []

    ranges = []
    for i in range(len(change_points) - 1):
        s_idx = change_points[i]
        e_idx = change_points[i + 1]
        ranges.append([s_idx, e_idx])

    i = 0
    while i < len(ranges):
        s_idx, e_idx = ranges[i]
        start_time = grouped_segments[s_idx][0]
        end_time = grouped_segments[e_idx][1]
        duration = end_time - start_time

        if duration < min_duration:
            if i == 0 and len(ranges) > 1:
                ranges[i + 1][0] = ranges[i][0]
                ranges.pop(i)
            elif i == len(ranges) - 1 and len(ranges) > 1:
                ranges[i - 1][1] = ranges[i][1]
                ranges.pop(i)
                i -= 1
            else:
                ranges[i - 1][1] = ranges[i][1]
                ranges.pop(i)
                i -= 1
        else:
            i += 1

    if not ranges:
        return [(0, len(grouped_segments) - 1)]

    merged = [(r[0], r[1]) for r in ranges]
    return merged


def generate_chapter_title(text: str, max_length: int = 50) -> str:
    if not text:
        return "Chapter"

    cleaned_text = text.strip()
    sentences = [s.strip() for s in cleaned_text.split('.') if s.strip()]
    if sentences:
        title = sentences[0]
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + "..."
        return title
    if len(cleaned_text) > max_length:
        return cleaned_text[:max_length].rsplit(' ', 1)[0] + "..."
    return cleaned_text


def create_semantic_segments(transcript_data,
                             video_id: str,
                             video_duration: Optional[float] = None,
                             initial_window_seconds: int = 60,
                             desired_min_duration: float = 15.0,
                             initial_similarity_threshold: float = 0.75,
                             max_adjust_iters: int = 6) -> List[VideoSegment]:
    """
    전체 파이프라인:
    1) 동적 window_seconds 결정(영상 길이에 따라)
    2) grouped_segments 생성
    3) 임베딩 계산 (한 번)
    4) threshold 조정 반복: detect_topic_changes_centroid -> merge_short_segments
       목표 챕터 범위(영상 길이 기반)에 들도록 similarity_threshold를 조정
    5) VideoSegment 리스트 반환
    """
    print("🔍 Semantic Segmentation (목표 챕터 범위 자동조정 포함) 시작")

    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        raise ImportError("sentence-transformers가 설치되어 있지 않습니다. pip install sentence-transformers")

    if not transcript_data:
        print("⚠️ 자막 데이터가 없습니다.")
        return []

    # 1) 동적 윈도우 계산 (video_duration이 있으면)
    window_seconds = initial_window_seconds
    if video_duration and video_duration > 0:
        # approximate chunk count: aim for chunk ~15~30초 내외 (clamp)
        approx_chunks = int(max(10, min(video_duration / 20, 120)))
        window_seconds = max(5, int(video_duration / approx_chunks))
        print(f"🔧 동적 윈도우 적용: window_seconds={window_seconds}s (approx_chunks={approx_chunks})")

    # 2) 그룹핑
    grouped_segments = group_transcripts_by_time(transcript_data, window_seconds)
    if not grouped_segments:
        print("⚠️ grouped_segments가 없습니다.")
        return []

    print(f"📊 초기 구간 수: {len(grouped_segments)}")

    # 3) 임베딩 계산 (한 번만)
    print("🤖 Embedding 모델 로딩 및 임베딩 계산 중...")
    model = None
    try:
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # type: ignore
    except Exception as e:
        print(f"⚠️ 다국어 모델 로드 실패: {e}. 영어 모델로 대체 시도.")
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')  # type: ignore
        except Exception as e2:
            print(f"❌ Embedding 모델 로드 실패: {e2}")
            return []
    
    if model is None:
        print("❌ Embedding 모델을 로드할 수 없습니다.")
        return []
    
    text_segments = [seg[2] for seg in grouped_segments]
    embeddings = calculate_embeddings(text_segments, model)
    if embeddings.size == 0:
        print("⚠️ 임베딩 계산 실패 또는 텍스트 비어있음")
        return []
    print(f"✅ {len(embeddings)} 임베딩 완료")

    # target chapter range 결정
    min_ch, max_ch = compute_target_chapter_range(video_duration) if video_duration else (5, 20)
    print(f"🎯 목표 챕터 범위: {min_ch} ~ {max_ch}")

    # 4) threshold 조정 루프
    lo_thresh = 0.55
    hi_thresh = 0.92
    best_result = None  # (num_segments, threshold, merged_ranges)
    best_diff = float('inf')

    # 시작 threshold
    thresh = initial_similarity_threshold

    for it in range(max_adjust_iters):
        change_points = detect_topic_changes_centroid(embeddings, similarity_threshold=thresh, min_segment_len=1)
        merged_ranges = merge_short_segments(grouped_segments, change_points, min_duration=desired_min_duration)
        num_segments = len(merged_ranges)

        print(f"  반복 {it+1}: threshold={thresh:.3f} -> segments={num_segments}")

        # 목표 범위 내이면 바로 채택
        if min_ch <= num_segments <= max_ch:
            best_result = (num_segments, thresh, merged_ranges)
            print("✅ 목표 범위 내에 들었습니다.")
            break

        # 가장 근접한 결과 저장
        diff = min(abs(num_segments - min_ch), abs(num_segments - max_ch))
        if diff < best_diff:
            best_diff = diff
            best_result = (num_segments, thresh, merged_ranges)

        # threshold 조정 전략:
        # - segments가 너무 많으면(과분할): threshold 낮춰서 병합을 유도 (sim < thresh 가 분할 조건이므로 낮추면 덜 분할)
        # - segments가 너무 적으면(과소분할): threshold 높여서 더 분할
        if num_segments > max_ch:
            # 너무 많음 -> 낮춰야 함
            hi_thresh = thresh
            thresh = (thresh + lo_thresh) / 2.0
        elif num_segments < min_ch:
            # 너무 적음 -> 높여야 함
            lo_thresh = thresh
            thresh = (thresh + hi_thresh) / 2.0

    if best_result is None:
        print("⚠️ 목표 범위에 도달하지 못했지만 가장 근접한 결과를 사용합니다.")
        # fallback: compute once more with initial threshold if none
        change_points = detect_topic_changes_centroid(embeddings, similarity_threshold=initial_similarity_threshold, min_segment_len=1)
        merged_ranges = merge_short_segments(grouped_segments, change_points, min_duration=desired_min_duration)
        best_result = (len(merged_ranges), initial_similarity_threshold, merged_ranges)

    final_num, final_thresh, final_ranges = best_result
    print(f"🔚 최종 선택: threshold={final_thresh:.3f}, 챕터수={final_num}")

    # 5) VideoSegment 객체 생성
    video_segments: List[VideoSegment] = []
    for i, (s_idx, e_idx) in enumerate(final_ranges):
        seg_start = grouped_segments[s_idx][0]
        seg_end = grouped_segments[e_idx][1]
        segment_texts = [grouped_segments[j][2] for j in range(s_idx, e_idx + 1)]
        combined_text = " ".join([t for t in segment_texts if t])
        chapter_title = generate_chapter_title(combined_text, max_length=50)

        segment = VideoSegment(
            id=f"{video_id}_seg_{i}",
            video_id=video_id,
            title=chapter_title,
            start_time=seg_start,
            end_time=seg_end,
            subtitles=combined_text,
            tags=[],
            keywords=[],
            summary=(combined_text[:200] + "...") if len(combined_text) > 200 else combined_text,
            cognitive_level="Unknown",
            dok_level="Unknown"
        )
        video_segments.append(segment)
        print(f"   - 생성: {chapter_title} ({seg_start:.1f}s - {seg_end:.1f}s)")

    print(f"✅ 총 {len(video_segments)}개의 챕터 생성 완료 (threshold={final_thresh:.3f})")
    return video_segments
