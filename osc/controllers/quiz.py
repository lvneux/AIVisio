import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from openai import OpenAI

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("quiz")

OPENAI_API_KEY = "openai"
_client = OpenAI(api_key=OPENAI_API_KEY)

MODEL_FOR_GEN = "gpt-4o-mini"
MODEL_FOR_JUDGE = "gpt-4o-mini"

def _build_gen_prompt(chapter_title: str, context_text: str) -> List[Dict[str, str]]:
    """
    Build a chat prompt to generate 3 quizzes grounded in the provided summary (context_text).
    """
    sys_msg = (
        "당신은 학습 내용을 평가하기 위한 퀴즈를 생성합니다. "
        "반드시 JSON만 반환해야 하며, 설명이나 마크다운은 포함하지 마세요."
        'JSON 형식: {"quizzes": [{"type": "OX"|"short", "question": "...", "answer": "..."}]} '
        "항상 3개의 문항만 생성하세요. 질문은 간결하고 모호하지 않게 작성하세요. "
        "반드시 제공된 요약(Context)에 기반하여 질문을 생성하세요."
    )

    user_msg = (
        f"# 챕터 제목\n{chapter_title}\n\n"
        f"# 요약 (해당 챕터의 내용)\n{context_text or '(요약 없음)'}\n\n"
        "위 내용을 바탕으로 퀴즈 3개를 생성하세요. 문항 유형은 OX만 생성합니다.\n"
        "- OX : 문제의 정답은 반드시 'O' 또는 'X'입니다.\n"
        "각 문항은 반드시 위의 요약(Context)에 기반 해야합니다."
    )

    return [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]

def generate_quizzes(chapter_title: str, context_text: str) -> List[Dict[str, Any]]:
    """
    Generate exactly 3 quizzes using the given chapter title and its summary text (context_text).
    Robust against older openai clients and non-JSON outputs.
    Returns: List[{"type": "OX"|"short", "question": str, "answer": str}] (length 3)
    """
    try:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set in environment.")

        msgs = _build_gen_prompt(chapter_title, context_text)

        try:
            resp = _client.chat.completions.create(
                model=MODEL_FOR_GEN,
                messages=msgs,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
        except Exception as e_json_mode:
            LOGGER.warning(f"[quiz] JSON mode failed, fallback to text mode: {e_json_mode}")

            resp = _client.chat.completions.create(
                model=MODEL_FOR_GEN,
                messages=msgs,
                temperature=0.2,
            )
            raw = resp.choices[0].message.content

        data = None
        # (a) direct JSON
        try:
            data = json.loads(raw)
        except Exception:
            # (b) extract largest JSON object via regex
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception as e_sub:
                    LOGGER.error(f"[quiz] JSON substring parse failed: {e_sub}\nRAW:\n{raw}")
            else:
                LOGGER.error(f"[quiz] No JSON found in model output.\nRAW:\n{raw}")

        if not isinstance(data, dict) or "quizzes" not in data:
            raise ValueError("Model output did not contain expected JSON with 'quizzes'.")

        quizzes = data.get("quizzes", [])
        out: List[Dict[str, Any]] = []

        for q in quizzes[:3]:
            t_raw = str(q.get("type", "")).strip()
            t = "OX" if t_raw.upper() in ["OX", "O/X", "TF", "T/F", "TRUE/FALSE"] else "short"
            question = str(q.get("question", "")).strip()
            answer = str(q.get("answer", "")).strip()
            if t == "OX":
                answer = "O" if answer.upper().startswith("O") else "X"
            out.append({"type": t, "question": question, "answer": answer})

        # Ensure exactly 3
        while len(out) < 3:
            out.append({"type": "OX", "question": "이 명제가 참이면 O, 거짓이면 X:", "answer": "O"})
        return out[:3]

    except Exception as e:
        # If you keep seeing this fallback, check logs for the root cause.
        LOGGER.exception(f"[quiz] Falling back to default quizzes due to: {e}")
        return [
            {"type": "OX", "question": "요약에 언급된 내용이 사실이면 O, 아니면 X를 고르세요. (O/X)", "answer": "O"},
            {"type": "short", "question": "요약에서 강조된 핵심 키워드를 한 단어로 쓰세요.", "answer": "핵심"},
            {"type": "OX", "question": "요약은 긴 내용을 압축해 제공한다. (O/X)", "answer": "O"},
        ]


def check_answer(quiz: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    """
    Judge correctness. For OX: strict O/X. For short: simple normalization first, then LLM judge.
    Returns: {"correct": bool, "feedback": str}
    """
    q_type = quiz.get("type", "short")
    gt = str(quiz.get("answer", "")).strip()
    ua = str(user_answer or "").strip()

    if q_type == "OX":
        ua_norm = "O" if ua.upper().startswith("O") else ("X" if ua.upper().startswith("X") else ua.upper())
        correct = (ua_norm == ("O" if gt.upper().startswith("O") else "X"))
        return {"correct": correct, "feedback": "" if correct else "오답입니다. 다시 시도해 보세요."}

    # short: quick normalization
    if gt and ua:
        if _normalize_text(gt) in _normalize_text(ua) or _normalize_text(ua) in _normalize_text(gt):
            return {"correct": True, "feedback": ""}

    try:
        judge_system = (
            "You are a strict short-answer judge. "
            "Given the question, ground-truth short answer, and user answer, "
            'reply JSON ONLY: {"correct": true|false, "hint": "..."} . '
            "Accept minor synonyms/typos if meaning matches."
        )
        judge_user = (
            f"Question: {quiz.get('question','')}\n"
            f"Ground Truth: {gt}\n"
            f"User Answer: {ua}\n"
            "Is the user answer correct?"
        )
        resp = _client.chat.completions.create(
            model=MODEL_FOR_JUDGE,
            messages=[{"role": "system", "content": judge_system},
                      {"role": "user", "content": judge_user}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        j = json.loads(resp.choices[0].message.content)
        correct = bool(j.get("correct", False))
        if correct:
            return {"correct": True, "feedback": ""}
        else:
            hint = j.get("hint", "오답입니다. 다시 시도해 보세요.")
            return {"correct": False, "feedback": hint}
    except Exception as e:
        LOGGER.warning(f"[quiz] LLM judge failed, use conservative fallback: {e}")
        return {"correct": False, "feedback": "오답입니다. 다시 시도해 보세요."}

def _normalize_text(s: str) -> str:
    return "".join(s.lower().strip().split())


def _parse_timecode(ts: Optional[str]) -> Optional[int]:
    if ts is None:
        return None
    try:
        parts = [int(p) for p in str(ts).strip().split(":")]
        sec = 0
        for p in parts:
            sec = sec * 60 + p
        return sec
    except Exception:
        return None

def build_context_from_json(json_path: Path, chapter_title: str) -> str:
    """
    Read the segments JSON and concatenate summaries for the given chapter_title.
    """
    if not json_path.exists():
        return ""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = None
        for key in ["segments", "data", "items", "results"]:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        items = items or []
    else:
        items = []

    summaries = [it.get("summary", "") for it in items if it.get("title") == chapter_title and it.get("summary")]
    return "\n\n".join([s for s in summaries if s]).strip()


def generate_quizzes_from_json(chapter_title: str, json_path: Path) -> List[Dict[str, Any]]:
    """
    Convenience wrapper: builds context from the given JSON and calls generate_quizzes.
    """
    context_text = build_context_from_json(json_path, chapter_title)
    return generate_quizzes(chapter_title, context_text)
