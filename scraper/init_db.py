"""
init_db.py — SQLite データベース初期化スクリプト
FTS5 仮想テーブルによる日英全文検索対応
"""
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "events.db")


def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # --- メインイベントテーブル ---
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            title_ja                TEXT    NOT NULL,
            title_en                TEXT,
            date_start              TEXT,           -- ISO8601 "2025-10-24T10:00:00"
            date_end                TEXT,
            venue_ja                TEXT,
            venue_en                TEXT,
            description_ja          TEXT,
            description_en          TEXT,
            researchers             TEXT,           -- JSON配列: ["山田太郎", ...]
            researchers_en          TEXT,           -- JSON配列（英語名）
            target_audience_ja      TEXT,
            target_audience_en      TEXT,
            registration_required   INTEGER DEFAULT 0,  -- BOOLEAN
            registration_url        TEXT,
            department_ja           TEXT,
            department_en           TEXT,
            source_url              TEXT,
            scraped_at              TEXT,           -- ISO8601
            content_hash            TEXT,           -- MD5 for change detection
            translation_edited      INTEGER DEFAULT 0   -- 1=手動修正済み
        );

        -- FTS5 全文検索インデックス（日英両対応）
        CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
            title_ja,
            title_en,
            description_ja,
            description_en,
            researchers,
            researchers_en,
            department_ja,
            department_en,
            target_audience_ja,
            target_audience_en,
            content='events',
            content_rowid='id',
            tokenize='unicode61'
        );

        -- FTS 同期トリガー
        CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
            INSERT INTO events_fts(rowid, title_ja, title_en, description_ja, description_en,
                researchers, researchers_en, department_ja, department_en,
                target_audience_ja, target_audience_en)
            VALUES (new.id, new.title_ja, new.title_en, new.description_ja, new.description_en,
                new.researchers, new.researchers_en, new.department_ja, new.department_en,
                new.target_audience_ja, new.target_audience_en);
        END;

        CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
            INSERT INTO events_fts(events_fts, rowid, title_ja, title_en, description_ja, description_en,
                researchers, researchers_en, department_ja, department_en,
                target_audience_ja, target_audience_en)
            VALUES ('delete', old.id, old.title_ja, old.title_en, old.description_ja, old.description_en,
                old.researchers, old.researchers_en, old.department_ja, old.department_en,
                old.target_audience_ja, old.target_audience_en);
        END;

        CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
            INSERT INTO events_fts(events_fts, rowid, title_ja, title_en, description_ja, description_en,
                researchers, researchers_en, department_ja, department_en,
                target_audience_ja, target_audience_en)
            VALUES ('delete', old.id, old.title_ja, old.title_en, old.description_ja, old.description_en,
                old.researchers, old.researchers_en, old.department_ja, old.department_en,
                old.target_audience_ja, old.target_audience_en);
            INSERT INTO events_fts(rowid, title_ja, title_en, description_ja, description_en,
                researchers, researchers_en, department_ja, department_en,
                target_audience_ja, target_audience_en)
            VALUES (new.id, new.title_ja, new.title_en, new.description_ja, new.description_en,
                new.researchers, new.researchers_en, new.department_ja, new.department_en,
                new.target_audience_ja, new.target_audience_en);
        END;

        -- 更新ログテーブル
        CREATE TABLE IF NOT EXISTS scrape_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at      TEXT NOT NULL,
            source_url  TEXT,
            new_count   INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            notes       TEXT
        );
    """)

    conn.commit()
    conn.close()
    print(f"[init_db] Database initialized: {db_path}")


if __name__ == "__main__":
    init_db()
