"""
파일 입출력 관련 함수들
"""

import json
import os
from datetime import datetime
from typing import List
from Backend.models.video_segment import VideoSegment
from .utils import seconds_to_time_str


def ensure_output_dir(video_id: str = None):
    """output 폴더가 존재하는지 확인하고 없으면 생성합니다.
    
    Args:
        video_id (str, optional): 영상 ID가 주어지면 {output_dir}/{video_id} 폴더를 생성
    """
    # output 폴더를 기준으로 한 절대 경로 사용
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(current_dir, 'output')
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"[INFO] Output 디렉토리 확인/생성: {output_dir}")
    except Exception as e:
        print(f"[ERROR] Output 디렉토리 생성 실패: {e}")
        raise
    
    # 영상 ID별 폴더 생성
    if video_id and video_id.strip():
        video_dir = os.path.join(output_dir, video_id)
        try:
            os.makedirs(video_dir, exist_ok=True)
            print(f"[INFO] 영상 ID 디렉토리 확인/생성: {video_dir}")
            return video_dir
        except Exception as e:
            print(f"[ERROR] 영상 ID 디렉토리 생성 실패: {e}")
            raise
    
    return output_dir


def save_segments_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    세그먼트 정보를 JSON 파일로 저장합니다.
    """
    # 영상 ID별 폴더 생성
    video_dir = ensure_output_dir(video_id)
    
    # 폴더가 실제로 존재하는지 재확인
    if not os.path.exists(video_dir):
        print(f"[WARN] 폴더가 존재하지 않아 다시 생성 시도: {video_dir}")
        os.makedirs(video_dir, exist_ok=True)
        if not os.path.exists(video_dir):
            raise OSError(f"폴더 생성 실패: {video_dir}")
    
    if output_path is None:
        output_path = os.path.join(video_dir, f'{video_id}_segments.json')
    
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
    # 영상 ID별 폴더 생성
    video_dir = ensure_output_dir(video_id)
    
    # 폴더가 실제로 존재하는지 재확인
    if not os.path.exists(video_dir):
        print(f"[WARN] 폴더가 존재하지 않아 다시 생성 시도: {video_dir}")
        os.makedirs(video_dir, exist_ok=True)
        if not os.path.exists(video_dir):
            raise OSError(f"폴더 생성 실패: {video_dir}")
    
    if output_path is None:
        output_path = os.path.join(video_dir, f'{video_id}_segments.txt')
    
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


def save_segments_with_subtitles_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None, language_code: str = 'ko'):
    """
    자막이 매핑된 세그먼트 정보를 JSON 파일로 저장합니다.
    AI 요약을 포함합니다.
    """
    # 영상 ID별 폴더 생성
    video_dir = ensure_output_dir(video_id)
    
    # 폴더가 실제로 존재하는지 재확인
    if not os.path.exists(video_dir):
        print(f"[WARN] 폴더가 존재하지 않아 다시 생성 시도: {video_dir}")
        os.makedirs(video_dir, exist_ok=True)
        if not os.path.exists(video_dir):
            raise OSError(f"폴더 생성 실패: {video_dir}")
    
    if output_path is None:
        # 언어 코드를 파일명에 포함
        lang_suffix = "kr" if language_code == "ko" else "en"
        # 영상 ID 폴더 안에 저장, 파일명에서 video_id 제거 (폴더명에 이미 포함)
        output_path = os.path.join(video_dir, f'segments_with_subtitles_{lang_suffix}.json')
    
    segments_data = {
        "video_id": video_id,
        "total_segments": len(segments),
        "extraction_time": str(datetime.now()),
        "segments": []
    }
    
    # AI 요약 함수 import
    from Backend.controllers.summary import generate_summary
    
    for i, segment in enumerate(segments):
        print(f"🤖 세그먼트 {i+1}/{len(segments)} AI 요약 생성 중...")
        
        # 자막이 있는 경우 AI 요약 생성
        if segment.subtitles and len(segment.subtitles.strip()) > 50:
            ai_summary = generate_summary(segment.subtitles, language_code)
        else:
            ai_summary = "자막이 부족하여 요약할 수 없습니다."
        
        # Bloom 인지단계 분류 결과 가져오기
        bloom_category = getattr(segment, 'bloom_category', 'Unknown')
        
        segment_dict = {
            "id": segment.id,
            "title": segment.title,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "start_time_formatted": seconds_to_time_str(segment.start_time),
            "end_time_formatted": seconds_to_time_str(segment.end_time),
            "duration": segment.end_time - segment.start_time,
            "summary": ai_summary,  # AI 요약 사용
            "subtitles": segment.subtitles,
            "bloom_category": bloom_category,  # Bloom 인지단계 분류 결과
            "tags": segment.tags,
            "keywords": segment.keywords
        }
        segments_data["segments"].append(segment_dict)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(segments_data, f, ensure_ascii=False, indent=2)
        
        # 파일이 실제로 저장되었는지 확인
        if not os.path.exists(output_path):
            raise OSError(f"파일 저장 실패: {output_path}")
        
        print(f"✅ AI 요약과 Bloom 분류가 포함된 세그먼트 JSON 저장 완료: {output_path}")
    except Exception as e:
        print(f"[ERROR] 파일 저장 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise 
