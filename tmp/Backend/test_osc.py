import json
import requests
import time
import numpy as np
from collections import defaultdict, Counter
from typing import List, Tuple
import math

# 요약 모델을 위한 import
try:
    from transformers import pipeline
    SUMMARIZATION_AVAILABLE = True
except ImportError:
    SUMMARIZATION_AVAILABLE = False
    print("⚠️ transformers 라이브러리가 설치되지 않아 요약 기능을 사용할 수 없습니다.")

# 🔐 사용자 키 (Wikifier 사이트에서 발급)
WIKIFIER_USER_KEY = "dgvbwjfonhpzjpdjjkzpgefbiifvfz"
json_path = "./script/E6DuimPZDz8_ko_transcript.json"
# ========== Step 1: 자막 JSON 로드 ==========
def load_youtube_subtitles(json_path: str) -> List[dict]:
    """
    YouTube 자막 JSON 파일을 로드합니다.
    새로운 형식 (script_osc.py에서 생성)과 기존 형식 모두 지원합니다.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 새로운 형식인지 확인 (segments 키가 있는지)
    if 'segments' in data:
        print(f"📁 새로운 형식 JSON 파일 로드: {data.get('video_id', 'Unknown')}")
        print(f"🌐 언어: {data.get('language_code', 'Unknown')}")
        print(f"📊 총 세그먼트 수: {data.get('total_segments', 0)}")
        return data['segments']
    else:
        # 기존 형식 (직접 리스트)
        print(f"📁 기존 형식 JSON 파일 로드")
        return data

def wikifier(text: str, user_key: str, lang: str = 'en') -> List[Tuple[str, float]]:
    url = 'http://www.wikifier.org/annotate-article'
    params = {
        'userKey': user_key,
        'text': text,
        'lang': lang,
        'support': 'true',
        'pageRankSqThreshold': '0.8',
        'applyPageRankSqThreshold': 'true',
        'nTopDfValuesToIgnore': '100',
        'nWordsToIgnoreFromList': '100',
        'wikiDataClasses': 'false',
        'wikiDataClassIds': 'false',
        'supportText': 'false',
        'ranges': 'false',
        'includeCosines': 'false'
    }

    try:
        # 타임아웃 설정
        response = requests.post(url, data=params, timeout=30)
        
        if response.status_code == 429:
            print("⚠️ Rate limit 초과 - 60초 대기 후 재시도")
            time.sleep(60)
            response = requests.post(url, data=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Wikifier API 오류 (상태코드: {response.status_code}): {response.text[:200]}")
            return []
        
        annotations = response.json().get("annotations", [])
        top_3 = sorted(
            [(ann['title'], ann['pageRank']) for ann in annotations if 'title' in ann and 'pageRank' in ann],
            key=lambda x: x[1], reverse=True
        )[:3]
        return top_3
        
    except requests.exceptions.Timeout:
        print("⚠️ Wikifier API 타임아웃")
        return []
    except requests.exceptions.ConnectionError:
        print("⚠️ Wikifier API 연결 오류")
        return []
    except Exception as e:
        print(f"⚠️ Wikifier 처리 중 오류: {e}")
        return []

def normalize_scores(scores: List[float]) -> List[float]:
    total = sum(scores)
    if total > 0:
        return [s / total for s in scores]
    elif len(scores) > 0:
        return [1/len(scores)] * len(scores)
    else:
        return [1.0]  # 빈 리스트인 경우 기본값

def shannon_entropy(prob_dist: List[float]) -> float:
    return -sum(p * math.log2(p) for p in prob_dist if p > 0)

def normalize_entropy(entropy_list: List[float]) -> List[float]:
    min_e, max_e = min(entropy_list), max(entropy_list)
    return [(e - min_e) / (max_e - min_e + 1e-8) for e in entropy_list]

def compute_entropy_deltas(norm_entropy: List[float]) -> List[float]:
    return [abs(norm_entropy[i+1] - norm_entropy[i]) for i in range(len(norm_entropy) - 1)]


def segment_blocks_by_entropy(entropy_deltas: List[float], threshold: float = 0.30) -> List[int]:
    """
    엔트로피 변화를 기반으로 세그먼트 경계를 찾습니다.
    더 낮은 임계값으로 더 많은 세그먼트를 생성합니다.
    """
    boundaries = [0]
    for i, delta in enumerate(entropy_deltas):
        if delta > threshold:
            boundaries.append(i + 1)
    boundaries.append(len(entropy_deltas) + 1)
    
    # 최소 세그먼트 크기 보장 (너무 작은 세그먼트 방지)
    filtered_boundaries = [boundaries[0]]
    for i in range(1, len(boundaries) - 1):
        if boundaries[i] - filtered_boundaries[-1] >= 1:  # 최소 1블록
            filtered_boundaries.append(boundaries[i])
    filtered_boundaries.append(boundaries[-1])
    
    segments = [(filtered_boundaries[i], filtered_boundaries[i+1]) for i in range(len(filtered_boundaries) - 1)]
    
    print(f"🔍 엔트로피 기반 세그먼트 분할:")
    print(f"   임계값: {threshold}")
    print(f"   생성된 세그먼트 수: {len(segments)}")
    for i, (start, end) in enumerate(segments):
        print(f"   세그먼트 {i+1}: 블록 {start}~{end-1} ({end-start}개 블록)")
    
    return segments


def summarize_segments(blocks, segments, all_topics):
    print("📌 Segment Summary (with Wikifier):")
    for seg_idx, (start, end) in enumerate(segments):
        segment_topics = []
        for i in range(start, end):
            segment_topics.extend([topic for topic, _ in all_topics[i]])
        dominant = Counter(segment_topics).most_common(1)[0][0] if segment_topics else "N/A"
        print(f"Segment {seg_idx + 1}: Blocks {start} ~ {end - 1}, Dominant Topic: {dominant}")
        
def print_detailed_blocks_summary(all_topics: List[List[Tuple[str, float]]], entropy_list: List[float]):
    print(f"{'t':<3} | {'Top-3 Topics (PageRank)':<60} | {'H_t (nat)':>9} | {'ΔH_t':>6}")
    print('-' * 90)

    prev_entropy = None
    for t, (topics, entropy) in enumerate(zip(all_topics, entropy_list), 1):
        topics_str = ', '.join([f"{topic} {score:.2f}" for topic, score in topics])
        delta = abs(entropy - prev_entropy) if prev_entropy is not None else None
        delta_str = f"{delta:.2f}" if delta is not None else "—"
        print(f"{t:<3} | {topics_str:<60} | {entropy:>9.2f} | {delta_str:>6}")
        prev_entropy = entropy
        
import pandas as pd

def save_summary_to_csv(all_topics: List[List[Tuple[str, float]]], entropy_list: List[float], output_path: str):
    data = []
    prev_entropy = None

    for t, (topics, entropy) in enumerate(zip(all_topics, entropy_list), 1):
        delta = abs(entropy - prev_entropy) if prev_entropy is not None else None
        topic_strs = [f"{topic} {score:.2f}" for topic, score in topics]
        row = {
            't': t,
            'Top1': topic_strs[0] if len(topic_strs) > 0 else '',
            'Top2': topic_strs[1] if len(topic_strs) > 1 else '',
            'Top3': topic_strs[2] if len(topic_strs) > 2 else '',
            'H_t (nat)': round(entropy, 4),
            'ΔH_t': round(delta, 4) if delta is not None else ''
        }
        data.append(row)
        prev_entropy = entropy

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ CSV 저장 완료: {output_path}")

def save_sorted_blocks_to_json(sorted_blocks: List[str], output_path: str = "osc/sorted_blocks.json"):
    """
    sorted_blocks를 JSON 파일로 저장하는 함수
    
    Args:
        sorted_blocks: 저장할 블록 리스트
        output_path: 저장할 파일 경로 (기본값: "sorted_blocks.json")
    """
    blocks_data = {
        "total_blocks": len(sorted_blocks),
        "blocks": [
            {
                "block_index": i,
                "text": block.strip(),
                "word_count": len(block.split())
            }
            for i, block in enumerate(sorted_blocks)
        ]
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(blocks_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ sorted_blocks 저장 완료: {output_path} (총 {len(sorted_blocks)}개 블록)")

def load_sorted_blocks_from_json(input_path: str = "osc/sorted_blocks.json") -> List[str]:
    """
    JSON 파일에서 sorted_blocks를 로드하는 함수
    
    Args:
        input_path: 로드할 파일 경로 (기본값: "sorted_blocks.json")
    
    Returns:
        블록 텍스트 리스트
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    blocks = [block["text"] for block in data["blocks"]]
    print(f"✅ sorted_blocks 로드 완료: {input_path} (총 {len(blocks)}개 블록)")
    return blocks

def save_segments_to_json(blocks, segments, all_topics, output_path: str = "osc/wikifier_segments.json"):
    """
    Wikifier로 나눠진 세그먼트의 시간과 내용을 JSON 파일로 저장하는 함수
    
    Args:
        blocks: 원본 블록 리스트
        segments: 세그먼트 경계 정보 [(start, end), ...]
        all_topics: 각 블록의 Wikifier 토픽 정보
        output_path: 저장할 파일 경로
    """
    segments_data = {
        "total_segments": len(segments),
        "segments": []
    }
    
    for seg_idx, (start, end) in enumerate(segments):
        # 세그먼트의 모든 블록 텍스트 합치기
        segment_text = ""
        for i in range(start, end):
            segment_text += blocks[i] + " "
        
        # 세그먼트의 모든 토픽 수집
        segment_topics = []
        for i in range(start, end):
            segment_topics.extend([topic for topic, _ in all_topics[i]])
        
        # 주요 토픽 찾기
        topic_counter = Counter(segment_topics)
        dominant_topic = topic_counter.most_common(1)[0][0] if segment_topics else "N/A"
        
        # 시간 계산 (각 블록은 1분 = 60초)
        start_time_minutes = start
        end_time_minutes = end - 1
        start_time_seconds = start_time_minutes * 60
        end_time_seconds = (end_time_minutes + 1) * 60
        
        # 시간을 HH:MM:SS 형식으로 변환
        def seconds_to_time(seconds):
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        
        segment_info = {
            "segment_id": seg_idx + 1,
            "block_range": {
                "start_block": start,
                "end_block": end - 1,
                "total_blocks": end - start
            },
            "time_range": {
                "start_time_minutes": start_time_minutes,
                "end_time_minutes": end_time_minutes,
                "start_time_formatted": seconds_to_time(start_time_seconds),
                "end_time_formatted": seconds_to_time(end_time_seconds),
                "duration_minutes": end_time_minutes - start_time_minutes + 1
            },
            "content": {
                "text": segment_text.strip(),
                "word_count": len(segment_text.split()),
                "character_count": len(segment_text.strip())
            },
            "topics": {
                "dominant_topic": dominant_topic,
                "all_topics": list(topic_counter.items()),
                "unique_topics_count": len(topic_counter)
            }
        }
        
        segments_data["segments"].append(segment_info)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Wikifier 세그먼트 저장 완료: {output_path} (총 {len(segments)}개 세그먼트)")

def generate_summary(text: str, language_code: str = 'ko') -> str:
    """
    주어진 텍스트를 요약합니다.
    
    Args:
        text (str): 요약할 텍스트
        language_code (str): 언어 코드 ('ko' 또는 'en')
    
    Returns:
        str: 요약된 텍스트
    """
    if not SUMMARIZATION_AVAILABLE:
        return "요약 생성에 필요한 라이브러리가 설치되어 있지 않습니다."
    
    try:
        # 언어에 따른 모델 선택
        if language_code == 'ko':
            model_name = "digit82/kobart-summarization"  # 한국어 요약 모델 (대안)
        else:
            model_name = "facebook/bart-large-cnn"  # 영어 요약 모델
        
        summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name,
            device=-1  # CPU 사용 (GPU가 없거나 메모리 부족 시)
        )
        
        # 텍스트 길이 제한 (모델 제한 고려)
        max_input_length = 1024 if language_code == 'ko' else 1024
        if len(text) > max_input_length:
            text = text[:max_input_length]
        
        summary = summarizer(
            text, 
            max_length=130, 
            min_length=30, 
            do_sample=False,
            truncation=True
        )
        return summary[0]['summary_text']
        
    except Exception as e:
        return f"요약 생성 중 오류 발생: {str(e)}"

def save_segments_to_txt(blocks, segments, all_topics, output_path: str = "osc/wikifier_segments.txt"):
    """
    Wikifier로 나눠진 세그먼트를 읽기 쉬운 TXT 파일로 저장하는 함수
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Wikifier 세그먼트 요약 ===\n\n")
        
        for seg_idx, (start, end) in enumerate(segments):
            # 세그먼트 텍스트 합치기
            segment_text = ""
            for i in range(start, end):
                segment_text += blocks[i] + " "
            
            # 토픽 수집
            segment_topics = []
            for i in range(start, end):
                segment_topics.extend([topic for topic, _ in all_topics[i]])
            
            dominant_topic = Counter(segment_topics).most_common(1)[0][0] if segment_topics else "N/A"
            
            # 시간 계산
            start_time = f"{start:02d}:00"
            end_time = f"{end-1:02d}:59"
            
            f.write(f"📌 세그먼트 {seg_idx + 1}\n")
            f.write(f"⏰ 시간: {start_time} ~ {end_time}\n")
            f.write(f"🏷️  주요 토픽: {dominant_topic}\n")
            f.write(f"📝 내용:\n{segment_text.strip()}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"✅ Wikifier 세그먼트 TXT 저장 완료: {output_path}")

def save_segments_with_summaries(blocks, segments, all_topics, language_code: str = 'ko', output_path: str = "osc/wikifier_segments_with_summaries.txt"):
    """
    Wikifier로 나눠진 세그먼트를 요약과 함께 TXT 파일로 저장하는 함수
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Wikifier 세그먼트 요약 (AI 요약 포함) ===\n\n")
        
        for seg_idx, (start, end) in enumerate(segments):
            # 세그먼트 텍스트 합치기
            segment_text = ""
            for i in range(start, end):
                segment_text += blocks[i] + " "
            
            segment_text = segment_text.strip()
            
            # 토픽 수집
            segment_topics = []
            for i in range(start, end):
                segment_topics.extend([topic for topic, _ in all_topics[i]])
            
            dominant_topic = Counter(segment_topics).most_common(1)[0][0] if segment_topics else "N/A"
            
            # 시간 계산
            start_time = f"{start:02d}:00"
            end_time = f"{end-1:02d}:59"
            
            f.write(f"📌 세그먼트 {seg_idx + 1}\n")
            f.write(f"⏰ 시간: {start_time} ~ {end_time}\n")
            f.write(f"🏷️  주요 토픽: {dominant_topic}\n")
            f.write(f"📝 원본 내용:\n{segment_text}\n\n")
            
            # AI 요약 생성
            if len(segment_text) > 50:  # 충분히 긴 텍스트만 요약
                print(f"🤖 세그먼트 {seg_idx + 1} 요약 생성 중...")
                summary = generate_summary(segment_text, language_code)
                f.write(f"🤖 AI 요약:\n{summary}\n")
            else:
                f.write("🤖 AI 요약: 텍스트가 너무 짧아 요약하지 않음\n")
            
            f.write("-" * 50 + "\n\n")
    
    print(f"✅ Wikifier 세그먼트 요약 TXT 저장 완료: {output_path}")

def segment_blocks_one_minute(data: List[dict]):
    block_map = defaultdict(str)

    for entry in data:
        block_index = int(entry['start'] // 60)
        block_map[block_index] += ' ' + entry['text']

    segments_one_minute = [block_map[i] for i in sorted(block_map.keys())]

    return segments_one_minute

def process_youtube_segments_with_wikifier(json_path: str, user_key: str):
    data = load_youtube_subtitles(json_path)
    
    # 자막 1분별로 끊기.
    segments_one_minute = segment_blocks_one_minute(data)

    # Wikifier 호출 (1초 딜레이로 API 과부하 방지)
    all_topics = []
    
    # JSON 파일에서 언어 정보 가져오기
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    language_code = json_data.get('language_code', 'en')  # 기본값은 영어
    
    print(f"🌐 Wikifier 언어 설정: {language_code}")
    
    # 블록 수 제한 (테스트용)
    max_blocks = 10  # 10개 블록으로 늘림
    print(f"🔧 처리할 블록 수 제한: {max_blocks}개")
    
    for i, block in enumerate(sorted_blocks[:max_blocks]):
        print(f"🔎 Wikifier 처리 중: Block {i+1}/{min(max_blocks, len(sorted_blocks))}")
        
        # 텍스트 길이 제한 및 전처리
        text = block[:1000]  # 1000자로 더 줄임
        if len(text.strip()) < 10:  # 너무 짧은 텍스트 건너뛰기
            print(f"   ⏭️ Block {i+1}: 텍스트가 너무 짧음 (건너뜀)")
            all_topics.append([("empty_block", 1.0)])
            continue
            
        topics = wikifier(text, user_key, lang=language_code)
        
        # Wikifier 결과가 비어있으면 더미 데이터 사용
        if not topics:
            print(f"   ⚠️ Block {i+1}: Wikifier 결과 없음, 더미 데이터 사용")
            topics = [("dummy_topic", 1.0)]
        
        all_topics.append(topics)
        
        # 더 긴 딜레이로 API 과부하 방지
        time.sleep(3)  # 3초 딜레이
        
        # 3개 블록마다 추가 딜레이
        if (i + 1) % 3 == 0:
            print(f"   ⏸️ 3개 블록 완료, 15초 대기...")
            time.sleep(15)
    
    # 점수 정규화 및 엔트로피 계산
    entropy_list = []
    for topics in all_topics:
        scores = [score for _, score in topics]
        probs = normalize_scores(scores)
        entropy = shannon_entropy(probs)
        entropy_list.append(entropy)
    
    norm_entropy = normalize_entropy(entropy_list)
    entropy_deltas = compute_entropy_deltas(norm_entropy)
    segments = segment_blocks_by_entropy(entropy_deltas)
    print_detailed_blocks_summary(all_topics, entropy_list)


    summarize_segments(sorted_blocks, segments, all_topics)
    
    save_summary_to_csv(all_topics, entropy_list, "osc/segment_summary.csv")
            # Wikifier 세그먼트를 파일로 저장
    save_segments_to_json(sorted_blocks, segments, all_topics)
    save_segments_to_txt(sorted_blocks, segments, all_topics)
    
    # AI 요약과 함께 저장
    save_segments_with_summaries(sorted_blocks, segments, all_topics, language_code)


#process_youtube_segments_with_wikifier(json_path, WIKIFIER_USER_KEY)

test_data = load_youtube_subtitles(json_path)
print(segment_blocks_one_minute(test_data))