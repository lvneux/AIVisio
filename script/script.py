import json
import nltk
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from nltk import word_tokenize, pos_tag
from nltk.corpus import stopwords
from konlpy.tag import Okt

# NLTK 초기화
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger_eng')

# Konlpy 형태소 분석기
okt = Okt()

# 언어에 따른 명사 추출 함수
def extract_nouns(text, lang='en'):
    if lang == 'ko':
        return okt.nouns(text)
    else:
        words = word_tokenize(text)
        tagged = pos_tag(words)
        nouns = [word for word, pos in tagged if pos.startswith('NN')]
        stop_words = set(stopwords.words('english'))
        return [word for word in nouns if word.lower() not in stop_words]

# 자막 및 명사 추출
def process_video(video_id):
    try:
        # 자막 목록 확인
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # 언어 우선순위 설정: en > ko
        try:
            transcript = transcript_list.find_transcript(['en']).fetch()
            lang = 'en'
            print("📌 영어 자막을 사용합니다.")
        except:
            transcript = transcript_list.find_transcript(['ko']).fetch()
            lang = 'ko'
            print("📌 한국어 자막을 사용합니다.")
        
        transcript_data = transcript.to_raw_data()

        # 자막 JSON 저장
        with open(f'./script/{video_id}_subtitles.json', 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=4)
        print("✅ 자막 추출이 완료되어 'subtitles.json'으로 저장되었습니다.")

        # 자막에서 명사 추출
        noun_data = []
        for entry in transcript_data:
            nouns = extract_nouns(entry['text'], lang=lang)
            noun_data.append({
                'start': entry['start'],
                'end': entry['start'] + entry['duration'],
                'nouns': nouns
            })

        # JSON 파일로 저장
        with open('./script/noun.json', 'w', encoding='utf-8') as f:
            json.dump(noun_data, f, ensure_ascii=False, indent=4)

        print("✅ 명사 추출이 완료되어 'noun.json'으로 저장되었습니다.")

    except TranscriptsDisabled:
        print("❌ 이 영상에는 자막이 제공되지 않습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")

# 사용 예시
video_id = 'aircAruvnKk'  # 원하는 영상 ID
process_video(video_id)
