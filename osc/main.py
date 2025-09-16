"""
YouTube 영상 분석 메인 스크립트
모듈화된 구조를 사용하여 깔끔하게 정리된 버전
"""

import json
from pathlib import Path

from osc.controllers.transcript import extract_transcript
from osc.controllers.youtube_api import get_youtube_chapters
from osc.controllers.segments import segment_video_by_description, map_subtitles_to_segments
from osc.controllers.file_io import save_segments_to_json, save_segments_to_txt, save_segments_with_subtitles_to_json
from osc.controllers.summary import generate_summary


def load_selected_video_id(default: str = "E6DuimPZDz8") -> str:
    """
    Frontend/main.py가 저장한 selected_video.json을 읽어 video_id를 반환.
    """
    try:
        root_dir = Path(__file__).resolve().parents[1]  # 프로젝트 루트
        json_path = root_dir / "osc" / "output" / "selected_video.json"
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


def main():
    """메인 실행 함수"""
    video_id = load_selected_video_id(default="E6DuimPZDz8")

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

    # YouTube API를 사용할 수 없는 경우 예시 설명 사용
    if not segments:
        print("⚠️ YouTube API를 사용할 수 없습니다.")
        print("   환경변수 YOUTUBE_API_KEY를 설정해주세요.")
        return

    if segments:
        # 자막 매핑
        if transcript_data:
            segments = map_subtitles_to_segments(segments, transcript_data)

        # 세그먼트 정보 저장
        save_segments_to_json(segments, video_id)
        save_segments_to_txt(segments, video_id)
        save_segments_with_subtitles_to_json(segments, video_id, language_code=lang)

        print(f"\n📈 세그먼트 분석 결과:")
        print(f"   - 총 세그먼트 수: {len(segments)}개")
        if segments:
            avg_duration = sum(seg.end_time - seg.start_time for seg in segments) / len(segments)
            print(f"   - 평균 세그먼트 길이: {avg_duration:.1f}초")
    else:
        print("⚠️ 세그먼트를 추출할 수 없습니다.")

    print(f"\n✅ 분석 완료!")


if __name__ == "__main__":
    main()