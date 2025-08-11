"""
YouTube 영상 분석 스크립트 (모듈화된 버전)
기존 script_osc.py의 기능을 모듈화된 구조로 재구성
"""

from . import (
    extract_transcript,
    get_youtube_chapters,
    segment_video_by_description,
    map_subtitles_to_segments,
    save_segments_to_json,
    save_segments_to_txt,
    save_segments_with_subtitles_to_json
)


def analyze_video(video_id: str, lang: str = 'ko'):
    """
    YouTube 영상을 분석하여 세그먼트를 추출하고 자막을 매핑합니다.
    
    Args:
        video_id (str): YouTube 영상 ID
        lang (str): 언어 선택 ('en' 또는 'ko')
    """
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
    
    # YouTube API를 사용할 수 없는 경우 실패 처리
    if not segments:
        print("❌ YouTube API를 사용할 수 없어 세그먼트를 추출할 수 없습니다.")
        print("   YouTube API 키를 설정하거나 다른 영상을 시도해주세요.")
        return
    
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


# 테스트 실행
if __name__ == "__main__":
    video_id = 'E6DuimPZDz8'  # 테스트용 영상 ID
    lang = 'ko'  # 'en' 또는 'ko'로 변경
    
    analyze_video(video_id, lang) 