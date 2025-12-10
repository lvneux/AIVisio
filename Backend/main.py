"""
YouTube 영상 분석 메인 스크립트
모듈화된 구조를 사용하여 깔끔하게 정리된 버전
"""

import json
from pathlib import Path

from .controllers.transcript import extract_transcript
from .controllers.youtube_api import get_youtube_chapters
from .controllers.segments import map_subtitles_to_segments
from .controllers.file_io import  save_segments_with_subtitles_to_json
from .controllers.bloom_classifier import BloomClassifier

"""
def load_selected_video_id(default: str = "E6DuimPZDz8") -> str:
    
    #Frontend/main.py가 저장한 selected_video.json을 읽어 video_id를 반환.
    
    try:
        root_dir = Path(__file__).resolve().parents[1]  # 프로젝트 루트
        json_path = root_dir / "Backend" / "output" / "selected_video.json"
        if not json_path.exists():
            print("⚠️ selected_video.json이 없어 기본 영상 ID를 사용합니다.")
            return default
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vid = (data or {}).get("video_id")
        if not vid:
            print("⚠️ selected_video.json에 video_id가 없어 기본 영상 ID를 사용합니다.")
            return default
        print(f"✅ Frontend에서 선택된 영상 ID 사용: {vid}")
        return vid
    except Exception as e:
        print(f"⚠️ 선택 영상 로딩 중 오류: {e} → 기본 영상 ID 사용")
        return default
"""

def main(video_id="E6DuimPZDz8", lang='en'):
    """메인 실행 함수
    
    Args:
        video_id (str, optional): 분석할 YouTube 영상 ID. None이면 selected_video.json에서 로드
        language (str): 자막 언어 ('ko' 또는 'en'). 기본값은 'ko'
    """
    print("=" * 60)
    print(f"🎬 YouTube 영상 분석 시작 - Video ID: {video_id}")
    print("=" * 60)

    # 자막 추출
    print(f"\n🌐 선택된 언어: {'한국어' if lang == 'ko' else '영어'}")
    transcript_data = extract_transcript(video_id, lang=lang)

    if transcript_data:
        print(f"\n📊 추출된 자막 구간 수: {len(transcript_data)}")
        print("📝 첫 번째 자막 구간 예시:")
        first_segment = transcript_data[0]
        print(f"   시간: {first_segment.start:.2f}s - {first_segment.start + first_segment.duration:.2f}s")
        print(f"   내용: {first_segment.text[:100]}...")
    else:
        print("❌ 자막을 추출할 수 없습니다.")
        return

    # 세그먼트 추출 (실제 YouTube 챕터 사용)
    print(f"\n" + "=" * 60)
    print("📋 YouTube 챕터 기반 세그먼트 추출")
    print("=" * 60)

    # 실제 YouTube 챕터 정보 가져오기
    segments = get_youtube_chapters(video_id)

    # 여기다가 custom 세그먼트 추출 코드 추가
    

    # YouTube API를 사용할 수 없는 경우 예시 설명 사용
    if not segments:
        print("⚠️ YouTube API를 사용할 수 없습니다.")
        print("   환경변수 YOUTUBE_API_KEY를 설정해주세요.")
        return

    if segments:
        # 자막 매핑
        if transcript_data:
            segments = map_subtitles_to_segments(segments, transcript_data)

        # Bloom 인지단계 분류
        print(f"\n" + "=" * 60)
        print("🧠 Bloom 인지단계 분류")
        print("=" * 60)
        
        try:
            bloom_classifier = BloomClassifier()
            segments = bloom_classifier.predict_segments(segments)
        except Exception as e:
            print(f"⚠️ Bloom 분류 중 오류 발생: {e}")
            print("   Bloom 분류 없이 진행합니다.")
            # 오류가 발생해도 계속 진행
            for segment in segments:
                segment.bloom_category = "Unknown"

        # 세그먼트 정보 저장
        save_segments_with_subtitles_to_json(segments, video_id, language_code=lang)

        print(f"\n📈 세그먼트 분석 결과:")
        print(f"   - 총 세그먼트 수: {len(segments)}개")
        if segments:
            avg_duration = sum(seg.end_time - seg.start_time for seg in segments) / len(segments)
            print(f"   - 평균 세그먼트 길이: {avg_duration:.1f}초")
            
            # Bloom 분류 결과 요약
            bloom_counts = {}
            for seg in segments:
                category = getattr(seg, 'bloom_category', 'Unknown')
                bloom_counts[category] = bloom_counts.get(category, 0) + 1
            
            print(f"\n🧠 Bloom 인지단계 분포:")
            for category, count in bloom_counts.items():
                print(f"   - {category}: {count}개")
    else:
        print("⚠️ 세그먼트를 추출할 수 없습니다.")

    print(f"\n✅ 분석 완료!")


if __name__ == "__main__":
    import sys
    video_id = sys.argv[1] if len(sys.argv) > 1 else "aircAruvnKk"
    main(video_id)