"""
main.py — FastAPI バックエンド
柏キャンパス一般公開 イベント検索 API
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, Security, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    get_departments,
    get_event_by_id,
    get_stats,
    search_events,
    update_event_translation,
)

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "change-me-in-production")
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://your-app.vercel.app"
).split(",")

# ---------------------------------------------------------------------------
# FastAPI アプリ
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UTokyo Kashiwa Open Campus API",
    description="東京大学柏キャンパス一般公開 イベント検索 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def verify_admin_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------

class EventTranslationUpdate(BaseModel):
    title_en: str | None = None
    venue_en: str | None = None
    description_en: str | None = None
    target_audience_en: str | None = None
    department_en: str | None = None
    researchers_en: list[str] | None = None

    model_config = {"extra": "ignore"}


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "UTokyo Kashiwa Open Campus API"}


@app.get("/api/events", tags=["Events"])
async def list_events(
    q: Annotated[str | None, Query(description="全文検索キーワード")] = None,
    date: Annotated[str | None, Query(description="日付フィルタ (YYYY-MM-DD)")] = None,
    department: Annotated[str | None, Query(description="部局名（部分一致）")] = None,
    target: Annotated[str | None, Query(description="対象者（部分一致）")] = None,
    lang: Annotated[str, Query(description="言語 (ja|en)")] = "ja",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    企画一覧の検索・フィルタリング。

    - **q**: 日本語または英語のキーワードで全文検索
    - **date**: 特定日のイベントのみ取得 (例: `2025-10-24`)
    - **department**: 部局名での絞り込み
    - **target**: 対象者での絞り込み（例: `小中高生`, `一般市民`）
    - **lang**: `ja`（デフォルト）または `en` で返却フィールドを選択
    """
    return search_events(
        q=q, date=date, department=department,
        target=target, lang=lang, page=page, limit=limit
    )


@app.get("/api/events/{event_id}", tags=["Events"])
async def get_event(event_id: int):
    """特定の企画の詳細情報を返す"""
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/api/departments", tags=["Metadata"])
async def list_departments(
    lang: Annotated[str, Query(description="言語 (ja|en)")] = "ja"
):
    """参加部局の一覧を返す"""
    return {"departments": get_departments(lang)}


@app.get("/api/stats", tags=["Metadata"])
async def stats():
    """データベースの統計情報（総件数、最終更新日時など）"""
    return get_stats()


@app.patch("/api/admin/events/{event_id}", tags=["Admin"])
async def update_translation(
    event_id: int,
    body: EventTranslationUpdate,
    _: str = Security(verify_admin_key),
):
    """
    [管理者専用] 英語翻訳フィールドを手動で更新する。
    X-API-Key ヘッダーに管理者キーを指定してください。
    更新後は `translation_edited=1` が設定され、自動翻訳でも上書きされなくなります。
    """
    updates = body.model_dump(exclude_none=True)
    if "researchers_en" in updates:
        import json
        updates["researchers_en"] = json.dumps(updates["researchers_en"], ensure_ascii=False)

    ok = update_event_translation(event_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True, "event_id": event_id}


@app.post("/api/admin/refresh", tags=["Admin"])
async def trigger_scrape(
    _: str = Security(verify_admin_key),
):
    """
    [管理者専用] スクレイパーを手動実行してDBを更新する。
    完了まで最大60秒かかる場合があります。
    """
    scraper_path = Path(__file__).parent.parent / "scraper" / "scrape.py"
    if not scraper_path.exists():
        raise HTTPException(status_code=500, detail="Scraper not found")

    try:
        result = subprocess.run(
            [sys.executable, str(scraper_path)],
            capture_output=True, text=True, timeout=120
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Scraper timed out"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/db-sync", tags=["Admin"])
async def upload_db(
    db: UploadFile = File(...),
    _: str = Security(verify_admin_key),
):
    """
    [管理者専用] GitHub Actions から最新の SQLite DB をアップロードする。
    スクレイパーが外部（GitHub Actions）で動作する場合に使用。
    """
    db_path = os.environ.get("DB_PATH", "/data/events.db")
    backup_path = db_path + ".bak"

    # 既存DBをバックアップ
    if Path(db_path).exists():
        shutil.copy2(db_path, backup_path)

    try:
        contents = await db.read()
        with open(db_path, "wb") as f:
            f.write(contents)
        return {"success": True, "size_bytes": len(contents)}
    except Exception as e:
        # 失敗時はバックアップから復元
        if Path(backup_path).exists():
            shutil.copy2(backup_path, db_path)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# エントリポイント（ローカル起動用）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
