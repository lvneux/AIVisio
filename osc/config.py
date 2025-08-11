"""
설정 파일
환경변수나 API 키 등을 관리합니다.
"""

import os

# YouTube Data API v3 키
# 환경변수에서 가져오거나 직접 설정
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

# API 키가 설정되지 않은 경우 사용자에게 안내
if not YOUTUBE_API_KEY:
    print("⚠️ YouTube API 키가 설정되지 않았습니다.")
    print("   다음 중 하나의 방법으로 설정해주세요:")
    print("   1. 환경변수 YOUTUBE_API_KEY 설정")
    print("   2. 이 파일에서 직접 YOUTUBE_API_KEY = 'your_key_here' 입력")
    print("   3. .env 파일 생성 (YOUTUBE_API_KEY=your_key_here)")
else:
    print("✅ YouTube API 키가 설정되었습니다.") 