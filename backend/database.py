"""
database.py — SQLite 接続・クエリヘルパー
"""
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "events.db"))


def _ensure_db() -> None:
    """DB ファイルが存在しない場合、最低限のスキーマを初期化する"""
    from pathlib import Path as _Path
    import sys as _sys
    db = _Path(DB_PATH)
    if db.exists():
        return
    db.parent.mkdir(parents=True, exist_ok=True)
    # scraper の init_db を使う（同梱されていない場合はインラインで作成）
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            title_ja            TEXT NOT NULL,
            title_en            TEXT,
            date_start          TEXT,
            date_end            TEXT,
            venue_ja            TEXT,
            venue_en            TEXT,
            description_ja      TEXT,
            description_en      TEXT,
            researchers         TEXT DEFAULT '[]',
            researchers_en      TEXT DEFAULT '[]',
            target_audience_ja  TEXT,
            target_audience_en  TEXT,
            registration_required INTEGER DEFAULT 0,
            registration_url    TEXT,
            department_ja       TEXT,
            department_en       TEXT,
            source_url          TEXT,
            scraped_at          TEXT,
            content_hash        TEXT,
            translation_edited  INTEGER DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
            USING fts5(title_ja, title_en, description_ja, description_en,
                       department_ja, department_en, researchers,
                       content=events, content_rowid=id);
        CREATE TABLE IF NOT EXISTS scrape_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at        TEXT,
            source_url    TEXT,
            new_count     INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            error_count   INTEGER DEFAULT 0,
            notes         TEXT
        );
    """)
    conn.close()


def get_conn() -> sqlite3.Connection:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # JSON 配列フィールドをパース
    for field in ("researchers", "researchers_en"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []
    return d


def search_events(
    q: str | None = None,
    date: str | None = None,
    department: str | None = None,
    target: str | None = None,
    lang: str = "ja",
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """
    全文検索 + フィルタリング。
    FTS5 を使った日英両対応検索。
    """
    conn = get_conn()
    offset = (page - 1) * limit

    conditions = []
    params: list[Any] = []

    # --- 全文検索 (FTS5) ---
    if q and q.strip():
        # FTS サブクエリで rowid を取得
        fts_query = q.strip() + "*"  # 前方一致
        conditions.append("""
            e.id IN (
                SELECT rowid FROM events_fts
                WHERE events_fts MATCH ?
            )
        """)
        params.append(fts_query)

    # --- 日付フィルタ ---
    if date:
        conditions.append("date(e.date_start) = date(?)")
        params.append(date)

    # --- 部局フィルタ ---
    if department:
        col = "department_en" if lang == "en" else "department_ja"
        conditions.append(f"e.{col} LIKE ?")
        params.append(f"%{department}%")

    # --- 対象者フィルタ ---
    if target:
        col = "target_audience_en" if lang == "en" else "target_audience_ja"
        conditions.append(f"e.{col} LIKE ?")
        params.append(f"%{target}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # カウント
    count_sql = f"SELECT COUNT(*) FROM events e {where}"
    total = conn.execute(count_sql, params).fetchone()[0]

    # データ取得
    data_sql = f"""
        SELECT e.* FROM events e {where}
        ORDER BY e.date_start ASC NULLS LAST, e.id ASC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(data_sql, [*params, limit, offset]).fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [row_to_dict(r) for r in rows],
    }


def get_event_by_id(event_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_departments(lang: str = "ja") -> list[str]:
    conn = get_conn()
    col = "department_en" if lang == "en" else "department_ja"
    rows = conn.execute(
        f"SELECT DISTINCT {col} FROM events WHERE {col} IS NOT NULL AND {col} != '' ORDER BY {col}"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    with_date = conn.execute(
        "SELECT COUNT(*) FROM events WHERE date_start IS NOT NULL"
    ).fetchone()[0]
    departments = conn.execute(
        "SELECT COUNT(DISTINCT department_ja) FROM events"
    ).fetchone()[0]
    last_scrape = conn.execute(
        "SELECT run_at FROM scrape_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_update = conn.execute(
        "SELECT MAX(scraped_at) FROM events"
    ).fetchone()[0]
    conn.close()
    return {
        "total_events": total,
        "events_with_date": with_date,
        "departments": departments,
        "last_scrape": last_scrape[0] if last_scrape else None,
        "last_event_update": last_update,
    }


def update_event_translation(
    event_id: int,
    updates: dict,
) -> bool:
    """
    翻訳フィールドを手動で更新し、translation_edited=1 をセット。
    """
    allowed_fields = {
        "title_en", "venue_en", "description_en",
        "target_audience_en", "department_en", "researchers_en"
    }
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered:
        return False

    filtered["translation_edited"] = 1
    set_clause = ", ".join(f"{k} = ?" for k in filtered)

    conn = get_conn()
    result = conn.execute(
        f"UPDATE events SET {set_clause} WHERE id = ?",
        [*filtered.values(), event_id]
    )
    conn.commit()
    conn.close()
    return result.rowcount > 0
