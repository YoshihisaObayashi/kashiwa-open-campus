"""
scrape.py — 東京大学柏キャンパス一般公開ページのスクレイパー
トップページ + 各部局ページを巡回して企画情報を抽出する。
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

load_dotenv()

TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://www.kashiwa.u-tokyo.ac.jp/open_campus_2025/"
)
DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "events.db"))

# ---------------------------------------------------------------------------
# 部局ページ URL リスト（ユーザー提供 + トップページから自動検出で補完）
# ---------------------------------------------------------------------------

DEPARTMENT_URLS = [
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/kashiwa-library-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/atomosphere-and-ocean-research-institute-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/graduate-school-of-frontier-sciences-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/gsfs-environmental_studies/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/%e3%82%b0%e3%83%ad%e3%83%bc%e3%83%90%e3%83%ab%e6%95%99%e8%82%b2%e3%82%bb%e3%83%b3%e3%82%bf%e3%83%bc%e6%9f%8f%e6%94%af%e9%83%a8%ef%bc%88kio%ef%bc%89-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/gsfs-biosciences/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/gsfs-transdisciplinary_sciences/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/environmental-science-center-kashiwa-branch-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/the-institute-for-solid-state-physics-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/kavli-institute-for-the-physics-and-mathematics-of-the-universe-utias-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/institute-for-cosmic-ray-research-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/center-for-spatial-information-science-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/the-university-of-tokyo-archives-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/institute-of-industrial-science-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/%e3%83%a2%e3%83%93%e3%83%aa%e3%83%86%e3%82%a3%e3%83%bb%e3%82%a4%e3%83%8e%e3%83%99%e3%83%bc%e3%82%b7%e3%83%a7%e3%83%b3%e9%80%a3%e6%90%ba%e7%a0%94%e7%a9%b6%e6%a9%9f%e6%a7%8b-2-2/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/information-technology-center-2025/",
    "https://www.kashiwa.u-tokyo.ac.jp/departments/2025/%e7%94%a3%e5%ad%a6%e5%ae%98%e6%b0%91%e9%80%a3%e6%90%ba%e6%a3%9f-2-2/",
]


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def compute_hash(data: dict) -> str:
    content = json.dumps(
        {k: v for k, v in data.items() if k not in ("id", "content_hash", "scraped_at")},
        ensure_ascii=False, sort_keys=True
    )
    return hashlib.md5(content.encode()).hexdigest()


def parse_datetime(text: str) -> tuple[str | None, str | None]:
    """
    "10月24日（金）10:00〜16:30" などから ISO8601 を抽出。
    年は TARGET_URL から推定（open_campus_2025 → 2025）。
    """
    year_match = re.search(r"(\d{4})", TARGET_URL)
    year = int(year_match.group(1)) if year_match else datetime.now().year

    # 複数日付の場合は最初の日付を使用
    date_match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if not date_match:
        return None, None
    month, day = int(date_match.group(1)), int(date_match.group(2))

    times = re.findall(r"(\d{1,2}):(\d{2})", text)
    if len(times) >= 2:
        start_h, start_m = times[0]
        end_h, end_m = times[1]
        start_dt = f"{year}-{month:02d}-{day:02d}T{int(start_h):02d}:{start_m}:00"
        end_dt   = f"{year}-{month:02d}-{day:02d}T{int(end_h):02d}:{end_m}:00"
        return start_dt, end_dt
    elif len(times) == 1:
        start_h, start_m = times[0]
        return f"{year}-{month:02d}-{day:02d}T{int(start_h):02d}:{start_m}:00", None
    else:
        return f"{year}-{month:02d}-{day:02d}", None


def normalize_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# 部局ページのイベント抽出
# ---------------------------------------------------------------------------

# カテゴリラベル（タイトルとの区切りに使う）
_CATEGORY_PATTERNS = [
    r"講\s+演",   r"体\s+験",   r"展\s+示",
    r"講演",       r"体験",       r"展示",
    r"実験",       r"見学",       r"ガイドツアー",
    r"トーク",     r"ワークショップ", r"シンポジウム",
    r"セミナー",   r"デモ",
]
_CATEGORY_RE = re.compile("|".join(_CATEGORY_PATTERNS))

# カテゴリの英語表記（除去対象）
_EN_CATEGORIES = [
    "/Lecture", "/Try It Yourself", "/Exhibit", "/Guide Tour",
    "/Workshop", "/Demo", "Lecture", "Try It Yourself",
]


def _extract_dept_name_from_title(title: str) -> str:
    """ページタイトル "部局名 – 東京大学..." から部局名を取得"""
    for sep in ("–", "—", "―", "-"):
        if sep in title:
            return title.split(sep)[0].strip()
    return title.strip()


def _parse_target_audience(text: str) -> str:
    """対象者テキストを日本語に正規化"""
    targets = []
    if re.search(r"幼児|Preschooler", text):
        targets.append("幼児")
    if re.search(r"小学|Elementary", text):
        targets.append("小学生")
    if re.search(r"中学|Junior High", text):
        targets.append("中学生")
    if re.search(r"高校|High School", text):
        targets.append("高校生")
    if re.search(r"大学生|Undergraduate|University", text):
        targets.append("大学生")
    if re.search(r"一般|Adult|どなた", text):
        targets.append("一般")
    if re.search(r"研究者|専門家|Researcher", text):
        targets.append("研究者")
    return "・".join(targets) if targets else "一般"


def _parse_event_block(text: str, dept_name: str, source_url: str) -> dict | None:
    """
    一つのイベントテキストブロックから構造化データを抽出。
    ブロックは「開催日／Date」か「日時／Date」を含む。
    """
    text = text.strip()
    if len(text) < 20:
        return None

    # ── 日付メタデータの開始位置を特定 ──
    meta_start = -1
    for marker in ("開催日／Date", "開催日/Date", "日時／Date", "日時/Date", "開催日\n", "日時\n"):
        idx = text.find(marker)
        if idx > 0:
            meta_start = idx
            break
    if meta_start < 0:
        return None

    header   = text[:meta_start].strip()
    metadata = text[meta_start:]

    # ── タイトルを抽出（カテゴリラベルの前まで）──
    title = header
    cat_match = _CATEGORY_RE.search(header)
    if cat_match and cat_match.start() > 0:
        title = header[: cat_match.start()].strip()

    # 英語カテゴリラベルもクリーンアップ
    for en in _EN_CATEGORIES:
        title = title.replace(en, "")
    title = normalize_text(title)

    # タイトルが短すぎる or 長すぎる場合はスキップ
    if len(title) < 3 or len(title) > 200:
        return None

    # ── 説明文（ヘッダーのうちタイトル以降の部分）──
    desc_raw = header[len(title):].strip() if len(title) < len(header) else ""
    for en in _EN_CATEGORIES:
        desc_raw = desc_raw.replace(en, "")
    desc_raw = re.sub(_CATEGORY_RE, "", desc_raw)
    description = normalize_text(desc_raw[:500])

    # ── 開催日 ──
    date_match = re.search(
        r"開催日[／/]Date\s*(.+?)(?:予約|撮影|場所|対象|定員|$)",
        metadata, re.DOTALL
    )
    if not date_match:
        date_match = re.search(
            r"日時[／/]Date.*?(?:のみ|Only|Anytime|いつでも)?\s*(.+?)(?:予約|撮影|場所|$)",
            metadata, re.DOTALL
        )
    date_text = date_match.group(1).strip() if date_match else ""
    date_start, date_end = parse_datetime(date_text) if date_text else (None, None)

    # ── 予約 ──
    reserve_match = re.search(
        r"予約[／/]Reserve\s*(.+?)(?:撮影|場所|対象|定員|開催日|$)",
        metadata, re.DOTALL
    )
    reserve_text = reserve_match.group(1).strip() if reserve_match else ""
    registration_required = int(bool(re.search(r"^要|Required|必要", reserve_text)))

    # ── 場所 ──
    venue_match = re.search(
        r"場所[／/]Place\s*[｜|]?\s*(.+?)(?:定員|対象|予約|開催日|$)",
        metadata, re.DOTALL
    )
    venue = normalize_text(venue_match.group(1).strip()) if venue_match else ""

    # ── 対象 ──
    target_match = re.search(
        r"対象[／/]For\s*(.+?)(?:定員|予約|開催日|\[企画|$)",
        metadata, re.DOTALL
    )
    target_raw = target_match.group(1).strip() if target_match else ""
    target_audience = _parse_target_audience(target_raw)

    return {
        "title_ja":             title,
        "date_start":           date_start,
        "date_end":             date_end,
        "venue_ja":             venue,
        "description_ja":       description,
        "researchers":          "[]",
        "target_audience_ja":   target_audience,
        "registration_required": registration_required,
        "department_ja":        dept_name,
        "source_url":           source_url,
    }


async def extract_events_from_dept_page(page, dept_url: str) -> list[dict]:
    """
    部局ページを Playwright でレンダリングし、企画一覧を抽出する。
    """
    print(f"  [dept] {dept_url}")
    try:
        await page.goto(dept_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  [dept] WARN: page load timeout/error: {e}")

    # 部局名をページタイトルから取得
    title_el = await page.title()
    dept_name = _extract_dept_name_from_title(title_el)
    print(f"  [dept] 部局名: {dept_name}")

    events = []

    # ── 戦略1: 「開催日」を含む <li> 要素を直接取得 ──
    items = await page.query_selector_all("li")
    for item in items:
        try:
            text = await item.inner_text()
        except Exception:
            continue
        if ("開催日" not in text and "日時" not in text):
            continue
        if len(text) < 30:
            continue
        event = _parse_event_block(text, dept_name, dept_url)
        if event:
            events.append(event)

    # ── 戦略2: <li> で取れない場合は記事本文全体をパース ──
    if not events:
        print(f"  [dept] li strategy failed, trying full-text parse")
        try:
            body_text = await page.inner_text("main")
        except Exception:
            body_text = await page.inner_text("body")

        # 「開催日」で区切って各ブロックを解析
        segments = re.split(r"(?=\S.{5,}開催日[／/]Date)", body_text)
        for seg in segments:
            if "開催日" not in seg and "日時" not in seg:
                continue
            event = _parse_event_block(seg, dept_name, dept_url)
            if event:
                events.append(event)

    # ── 重複除去（同一タイトルを1件に統合）──
    seen: set[str] = set()
    unique: list[dict] = []
    for ev in events:
        key = ev["title_ja"]
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    print(f"  [dept] {len(unique)} events extracted")
    return unique


async def discover_dept_urls_from_top(page, top_url: str) -> list[str]:
    """
    トップページから部局リンク（/departments/2025/）を自動検出。
    DEPARTMENT_URLS に含まれないURLを補完する。
    """
    try:
        await page.goto(top_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        return []

    links = await page.query_selector_all("a[href*='/departments/2025/']")
    found = set(DEPARTMENT_URLS)
    for link in links:
        href = await link.get_attribute("href")
        if href and "/departments/2025/" in href:
            # 相対URLを絶対URLに変換
            if href.startswith("/"):
                href = "https://www.kashiwa.u-tokyo.ac.jp" + href
            if not href.endswith("/"):
                href += "/"
            found.add(href)
    return list(found)


# ---------------------------------------------------------------------------
# データベース保存（差分検出付き）
# ---------------------------------------------------------------------------

def upsert_events(events: list[dict], db_path: str = DB_PATH) -> tuple[int, int]:
    from init_db import init_db
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    new_count = 0
    updated_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        event["scraped_at"]   = now
        event["content_hash"] = compute_hash(event)

        cur.execute(
            "SELECT id, content_hash, translation_edited FROM events "
            "WHERE source_url = ? AND title_ja = ?",
            (event["source_url"], event["title_ja"])
        )
        existing = cur.fetchone()

        if existing is None:
            cols         = ", ".join(event.keys())
            placeholders = ", ".join("?" * len(event))
            cur.execute(
                f"INSERT INTO events ({cols}) VALUES ({placeholders})",
                list(event.values())
            )
            new_count += 1
        elif existing["content_hash"] != event["content_hash"]:
            update_fields = {k: v for k, v in event.items() if k != "id"}
            if existing["translation_edited"]:
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
        (datetime.now(timezone.utc).isoformat(), source_url,
         new_count, updated_count, error_count, notes)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# メインエントリポイント
# ---------------------------------------------------------------------------

async def scrape():
    print(f"[scraper] Top URL: {TARGET_URL}")
    print(f"[scraper] DB: {DB_PATH}")

    from playwright.async_api import async_playwright

    total_new     = 0
    total_updated = 0
    total_errors  = 0
    all_events: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="ja-JP",
            user_agent=(
                "Mozilla/5.0 (compatible; KashiwaOpenCampusBot/1.0; "
                "+https://github.com/YoshihisaObayashi/kashiwa-open-campus)"
            )
        )
        page = await context.new_page()

        # ── トップページから追加の部局URLを検出 ──
        print("[scraper] Discovering department URLs from top page...")
        dept_urls = await discover_dept_urls_from_top(page, TARGET_URL)
        print(f"[scraper] {len(dept_urls)} department pages to scrape")

        # ── 各部局ページをスクレイプ ──
        for url in dept_urls:
            try:
                events = await extract_events_from_dept_page(page, url)
                all_events.extend(events)
            except Exception as e:
                print(f"  [dept] ERROR: {url} → {e}")
                total_errors += 1
            # サーバー負荷軽減のため少し待機
            await asyncio.sleep(2)

        await browser.close()

    print(f"[scraper] Total events collected: {len(all_events)}")

    if all_events:
        total_new, total_updated = upsert_events(all_events)
        print(f"[scraper] New: {total_new}, Updated: {total_updated}")
        await run_translation(DB_PATH)
    else:
        print("[scraper] No events found.")

    log_scrape_run(
        DB_PATH, TARGET_URL,
        total_new, total_updated, total_errors,
        notes=f"dept_pages={len(dept_urls)}"
    )
    print("[scraper] Done.")


async def run_translation(db_path: str):
    """未翻訳レコードを翻訳して DB 更新"""
    from translate import translate_event

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
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
                translated.get("title_en"),
                translated.get("venue_en"),
                translated.get("description_en"),
                translated.get("target_audience_en"),
                translated.get("department_en"),
                translated.get("researchers_en"),
                row["id"]
            )
        )
        conn.commit()
        conn.close()
    print("[translate] Done.")


if __name__ == "__main__":
    asyncio.run(scrape())
