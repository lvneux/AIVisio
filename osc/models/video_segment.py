"""
데이터 모델 및 클래스 정의
"""

from dataclasses import dataclass
from typing import List


@dataclass
class VideoSegment:
    """비디오 세그먼트를 나타내는 데이터 클래스"""
    id: str
    video_id: str
    title: str
    start_time: float
    end_time: float
    subtitles: str
    tags: List[str]
    keywords: List[str]
    summary: str
    cognitive_level: str
    dok_level: str 