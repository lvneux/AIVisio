"""
시간 변환 및 유틸리티 함수들
"""

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