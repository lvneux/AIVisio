"""
YouTube API 관련 함수들
"""

import os
import re
import requests
from typing import List, Optional
from osc.models.video_segment import VideoSegment
from .utils import time_str_to_seconds, seconds_to_time_str

# .env 파일 로드
try:
    from dotenv import load_dotenv
    # 루트 폴더(AIVisio)에서 .env 파일 찾기
    import os
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(current_dir, '.env')
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드 완료: {env_path}")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않음, 환경변수 직접 사용")
except Exception as e:
    print(f"⚠️ .env 파일 로드 실패: {e}")


def get_youtube_video_info(video_id: str) -> Optional[dict]:
    """
    YouTube Data API v3를 사용하여 비디오 정보를 가져옵니다.
    
    Args:
        video_id (str): YouTube 비디오 ID
    
    Returns:
        Optional[dict]: 비디오 정보 (챕터 정보 포함)
    """
    try:
        # YouTube Data API v3 엔드포인트
        url = f"https://www.googleapis.com/youtube/v3/videos"
        
        # API 키는 환경변수에서 가져오기
        api_key = 'AIzaSyAOwWaR6XuNF3w5YxFDSYZrPFyrEqw81UE'

        if api_key == None:
            api_key = "AIzaSyAOwWaR6XuNF3w5YxFDSYZrPFyrEqw81UE"

        if not api_key:
            print("⚠️ YouTube API 키가 설정되지 않았습니다.")
            print("   .env 파일에 YOUTUBE_API_KEY를 설정해주세요.")
            return None
        
        params = {
            'part': 'snippet,contentDetails',
            'id': video_id,
            'key': api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('items'):
            print(f"❌ 비디오 ID {video_id}를 찾을 수 없습니다.")
            return None
        
        video_info = data['items'][0]
        print(f"✅ YouTube 비디오 정보를 성공적으로 가져왔습니다.")
        print(f"   제목: {video_info['snippet']['title']}")
        
        return video_info
        
    except requests.exceptions.RequestException as e:
        print(f"❌ YouTube API 요청 중 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 비디오 정보 가져오기 중 오류: {e}")
        return None


def extract_chapters_from_description(description: str) -> List[tuple]:
    """
    비디오 설명에서 챕터 정보를 추출합니다.
    
    Args:
        description (str): 비디오 설명
    
    Returns:
        List[tuple]: (시간, 제목) 튜플 리스트
    """
    chapters = []
    
    # 시간 패턴 매칭 (MM:SS 또는 HH:MM:SS)
    chapter_pattern = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[|\-]?\s*(.+)'
    
    lines = description.split('\n')
    for line in lines:
        match = re.match(chapter_pattern, line.strip())
        if match:
            time_str = match.group(1)
            title = match.group(2).strip()
            chapters.append((time_str, title))
    
    return chapters


def get_youtube_chapters(video_id: str) -> Optional[List[VideoSegment]]:
    """
    YouTube 영상에서 실제 챕터 정보를 가져와서 VideoSegment 객체로 변환합니다.
    
    Args:
        video_id (str): YouTube 비디오 ID
    
    Returns:
        Optional[List[VideoSegment]]: 챕터 세그먼트 리스트
    """
    print(f"🔍 YouTube 챕터 추출 중: {video_id}")
    
    # 1. YouTube API로 비디오 정보 가져오기
    video_info = get_youtube_video_info(video_id)
    if not video_info:
        print("⚠️ YouTube API를 사용할 수 없어 설명에서 챕터를 추출합니다.")
        return None
    
    # 2. 설명에서 챕터 정보 추출
    description = video_info['snippet'].get('description', '')
    chapters = extract_chapters_from_description(description)
    
    if not chapters:
        print("⚠️ 설명에서 챕터 정보를 찾을 수 없습니다.")
        return None
    
    print(f"✅ {len(chapters)}개의 챕터를 찾았습니다.")
    
    # 3. VideoSegment 객체로 변환
    segments = []
    for idx, (time_str, title) in enumerate(chapters):
        start_sec = time_str_to_seconds(time_str)
        
        # 다음 챕터의 시작 시간을 종료 시간으로 사용
        if idx + 1 < len(chapters):
            end_sec = time_str_to_seconds(chapters[idx + 1][0])
        else:
            # 마지막 챕터는 90초 후로 설정
            end_sec = start_sec + 90.0
        
        segment = VideoSegment(
            id=f"{video_id}_seg_{idx}",
            video_id=video_id,
            title=title,
            start_time=start_sec,
            end_time=end_sec,
            subtitles="",
            tags=[],
            keywords=[],
            summary=video_info['snippet'].get('description', '')[:200] + "...",
            cognitive_level="Understand",
            dok_level="Level 2"
        )
        segments.append(segment)
        print(f"   📌 {title} ({seconds_to_time_str(start_sec)} - {seconds_to_time_str(end_sec)})")
    
    return segments 
