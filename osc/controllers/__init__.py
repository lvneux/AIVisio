"""
Controllers package for OSC analysis
"""

from osc.controllers.youtube_api import get_youtube_chapters, get_youtube_video_info
from osc.controllers.transcript import extract_transcript
from osc.controllers.segments import segment_video_by_description, map_subtitles_to_segments
from osc.controllers.file_io import save_segments_to_json, save_segments_to_txt, save_segments_with_subtitles_to_json
from osc.controllers.summary import generate_summary, batch_generate_summaries

__all__ = [
    'get_youtube_chapters',
    'get_youtube_video_info', 
    'extract_transcript',
    'segment_video_by_description',
    'map_subtitles_to_segments',
    'save_segments_to_json',
    'save_segments_to_txt',
    'save_segments_with_subtitles_to_json',
    'generate_summary',
    'batch_generate_summaries'
]
