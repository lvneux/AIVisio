"""
세그먼트 처리 관련 함수들
"""

import re
from typing import List, Optional
from osc.models.video_segment import VideoSegment
from .utils import time_str_to_seconds, seconds_to_time_str


def segment_video_by_description(video_id: str, description: str) -> Optional[List[VideoSegment]]:
    """
    비디오 설명에서 시간 표시된 세그먼트를 파싱하여 VideoSegment 객체 리스트를 반환합니다.

    설명에는 구분자(예: "=====")가 있어야 하며, 각 세그먼트 라인은 시간 문자열과 제목으로 시작해야 합니다.

    Args:
        video_id (str): 비디오 ID
        description (str): 전체 비디오 설명 (소개 텍스트와 세그먼트 마커 포함)

    Returns:
        Optional[List[VideoSegment]]: 파싱된 세그먼트 리스트 (제목, 시간 범위, 메타데이터 포함)
    """
    # 설명을 컨텍스트와 세그먼트로 분할
    parts = re.split(r"=+", description) 
    description_context = parts[0].strip() if len(parts) > 1 else ""
    segment_lines = parts[1].strip().splitlines() if len(parts) > 1 else description.strip().splitlines()

    # 시간 표시된 세그먼트와 태그를 위한 정규식 패턴 정의
    segment_pattern = r"\s*(\d{1,2}:\d{2})\s*[|\-]?\s*(.+)"
    # tag_pattern = r"#(\w+)"

    matches = []
    for line in segment_lines:
        match = re.match(segment_pattern, line)
        if match:
            matches.append((match.group(1), match.group(2).strip()))

    # 세그먼트를 찾지 못한 경우 None 반환
    if not matches:
        print("⚠️ 설명에서 세그먼트를 찾을 수 없습니다.")
        return None
    else:
        print(f"✅ 설명에서 {len(matches)}개의 세그먼트를 찾았습니다.")

    segments = []
    for idx, (start_str, title) in enumerate(matches):
        start_sec = time_str_to_seconds(start_str)
        end_sec = time_str_to_seconds(matches[idx + 1][0]) if idx + 1 < len(matches) else start_sec + 90.0

        clean_title = title.strip()

        seg = VideoSegment(
            id=f"{video_id}_seg_{idx}",
            video_id=video_id,
            title=clean_title,
            start_time=start_sec,
            subtitles="",
            tags=[],
            keywords=[],
            end_time=end_sec,
            summary=description_context,
            cognitive_level="Understand",
            dok_level="Level 2"
        )
        segments.append(seg)
        print(f"📌 세그먼트 {idx}: {clean_title} ({seconds_to_time_str(start_sec)} - {seconds_to_time_str(end_sec)})")

    return segments


def map_subtitles_to_segments(segments: List[VideoSegment], transcript_data) -> List[VideoSegment]:
    """
    세그먼트에 해당하는 자막을 매핑합니다.
    
    Args:
        segments: 세그먼트 리스트
        transcript_data: 자막 데이터
    
    Returns:
        자막이 매핑된 세그먼트 리스트
    """
    print(f"🔗 자막 매핑 시작...")
    
    for segment in segments:
        segment_subtitles = []
        
        # 세그먼트 시간 범위에 해당하는 자막 찾기
        for subtitle in transcript_data:
            subtitle_start = subtitle.start
            subtitle_end = subtitle.start + subtitle.duration
            
            # 자막이 세그먼트 시간 범위와 겹치는지 확인
            if (subtitle_start < segment.end_time and subtitle_end > segment.start_time):
                segment_subtitles.append(subtitle.text)
        
        # 매핑된 자막을 세그먼트에 저장
        segment.subtitles = " ".join(segment_subtitles)
        print(f"   📌 {segment.title}: {len(segment_subtitles)}개 자막 매핑됨")
    
    return segments 