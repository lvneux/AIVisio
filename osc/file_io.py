"""
파일 입출력 관련 함수들
"""

import json
import os
from datetime import datetime
from typing import List
from models import VideoSegment
from utils import seconds_to_time_str


def ensure_output_dir():
    """output 폴더가 존재하는지 확인하고 없으면 생성합니다."""
    output_dir = './output'
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_segments_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    세그먼트 정보를 JSON 파일로 저장합니다.
    """
    output_dir = ensure_output_dir()
    
    if output_path is None:
        output_path = f'{output_dir}/{video_id}_segments.json'
    
    segments_data = {
        "video_id": video_id,
        "total_segments": len(segments),
        "extraction_time": str(datetime.now()),
        "segments": []
    }
    
    for segment in segments:
        segment_dict = {
            "id": segment.id,
            "title": segment.title,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "start_time_formatted": seconds_to_time_str(segment.start_time),
            "end_time_formatted": seconds_to_time_str(segment.end_time),
            "duration": segment.end_time - segment.start_time,
            "summary": segment.summary,
            "cognitive_level": segment.cognitive_level,
            "dok_level": segment.dok_level,
            "tags": segment.tags,
            "keywords": segment.keywords
        }
        segments_data["segments"].append(segment_dict)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 세그먼트 JSON 저장 완료: {output_path}")


def save_segments_to_txt(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    세그먼트 정보를 읽기 쉬운 TXT 파일로 저장합니다.
    """
    output_dir = ensure_output_dir()
    
    if output_path is None:
        output_path = f'{output_dir}/{video_id}_segments.txt'
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== 비디오 세그먼트 정보 ===\n")
        f.write(f"비디오 ID: {video_id}\n")
        f.write(f"총 세그먼트 수: {len(segments)}개\n")
        f.write(f"추출 시간: {datetime.now()}\n\n")
        
        for i, segment in enumerate(segments, 1):
            start_time = seconds_to_time_str(segment.start_time)
            end_time = seconds_to_time_str(segment.end_time)
            duration = segment.end_time - segment.start_time
            
            f.write(f"📌 세그먼트 {i}\n")
            f.write(f"⏰ 시간: {start_time} ~ {end_time}\n")
            f.write(f"📝 제목: {segment.title}\n")
            f.write(f"⏱️  지속시간: {duration:.1f}초\n")
            f.write(f"📄 자막: {segment.subtitles[:200]}{'...' if len(segment.subtitles) > 200 else ''}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"✅ 세그먼트 TXT 저장 완료: {output_path}")


def save_segments_with_subtitles_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    자막이 매핑된 세그먼트 정보를 JSON 파일로 저장합니다.
    """
    output_dir = ensure_output_dir()
    
    if output_path is None:
        output_path = f'{output_dir}/{video_id}_segments_with_subtitles.json'
    
    segments_data = {
        "video_id": video_id,
        "total_segments": len(segments),
        "extraction_time": str(datetime.now()),
        "segments": []
    }
    
    for segment in segments:
        segment_dict = {
            "id": segment.id,
            "title": segment.title,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "start_time_formatted": seconds_to_time_str(segment.start_time),
            "end_time_formatted": seconds_to_time_str(segment.end_time),
            "duration": segment.end_time - segment.start_time,
            "summary": segment.summary,
            "subtitles": segment.subtitles,
            "tags": segment.tags,
            "keywords": segment.keywords
        }
        segments_data["segments"].append(segment_dict)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 자막 매핑된 세그먼트 JSON 저장 완료: {output_path}") 