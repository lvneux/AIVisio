import json
import nltk
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from nltk import word_tokenize, pos_tag
from nltk.corpus import stopwords
from konlpy.tag import Okt
import os
from datetime import datetime
import re
from typing import List, Optional
from dataclasses import dataclass
import requests


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


def time_str_to_seconds(time_str: str) -> float:
    """
    시간 문자열을 초로 변환합니다.
    
    Args:
        time_str (str): "MM:SS" 또는 "HH:MM:SS" 형식의 시간 문자열
    
    Returns:
        float: 초 단위 시간
    """
    parts = time_str.split(':')
    if len(parts) == 2:
        # MM:SS 형식
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 3:
        # HH:MM:SS 형식
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError(f"잘못된 시간 형식: {time_str}")


def seconds_to_time_str(seconds: float) -> str:
    """
    초를 시간 문자열로 변환합니다.
    
    Args:
        seconds (float): 초 단위 시간
    
    Returns:
        str: "MM:SS" 형식의 시간 문자열
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def extract_transcript(video_id, lang='en'):
    """
    YouTube 영상에서 자막을 추출합니다.
    
    Args:
        video_id (str): YouTube 영상 ID
        lang (str): 언어 선택 ('en' 또는 'ko')
    
    Returns:
        list: 자막 데이터 리스트
    """
    try:
        print(f"📺 영상 ID: {video_id}")
        print(f"🌐 선택 언어: {'한국어' if lang == 'ko' else '영어'}")
        print("🔍 자막을 가져오는 중...")
        
        # YouTubeTranscriptApi 인스턴스 생성
        ytt_api = YouTubeTranscriptApi()
        
        # 선택한 언어로 자막 가져오기
        try:
            transcript_data = ytt_api.fetch(video_id, languages=[lang])
            lang_name = "한국어" if lang == 'ko' else "영어"
            print(f"✅ {lang_name} 자막을 성공적으로 가져왔습니다.")
        except Exception as e:
            print(f"❌ {lang} 자막을 가져올 수 없습니다: {e}")
            return None
        
        print(f"📊 추출된 자막 구간 수: {len(transcript_data)}")
        
        # 자막 데이터를 JSON 파일로 저장
        save_transcript_to_file(transcript_data, video_id, lang)
        
        return transcript_data
        
    except TranscriptsDisabled:
        print("❌ 이 영상에는 자막이 제공되지 않습니다.")
        return None
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return None

def save_transcript_to_file(transcript_data, video_id, language_code):
    """자막 데이터를 JSON 파일로 저장"""
    try:
        # 저장할 데이터 구조 생성
        save_data = {
            'video_id': video_id,
            'language_code': language_code,
            'total_segments': len(transcript_data),
            'extraction_time': str(datetime.now()),
            'segments': []
        }
        
        # 각 자막 구간을 딕셔너리로 변환
        for segment in transcript_data:
            segment_dict = {
                'start': segment.start,
                'duration': segment.duration,
                'end': segment.start + segment.duration,
                'text': segment.text
            }
            save_data['segments'].append(segment_dict)
        
        # osc 폴더 생성
        os.makedirs('./osc', exist_ok=True)
        
        # 파일명 생성
        filename = f'./osc/{video_id}_{language_code}_transcript.json'
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 자막 데이터가 '{filename}' 파일로 저장되었습니다.")
        
        # 파일 크기 정보도 출력
        file_size = os.path.getsize(filename) / 1024  # KB
        print(f"📁 파일 크기: {file_size:.1f} KB")
        
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")


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


def save_segments_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    세그먼트 정보를 JSON 파일로 저장합니다.
    """
    # osc 폴더 생성
    os.makedirs('./osc', exist_ok=True)
    
    if output_path is None:
        output_path = f'./osc/{video_id}_segments.json'
    
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


def save_segments_to_txt(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    세그먼트 정보를 읽기 쉬운 TXT 파일로 저장합니다.
    """
    # osc 폴더 생성
    os.makedirs('./osc', exist_ok=True)
    
    if output_path is None:
        output_path = f'./osc/{video_id}_segments.txt'
    
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
        
        # API 키는 환경변수에서 가져오거나 직접 설정
        api_key = os.getenv('YOUTUBE_API_KEY', '')  # 환경변수에서 가져오기
        
        if not api_key:
            print("⚠️ YouTube API 키가 설정되지 않았습니다.")
            print("   환경변수 YOUTUBE_API_KEY를 설정하거나 직접 입력해주세요.")
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
            summary=video_info['snippet'].get('description', '')[:200] + "..."
        )
        segments.append(segment)
        print(f"   📌 {title} ({seconds_to_time_str(start_sec)} - {seconds_to_time_str(end_sec)})")
    
    return segments


def save_segments_with_subtitles_to_json(segments: List[VideoSegment], video_id: str, output_path: str = None):
    """
    자막이 매핑된 세그먼트 정보를 JSON 파일로 저장합니다.
    """
    # osc 폴더 생성
    os.makedirs('./osc', exist_ok=True)
    
    if output_path is None:
        output_path = f'./osc/{video_id}_segments_with_subtitles.json'
    
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


# 테스트 실행
if __name__ == "__main__":
    video_id = 'E6DuimPZDz8'  # 테스트용 영상 ID
    
    # 언어 선택 변수
    lang = 'ko'  # 'en' 또는 'ko'로 변경
    
    print("=" * 60)
    print("🎬 YouTube 영상 분석 시작")
    print("=" * 60)
    
    # 자막 추출
    print(f"\n🌐 선택된 언어: {'한국어' if lang == 'ko' else '영어'}")
    transcript_data = extract_transcript(video_id, lang=lang)
    
    if transcript_data:
        print(f"\n📊 추출된 자막 구간 수: {len(transcript_data)}")
        print("📝 첫 번째 자막 구간 예시:")
        if transcript_data:
            first_segment = transcript_data[0]
            print(f"   시간: {first_segment.start:.2f}s - {first_segment.start + first_segment.duration:.2f}s")
            print(f"   내용: {first_segment.text[:100]}...")
    
    # 세그먼트 추출 (실제 YouTube 챕터 사용)
    print(f"\n" + "=" * 60)
    print("📋 YouTube 챕터 기반 세그먼트 추출")
    print("=" * 60)
    
    # 실제 YouTube 챕터 정보 가져오기
    segments = get_youtube_chapters(video_id)
    
    # YouTube API를 사용할 수 없는 경우 예시 설명 사용
    if not segments:
        print("⚠️ YouTube API를 사용할 수 없어 예시 설명을 사용합니다.")
        example_description = """
        이 영상에서는 곰팡이의 다양한 활용에 대해 설명합니다.
        
        =====
        00:00 | Intro
        01:52 | 지구에 없어서는 안 될 곰팡이
        02:50 | 곰팡이를 이용한 새로운 식품 연구
        04:43 | 담수 균류 이용 대체 단백질 소재 연구
        08:28 | 곰팡이를 상업화하기 위한 조건
        09:57 | 음식물 쓰레기에서 배양한 곰팡이 단백질 상용화 도전
        11:01 | 곰팡이를 이용한 식물 가죽 소재 개발
        18:00 | 제품 보호 포장재로 쓰이는 버섯 균사체
        19:21 | 곰팡이와 식물 상호작용으로 식물 생장
        21:03 | 구상나무의 생존율을 높이는 외생균근
        """
        segments = segment_video_by_description(video_id, example_description)
    
    if segments:
        # 자막 매핑
        if transcript_data:
            segments = map_subtitles_to_segments(segments, transcript_data)
        
        # 세그먼트 정보 저장
        save_segments_to_json(segments, video_id)
        save_segments_to_txt(segments, video_id)
        save_segments_with_subtitles_to_json(segments, video_id)
        
        print(f"\n📈 세그먼트 분석 결과:")
        print(f"   - 총 세그먼트 수: {len(segments)}개")
        if segments:
            avg_duration = sum(seg.end_time - seg.start_time for seg in segments) / len(segments)
            print(f"   - 평균 세그먼트 길이: {avg_duration:.1f}초")
    else:
        print("⚠️ 세그먼트를 추출할 수 없습니다.")
    
    print(f"\n✅ 분석 완료!")