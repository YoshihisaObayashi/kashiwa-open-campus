"""
translate.py — Gemini API による日本語→英語翻訳モジュール
"""
import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-1.5-flash"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
else:
    model = None


TRANSLATE_SYSTEM_PROMPT = """You are a professional academic translator specializing in Japanese to English translation.
Translate the following Japanese text to natural, concise English suitable for an international academic audience.
- Preserve technical terms and proper nouns (names, institutes, etc.) accurately.
- Output ONLY the translated English text, no explanations.
- If the input is already in English or is a proper noun, return it as-is.
"""


def translate_text(text_ja: str, retries: int = 3) -> str:
    """
    単一テキストを日本語→英語に翻訳する。
    Gemini API が未設定の場合は元テキストをそのまま返す。
    """
    if not model or not text_ja or not text_ja.strip():
        return text_ja or ""

    prompt = f"{TRANSLATE_SYSTEM_PROMPT}\n\nJapanese text:\n{text_ja}"

    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"[translate] Retry {attempt+1}/{retries} after {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"[translate] Failed after {retries} attempts: {e}")
                return text_ja  # 失敗時はオリジナルを返す


def translate_researchers(researchers_json: str) -> str:
    """
    研究者名リスト（JSON文字列）を翻訳。
    日本語名はローマ字表記に変換するよう促す。
    """
    if not researchers_json or researchers_json == "[]":
        return "[]"

    try:
        names = json.loads(researchers_json)
    except json.JSONDecodeError:
        return researchers_json

    if not names:
        return "[]"

    prompt = (
        "Convert the following Japanese researcher names to their romanized English equivalents "
        "(Last First format). If a name appears to already be in English/romanized form, return as-is. "
        "Output a JSON array of strings only, no explanation.\n\n"
        f"Input: {json.dumps(names, ensure_ascii=False)}"
    )

    if not model:
        return researchers_json

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            # JSON 配列を抽出
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                return result[start:end]
            return researchers_json
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return researchers_json


def translate_event(event: dict) -> dict:
    """
    イベント辞書の翻訳フィールドをすべて埋める。
    translation_edited=1 のものはスキップ（手動修正済み）。
    """
    if event.get("translation_edited"):
        return event

    fields = {
        "title_en": event.get("title_ja", ""),
        "venue_en": event.get("venue_ja", ""),
        "description_en": event.get("description_ja", ""),
        "target_audience_en": event.get("target_audience_ja", ""),
        "department_en": event.get("department_ja", ""),
    }

    translated = {}
    for key, text in fields.items():
        translated[key] = translate_text(text)
        time.sleep(0.3)  # レート制限対策

    translated["researchers_en"] = translate_researchers(
        event.get("researchers", "[]")
    )

    return {**event, **translated}
