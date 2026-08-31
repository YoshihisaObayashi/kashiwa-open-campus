"""
translate.py — Gemini API による日本語→英語翻訳モジュール
全フィールドを1回のAPIコールでまとめて翻訳（高速・低コスト）。
"""
import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# gemini-2.0-flash-lite: 高速・低コスト。gemini-2.0-flash でも可。
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
else:
    model = None


# ---------------------------------------------------------------------------
# バッチ翻訳（1イベントを1回のAPIコールで処理）
# ---------------------------------------------------------------------------

_BATCH_PROMPT_TEMPLATE = """You are a professional academic translator (Japanese → English).
Translate the following fields of a university open campus event.
Rules:
- Output valid JSON only, with exactly the same keys as the input.
- Translate naturally and concisely for an international academic audience.
- Preserve proper nouns, institute names, and technical terms accurately.
- For "researchers": convert Japanese names to "Given Family" romanized format (e.g. 山田太郎 → Taro Yamada). Return a JSON array of strings.
- If a field is empty ("") or already in English, return it unchanged.
- Do NOT add any explanation outside the JSON.

Input JSON:
{input_json}

Output (JSON only):"""


def translate_event(event: dict) -> dict:
    """
    イベント辞書の全翻訳フィールドを1回のAPIコールで埋める。
    translation_edited=1 のものはスキップ（手動修正済み）。
    """
    if event.get("translation_edited"):
        return event

    if not model:
        # API キー未設定時はそのまま返す
        return {
            **event,
            "title_en":          event.get("title_ja", ""),
            "venue_en":          event.get("venue_ja", ""),
            "description_en":    event.get("description_ja", ""),
            "target_audience_en": event.get("target_audience_ja", ""),
            "department_en":     event.get("department_ja", ""),
            "researchers_en":    event.get("researchers", "[]"),
        }

    # 翻訳対象フィールドをまとめる
    researchers_raw = event.get("researchers", "[]")
    try:
        researchers_list = json.loads(researchers_raw) if researchers_raw else []
    except (json.JSONDecodeError, TypeError):
        researchers_list = []

    input_payload = {
        "title":          event.get("title_ja", ""),
        "venue":          event.get("venue_ja", ""),
        "description":    event.get("description_ja", ""),
        "target_audience": event.get("target_audience_ja", ""),
        "department":     event.get("department_ja", ""),
        "researchers":    researchers_list,
    }

    prompt = _BATCH_PROMPT_TEMPLATE.format(
        input_json=json.dumps(input_payload, ensure_ascii=False, indent=2)
    )

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # ```json ... ``` ブロックがある場合は中身だけ取り出す
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)

            # researchers を JSON 文字列に戻す
            researchers_en = result.get("researchers", researchers_list)
            if isinstance(researchers_en, list):
                researchers_en = json.dumps(researchers_en, ensure_ascii=False)

            return {
                **event,
                "title_en":          str(result.get("title", "")),
                "venue_en":          str(result.get("venue", "")),
                "description_en":    str(result.get("description", "")),
                "target_audience_en": str(result.get("target_audience", "")),
                "department_en":     str(result.get("department", "")),
                "researchers_en":    researchers_en,
            }

        except json.JSONDecodeError as e:
            print(f"[translate] JSON parse error (attempt {attempt+1}/3): {e}")
            print(f"[translate] Raw response: {raw[:200]}")
            if attempt < 2:
                time.sleep(2 ** attempt)

        except Exception as e:
            wait = 2 ** attempt
            print(f"[translate] Retry {attempt+1}/3 after {wait}s: {e}")
            if attempt < 2:
                time.sleep(wait)
            else:
                print(f"[translate] Failed, keeping Japanese text for: {event.get('title_ja', '')}")
                return {
                    **event,
                    "title_en":          event.get("title_ja", ""),
                    "venue_en":          event.get("venue_ja", ""),
                    "description_en":    event.get("description_ja", ""),
                    "target_audience_en": event.get("target_audience_ja", ""),
                    "department_en":     event.get("department_ja", ""),
                    "researchers_en":    researchers_raw,
                }

    # ここまで到達した場合（JSONエラーが3回続いた）
    return {
        **event,
        "title_en":          event.get("title_ja", ""),
        "venue_en":          event.get("venue_ja", ""),
        "description_en":    event.get("description_ja", ""),
        "target_audience_en": event.get("target_audience_ja", ""),
        "department_en":     event.get("department_ja", ""),
        "researchers_en":    researchers_raw,
    }
