import json
import requests
import time
import numpy as np
from collections import defaultdict, Counter
from typing import List, Tuple
import math

# 🔐 사용자 키 (Wikifier 사이트에서 발급)
WIKIFIER_USER_KEY = "dgvbwjfonhpzjpdjjkzpgefbiifvfz"
json_path = "./script/aircAruvnKk_subtitles.json"
# ========== Step 1: 자막 JSON 로드 ==========
def load_youtube_subtitles(json_path: str) -> List[dict]:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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

    response = requests.post(url, data=params)
    if response.status_code != 200:
        print("❌ Wikifier API 오류:", response.text)
        return []
    
    annotations = response.json().get("annotations", [])
    top_3 = sorted(
        [(ann['title'], ann['pageRank']) for ann in annotations if 'title' in ann and 'pageRank' in ann],
        key=lambda x: x[1], reverse=True
    )[:3]
    return top_3

def normalize_scores(scores: List[float]) -> List[float]:
    total = sum(scores)
    return [s / total for s in scores] if total > 0 else [1/len(scores)] * len(scores)

def shannon_entropy(prob_dist: List[float]) -> float:
    return -sum(p * math.log2(p) for p in prob_dist if p > 0)


def normalize_entropy(entropy_list: List[float]) -> List[float]:
    min_e, max_e = min(entropy_list), max(entropy_list)
    return [(e - min_e) / (max_e - min_e + 1e-8) for e in entropy_list]

def compute_entropy_deltas(norm_entropy: List[float]) -> List[float]:
    return [abs(norm_entropy[i+1] - norm_entropy[i]) for i in range(len(norm_entropy) - 1)]


def segment_blocks_by_entropy(entropy_deltas: List[float], threshold: float = 0.50) -> List[int]:
    boundaries = [0]
    for i, delta in enumerate(entropy_deltas):
        if delta > threshold:
            boundaries.append(i + 1)
    boundaries.append(len(entropy_deltas) + 1)
    return [(boundaries[i], boundaries[i+1]) for i in range(len(boundaries) - 1)]


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



def process_youtube_segments_with_wikifier(json_path: str, user_key: str):
    data = load_youtube_subtitles(json_path)
    
    block_map = defaultdict(str)
    for entry in data:
        block_index = int(entry['start'] // 60)
        block_map[block_index] += ' ' + entry['text']
    
    sorted_blocks = [block_map[i] for i in sorted(block_map.keys())]

    # Wikifier 호출 (1초 딜레이로 API 과부하 방지)
    all_topics = []
    for i, block in enumerate(sorted_blocks):
        print(f"🔎 Wikifier 처리 중: Block {i}")
        topics = wikifier(block[:2000], user_key)  # 최대 2000자 권장
        all_topics.append(topics)
        time.sleep(1)  # API 과부하 방지
    
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
    
    save_summary_to_csv(all_topics, entropy_list, "segment_summary.csv")

    
process_youtube_segments_with_wikifier(json_path, WIKIFIER_USER_KEY)

