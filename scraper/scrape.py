"""
scrape.py — 東京大学柏キャンパス一般公開ページのスクレイパー
Playwright によるヘッドレスブラウザで JS レンダリング後にコンテンツ取得
"""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(): pass

# playwright は scrape() 実行時のみインポート（DB ユーティリティのテストには不要）

load_dotenv()

TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/"
)
DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "events.db"))


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def compute_hash(data: dict) -> str:
    """イベントデータの変更検出用ハッシュを計算"""
    content = json.dumps(
        {k: v for k, v in data.items() if k not in ("id", "content_hash", "scraped_at")},
        ensure_ascii=False, sort_keys=True
    )
    return hashlib.md5(content.encode()).hexdigest()


def parse_datetime(text: str) -> tuple[str | None, str | None]:
    """
    "10月24日（金）10:00〜16:30" などの形式から ISO8601 を抽出。
    年は TARGET_URL から推定（open_campus_2025 → 2025）。
    """
    year_match = re.search(r"(\d{4})", TARGET_URL)
    year = int(year_match.group(1)) if year_match else datetime.now().year

    # "M月D日" パターン
    date_match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if not date_match:
        return None, None
    month, day = int(date_match.group(1)), int(date_match.group(2))

    # "HH:MM〜HH:MM" パターン
    times = re.findall(r"(\d{1,2}):(\d{2})", text)
    if len(times) >= 2:
        start_h, start_m = times[0]
        end_h, end_m = times[1]
        start_dt = f"{year}-{month:02d}-{day:02d}T{int(start_h):02d}:{start_m}:00"
        end_dt   = f"{year}-{month:02d}-{day:02d}T{int(end_h):02d}:{end_m}:00"
        return start_dt, end_dt
    elif len(times) == 1:
        start_h, start_m = times[0]
        start_dt = f"{year}-{month:02d}-{day:02d}T{int(start_h):02d}:{start_m}:00"
        return start_dt, None
    else:
        return f"{year}-{month:02d}-{day:02d}", None


def normalize_text(text: str) -> str:
    """HTML タグ除去・空白正規化"""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# スクレイピングロジック
# ---------------------------------------------------------------------------

async def extract_events_from_page(page) -> list[dict]:
    """
    一般公開ページから企画情報を抽出する。
    サイト構造に合わせてセレクタを調整すること。
    """
    events = []

    # ページが完全に読み込まれるまで待機
    await page.wait_for_load_state("networkidle", timeout=30000)
    await page.wait_for_timeout(2000)  # 追加待機（動的コンテンツ対応）

    # --- 戦略1: テーブル形式の企画一覧 ---
    # 多くの大学公開ページは <table> でプログラムを列挙する
    tables = await page.query_selector_all("table")
    for table in tables:
        rows = await table.query_selector_all("tr")
        for row in rows:
            cells = await row.query_selector_all("td, th")
            if len(cells) < 2:
                continue
            texts = [await c.inner_text() for c in cells]
            event = _parse_table_row(texts)
            if event:
                events.append(event)

    # --- 戦略2: セクション/カード形式 ---
    # <section>, <article>, <div class="event*|program*|plan*"> など
    if not events:
        selectors = [
            ".event-item", ".program-item", ".plan-item",
            "article", ".wp-block-group", ".entry-content > div",
            "[class*='event']", "[class*='program']", "[class*='plan']"
        ]
        for sel in selectors:
            items = await page.query_selector_all(sel)
            if len(items) > 2:
                for item in items:
                    text = await item.inner_text()
                    event = _parse_free_text(text)
                    if event:
                        events.append(event)
                break

    # --- 戦略3: ページ全体のテキストから構造化抽出 ---
    if not events:
        full_text = await page.inner_text("body")
        events = _parse_full_text(full_text)

    return events


def _parse_table_row(cells: list[str]) -> dict | None:
    """テーブル行からイベント情報を組み立てる"""
    # 最低限タイトルらしいテキストがあること
    if not any(len(c.strip()) > 5 for c in cells):
        return None

    # ヘッダー行を除外
    header_keywords = ["企画名", "内容", "日時", "場所", "タイトル", "開催", "title", "date"]
    if any(kw in cells[0].lower() for kw in header_keywords):
        return None

    date_start, date_end = None, None
    venue = ""
    description = ""
    department = ""
    researchers = []

    for cell in cells:
        cell = cell.strip()
        if re.search(r"\d+月\d+日", cell):
            date_start, date_end = parse_datetime(cell)
        elif any(kw in cell for kw in ["会場", "場所", "棟", "号館", "研究所", "センター"]):
            venue = cell
        elif any(kw in cell for kw in ["教授", "准教授", "講師", "研究員", "博士"]):
            researchers = [r.strip() for r in re.split(r"[、,・]", cell) if r.strip()]
        elif len(cell) > 20:
            description = cell

    title = cells[0].strip() if cells else ""
    if len(title) < 3:
        return None

    return {
        "title_ja": normalize_text(title),
        "date_start": date_start,
        "date_end": date_end,
        "venue_ja": normalize_text(venue),
        "description_ja": normalize_text(description or " ".join(cells[1:])),
        "researchers": json.dumps(researchers, ensure_ascii=False),
        "target_audience_ja": _extract_target(description),
        "registration_required": int(bool(re.search(r"要予約|事前申込|申し込み", " ".join(cells)))),
        "department_ja": normalize_text(department),
        "source_url": TARGET_URL,
    }


def _parse_free_text(text: str) -> dict | None:
    """フリーテキストブロックからイベント情報を抽出"""
    text = text.strip()
    if len(text) < 20:
        return None

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    title = lines[0]
    body = " ".join(lines[1:])

    date_start, date_end = None, None
    for line in lines:
        if re.search(r"\d+月\d+日|\d{4}-\d{2}-\d{2}", line):
            date_start, date_end = parse_datetime(line)
            break

    researchers = []
    for line in lines:
        if any(kw in line for kw in ["教授", "准教授", "講師", "研究員"]):
            researchers = [r.strip() for r in re.split(r"[、,・\s]+", line)
                          if r.strip() and len(r.strip()) > 1]

    return {
        "title_ja": normalize_text(title),
        "date_start": date_start,
        "date_end": date_end,
        "venue_ja": "",
        "description_ja": normalize_text(body[:500]),
        "researchers": json.dumps(researchers, ensure_ascii=False),
        "target_audience_ja": _extract_target(body),
        "registration_required": int(bool(re.search(r"要予約|事前申込|申し込み", text))),
        "department_ja": "",
        "source_url": TARGET_URL,
    }


def _parse_full_text(text: str) -> list[dict]:
    """
    ページ全体テキストから部局セクションごとに分割して抽出。
    各部局見出しの後に続く企画情報を収集する。
    """
    departments = [
        "大学院新領域創成科学研究科", "宇宙線研究所", "物性研究所", "大気海洋研究所",
        "カブリ数物連携宇宙研究機構", "Kavli IPMU", "空間情報科学研究センター",
        "生産技術研究所", "情報基盤センター", "柏図書館", "環境安全研究センター",
        "文書館", "グローバル教育センター", "モビリティ・イノベーション連携研究機構",
        "産学官民連携棟", "国立情報学研究所",
    ]

    events = []
    current_dept = ""

    for dept in departments:
        idx = text.find(dept)
        if idx < 0:
            continue

        # 部局名の後の500文字を解析
        snippet = text[idx: idx + 800]
        lines = [l.strip() for l in snippet.split("\n") if l.strip()]

        current_dept = dept
        for i, line in enumerate(lines[1:], 1):
            if len(line) < 5:
                continue
            if any(d in line for d in departments if d != dept):
                break  # 次の部局セクション開始

            # 企画タイトルらしい行を探す
            if (len(line) > 8 and
                not re.match(r"^\d", line) and
                not any(line.startswith(kw) for kw in ["tel", "fax", "http", "〒", "※"])):

                body = " ".join(lines[i+1:i+5]) if i+1 < len(lines) else ""
                date_start, date_end = None, None
                for search_line in lines[i:i+5]:
                    if re.search(r"\d+月\d+日", search_line):
                        date_start, date_end = parse_datetime(search_line)
                        break

                events.append({
                    "title_ja": normalize_text(line),
                    "date_start": date_start,
                    "date_end": date_end,
                    "venue_ja": "",
                    "description_ja": normalize_text(body[:400]),
                    "researchers": "[]",
                    "target_audience_ja": _extract_target(body),
                    "registration_required": int(bool(re.search(r"要予約|事前申込", body))),
                    "department_ja": current_dept,
                    "source_url": TARGET_URL,
                })

    return events


def _extract_target(text: str) -> str:
    """対象者を抽出"""
    targets = []
    if re.search(r"小学|中学|高校|小・中", text):
        targets.append("小中高生")
    if re.search(r"一般|どなた", text):
        targets.append("一般市民")
    if re.search(r"大学生|学部生", text):
        targets.append("大学生")
    if re.search(r"研究者|専門家", text):
        targets.append("研究者")
    return "、".join(targets) if targets else "一般"


# ---------------------------------------------------------------------------
# データベース保存（差分検出付き）
# ---------------------------------------------------------------------------

def upsert_events(events: list[dict], db_path: str = DB_PATH) -> tuple[int, int]:
    """
    イベントリストを DB に保存。
    content_hash で差分検出し、変更があったレコードのみ更新。
    Returns: (new_count, updated_count)
    """
    from init_db import init_db
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    new_count = 0
    updated_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        event["scraped_at"] = now
        event["content_hash"] = compute_hash(event)

        # 既存レコードを source_url + title_ja で検索
        cur.execute(
            "SELECT id, content_hash, translation_edited FROM events "
            "WHERE source_url = ? AND title_ja = ?",
            (event["source_url"], event["title_ja"])
        )
        existing = cur.fetchone()

        if existing is None:
            # 新規挿入
            cols = ", ".join(event.keys())
            placeholders = ", ".join("?" * len(event))
            cur.execute(
                f"INSERT INTO events ({cols}) VALUES ({placeholders})",
                list(event.values())
            )
            new_count += 1
        elif existing["content_hash"] != event["content_hash"]:
            # 内容変更あり → 更新（ただし translation_edited=1 の翻訳フィールドは保持）
            update_fields = {k: v for k, v in event.items()
                            if k not in ("id",)}
            if existing["translation_edited"]:
                # 手動修正済みの翻訳フィールドはスキップ
                for field in ("title_en", "venue_en", "description_en",
                              "target_audience_en", "department_en", "researchers_en"):
                    update_fields.pop(field, None)

            set_clause = ", ".join(f"{k} = ?" for k in update_fields)
            cur.execute(
                f"UPDATE events SET {set_clause} WHERE id = ?",
                [*update_fields.values(), existing["id"]]
            )
            updated_count += 1

    conn.commit()
    conn.close()
    return new_count, updated_count


def log_scrape_run(db_path: str, source_url: str, new_count: int,
                   updated_count: int, error_count: int, notes: str = ""):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO scrape_log (run_at, source_url, new_count, updated_count, error_count, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), source_url, new_count, updated_count, error_count, notes)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# メインエントリポイント
# ---------------------------------------------------------------------------

async def scrape():
    print(f"[scraper] Target: {TARGET_URL}")
    print(f"[scraper] DB: {DB_PATH}")

    from playwright.async_api import async_playwright  # 実行時のみインポート

    error_count = 0
    events = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            locale="ja-JP",
            user_agent=(
                "Mozilla/5.0 (compatible; KashiwaOpenCampusBot/1.0; "
                "+https://github.com/your-org/kashiwa-open-campus)"
            )
        )

        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            events = await extract_events_from_page(page)
            print(f"[scraper] Extracted {len(events)} events")
        except Exception as e:
            print(f"[scraper] ERROR: {e}")
            error_count += 1
        finally:
            await browser.close()

    if events:
        new_count, updated_count = upsert_events(events)
        print(f"[scraper] New: {new_count}, Updated: {updated_count}")

        # 翻訳実行（未翻訳レコードのみ）
        await run_translation(DB_PATH)
    else:
        new_count, updated_count = 0, 0

    log_scrape_run(DB_PATH, TARGET_URL, new_count, updated_count, error_count)
    print("[scraper] Done.")


async def run_translation(db_path: str):
    """未翻訳または翻訳前のレコードを翻訳してDB更新"""
    from translate import translate_event

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # title_en が NULL または空のものを対象
    cur.execute(
        "SELECT * FROM events WHERE (title_en IS NULL OR title_en = '') "
        "AND translation_edited = 0"
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    print(f"[translate] Translating {len(rows)} events...")

    for row in rows:
        translated = translate_event(row)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """UPDATE events SET
                title_en=?, venue_en=?, description_en=?,
                target_audience_en=?, department_en=?, researchers_en=?
               WHERE id=?""",
            (
                translated.get("title_en"), translated.get("venue_en"),
                translated.get("description_en"), translated.get("target_audience_en"),
                translated.get("department_en"), translated.get("researchers_en"),
                row["id"]
            )
        )
        conn.commit()
        conn.close()

    print(f"[translate] Done.")


if __name__ == "__main__":
    asyncio.run(scrape())
