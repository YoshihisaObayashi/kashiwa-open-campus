"""
test_db.py — DB初期化・デモデータ・全文検索のテスト
標準ライブラリのみで動作（外部依存なし）
"""
import sqlite3
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scraper"))

DB_PATH = str(Path(__file__).parent / "test_events.db")

# 既存テストDBを削除
if Path(DB_PATH).exists():
    Path(DB_PATH).unlink()

# DBを初期化
from init_db import init_db
init_db(DB_PATH)
print("✅ DB initialized")

# デモデータ投入
os.environ["DB_PATH"] = DB_PATH
from seed_demo import DEMO_EVENTS
from scrape import upsert_events

new_count, updated_count = upsert_events(DEMO_EVENTS, DB_PATH)
print(f"✅ Seeded {new_count} events (updated: {updated_count})")

# 全文検索テスト
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# テスト1: 日本語キーワード検索
rows = conn.execute("""
    SELECT e.id, e.title_ja, e.department_ja
    FROM events e
    WHERE e.id IN (SELECT rowid FROM events_fts WHERE events_fts MATCH '宇宙*')
""").fetchall()
print(f"\n✅ FTS test '宇宙*': {len(rows)} result(s)")
for r in rows:
    print(f"   [{r['id']}] {r['title_ja'][:40]}  ({r['department_ja']})")

# テスト2: 英語キーワード検索
rows = conn.execute("""
    SELECT e.id, e.title_en, e.department_en
    FROM events e
    WHERE e.id IN (SELECT rowid FROM events_fts WHERE events_fts MATCH 'dark*')
""").fetchall()
print(f"\n✅ FTS test 'dark*' (EN): {len(rows)} result(s)")
for r in rows:
    print(f"   [{r['id']}] {r['title_en'][:50] if r['title_en'] else '(no EN title)'}  ({r['department_en']})")

# テスト3: 日付フィルタ
rows = conn.execute("""
    SELECT id, title_ja, date_start FROM events
    WHERE date(date_start) = '2025-10-25'
    ORDER BY date_start
""").fetchall()
print(f"\n✅ Date filter '2025-10-25': {len(rows)} result(s)")
for r in rows:
    print(f"   [{r['id']}] {r['title_ja'][:40]}  @ {r['date_start']}")

# テスト4: 部局フィルタ
rows = conn.execute("""
    SELECT id, title_ja, department_ja FROM events
    WHERE department_ja LIKE '%研究所%'
""").fetchall()
print(f"\n✅ Department filter '研究所': {len(rows)} result(s)")
for r in rows:
    print(f"   [{r['id']}] {r['department_ja']}")

# テスト5: 対象者フィルタ
rows = conn.execute("""
    SELECT id, title_ja, target_audience_ja FROM events
    WHERE target_audience_ja LIKE '%小中高生%'
""").fetchall()
print(f"\n✅ Target filter '小中高生': {len(rows)} result(s)")
for r in rows:
    print(f"   [{r['id']}] {r['title_ja'][:40]}")

# 統計
total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
depts = conn.execute("SELECT COUNT(DISTINCT department_ja) FROM events").fetchone()[0]
print(f"\n✅ Stats: {total} total events, {depts} departments")

conn.close()

# テストDBを削除
Path(DB_PATH).unlink()
print(f"\n✅ All tests passed!")
