"""
AI 요약 관련 함수들
"""

# 요약 모델을 위한 import
try:
    from transformers import pipeline
    SUMMARIZATION_AVAILABLE = True
except ImportError:
    SUMMARIZATION_AVAILABLE = False
    print("⚠️ transformers 라이브러리가 설치되지 않아 요약 기능을 사용할 수 없습니다.")


def generate_summary(text: str, language_code: str = 'ko') -> str:
    import torch
    """
    주어진 텍스트를 AI 모델을 사용하여 요약합니다.
    
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
            model_name = "digit82/kobart-summarization"  # 한국어 요약 모델
        else:
            model_name = "facebook/bart-large-cnn"  # 영어 요약 모델
        
        summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=model_name,
            device=-1  # CPU 사용 (GPU가 없거나 메모리 부족 시)
        )
        
        # 텍스트 길이 제한 (모델 제한 고려)
        max_input_length = 1024
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


def batch_generate_summaries(texts: list, language_code: str = 'ko') -> list:
    """
    여러 텍스트를 일괄적으로 요약합니다.
    
    Args:
        texts (list): 요약할 텍스트 리스트
        language_code (str): 언어 코드
    
    Returns:
        list: 요약된 텍스트 리스트
    """
    if not SUMMARIZATION_AVAILABLE:
        return ["요약 생성에 필요한 라이브러리가 설치되어 있지 않습니다."] * len(texts)
    
    summaries = []
    for i, text in enumerate(texts):
        print(f"🤖 텍스트 {i+1}/{len(texts)} 요약 생성 중...")
        summary = generate_summary(text, language_code)
        summaries.append(summary)
    
    return summaries
