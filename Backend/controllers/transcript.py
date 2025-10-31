"""
YouTube 자막 추출 관련 함수들
"""

import json
import os
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from Backend.controllers.utils import seconds_to_time_str


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


def extract_transcript(video_id, lang='ko'):
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
        
        # YouTubeTranscriptApi를 사용하여 자막 가져오기
        try:
            # 올바른 방법: 인스턴스 생성 후 fetch 사용
            ytt_api = YouTubeTranscriptApi()
            transcript_data = ytt_api.fetch(video_id, languages=[lang])
            lang_name = "한국어" if lang == 'ko' else "영어"
            print(f"✅ {lang_name} 자막을 성공적으로 가져왔습니다.")
        except Exception as e:
            print(f"❌ {lang} 자막을 가져올 수 없습니다: {e}")
            # 대안: 영어 자막 시도
            try:
                print("🔄 영어 자막으로 재시도...")
                ytt_api = YouTubeTranscriptApi()
                transcript_data = ytt_api.fetch(video_id, languages=['en'])
                lang = 'en'
                print("✅ 영어 자막을 성공적으로 가져왔습니다.")
            except Exception as e2:
                print(f"❌ 영어 자막도 실패: {e2}")
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
        # 영상 ID별 폴더 생성
        video_dir = ensure_output_dir(video_id)
        
        # 폴더가 실제로 존재하는지 재확인
        if not os.path.exists(video_dir):
            print(f"[WARN] 폴더가 존재하지 않아 다시 생성 시도: {video_dir}")
            os.makedirs(video_dir, exist_ok=True)
            if not os.path.exists(video_dir):
                raise OSError(f"폴더 생성 실패: {video_dir}")
        
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
        
        # 파일명 생성 (영상 ID 폴더 안에 저장)
        filename = os.path.join(video_dir, f'{video_id}_{language_code}_transcript.json')
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 자막 데이터가 '{filename}' 파일로 저장되었습니다.")
        
        # 파일 크기 정보도 출력
        file_size = os.path.getsize(filename) / 1024  # KB
        print(f"📁 파일 크기: {file_size:.1f} KB")
        
    except Exception as e:
        print(f"[ERROR] 파일 저장 중 오류 발생: {e}")
        import traceback
        traceback.print_exc() 
