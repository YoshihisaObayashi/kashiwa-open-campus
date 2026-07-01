# 柏キャンパス一般公開 企画検索 Webサービス

**UTokyo Kashiwa Open Campus — Event Search Web Service**

東京大学柏キャンパス一般公開の企画情報をスクレイピングしてデータベース化し、開催日時・内容・研究者・対象者で検索できる日英バイリンガルWebサービスです。

---

## 🏗️ システム構成

```
[Playwright スクレイパー]
   │  毎日 JST 07:00 (GitHub Actions)
   ▼
[SQLite + FTS5 全文検索]  ←── content_hash による差分更新
   │
   ▼
[FastAPI バックエンド]  ──→  Render.com (永続ディスク)
   │
   ▼
[React + Vite フロントエンド]  ──→  Vercel
   │
   └─ /admin  管理者パネル（翻訳の手動修正）
```

## 📁 ディレクトリ構成

```
kashiwa-open-campus/
├── scraper/
│   ├── scrape.py       # Playwright スクレイパー
│   ├── translate.py    # Gemini API 翻訳モジュール
│   ├── init_db.py      # DB 初期化（FTS5 テーブル作成）
│   └── requirements.txt
├── backend/
│   ├── main.py         # FastAPI アプリ
│   ├── database.py     # SQLite クエリヘルパー
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/ # UI コンポーネント群
│       ├── api/        # axios クライアント
│       ├── i18n/       # 日英翻訳リソース
│       └── style.css
├── .github/workflows/
│   └── scrape.yml      # 毎日自動クロール
├── render.yaml         # Render.com デプロイ設定
├── vercel.json         # Vercel デプロイ設定
└── .env.example        # 環境変数テンプレート
```

---

## 🚀 ローカル開発セットアップ

### 前提条件
- Python 3.12+
- Node.js 20+
- Gemini API キー（[取得はこちら](https://aistudio.google.com/app/apikey)）

### 1. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して各 API キーを設定
```

### 2. スクレイパー & バックエンドのセットアップ

```bash
# スクレイパー依存関係のインストール
pip install -r scraper/requirements.txt
playwright install chromium

# DB を初期化してスクレイプ実行
python scraper/scrape.py
```

### 3. バックエンドの起動

```bash
pip install -r backend/requirements.txt

# DB_PATH を指定して起動（スクレイパーと同じDBを参照）
DB_PATH=./events.db uvicorn backend.main:app --reload --port 8000
```

API ドキュメント: http://localhost:8000/docs

### 4. フロントエンドの起動

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

管理者パネル: http://localhost:5173/admin

---

## 🔍 API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/events` | 企画一覧（検索・フィルタ対応） |
| `GET` | `/api/events/{id}` | 企画詳細 |
| `GET` | `/api/departments` | 部局一覧 |
| `GET` | `/api/stats` | 統計情報 |
| `PATCH` | `/api/admin/events/{id}` | 翻訳手動修正 🔑 |
| `POST` | `/api/admin/refresh` | 手動クロール実行 🔑 |
| `POST` | `/api/admin/db-sync` | DB アップロード 🔑 |

🔑 = `X-API-Key` ヘッダーに `ADMIN_API_KEY` が必要

### 検索パラメータ例

```
GET /api/events?q=宇宙&lang=ja&limit=10
GET /api/events?date=2025-10-24&department=宇宙線研究所
GET /api/events?target=小中高生&lang=ja
GET /api/events?q=cosmic+ray&lang=en
```

---

## ☁️ 本番デプロイ

### バックエンド → Render.com

1. [Render.com](https://render.com) にサインイン
2. **New → Blueprint** を選択してこのリポジトリを接続
3. `render.yaml` が自動検出されます
4. **Environment → Secret Files** で以下を設定:
   - `ADMIN_API_KEY` : 強力なランダム文字列（`openssl rand -hex 32`）
   - `GEMINI_API_KEY` : Gemini API キー
5. デプロイ後、`ALLOWED_ORIGINS` に Vercel の URL を追加

> **注意**: 無料プランは15分無操作でスリープします。`starter`プラン（$7/月）推奨。

### フロントエンド → Vercel

1. [Vercel](https://vercel.com) にサインイン → **New Project**
2. このリポジトリをインポート
3. **Root Directory** を `frontend` に設定
4. **Environment Variables** に追加:
   - `VITE_API_URL` = `https://your-api.onrender.com`
5. デプロイ！

### GitHub Actions のシークレット設定

リポジトリ → Settings → Secrets and variables → Actions:

| シークレット名 | 説明 |
|---|---|
| `GEMINI_API_KEY` | Gemini API キー |
| `ADMIN_API_KEY` | 管理者 API キー |
| `RENDER_ADMIN_URL` | Render バックエンド URL |

**Variables (シークレット不要):**

| 変数名 | 例 |
|---|---|
| `TARGET_URL` | `https://www.kashiwa.u-tokyo.ac.jp/open_campus_2026/` |

---

## 🔄 自動更新の仕組み

```
毎日 JST 07:00
   └─ GitHub Actions 起動
         ├─ Playwright でサイトを完全レンダリング
         ├─ 企画情報を抽出（テーブル/カード/フルテキスト 3戦略）
         ├─ content_hash で変更検出 → 差分のみ更新
         ├─ Gemini API で未翻訳フィールドを英訳
         └─ /api/admin/db-sync で Render.com に同期
```

年度が変わる場合は `TARGET_URL` を変更するだけ。

---

## ✏️ 翻訳の手動修正

1. `/admin` にアクセス
2. `ADMIN_API_KEY` でログイン
3. 左のリストから企画を選択
4. 英語フィールドを編集して「保存」
5. 保存後はそのレコードに `translation_edited=1` が設定され、以後の自動翻訳で上書きされません

---

## 🗄️ データベーススキーマ

```sql
events (
  id, title_ja, title_en,
  date_start, date_end,
  venue_ja, venue_en,
  description_ja, description_en,
  researchers (JSON),  researchers_en (JSON),
  target_audience_ja, target_audience_en,
  registration_required, registration_url,
  department_ja, department_en,
  source_url, scraped_at,
  content_hash,          -- 変更検出用MD5
  translation_edited     -- 1=手動修正済み（自動上書き保護）
)

events_fts  -- FTS5 全文検索インデックス（日英両対応）
scrape_log  -- クロール実行ログ
```

---

## 📄 ライセンス

MIT License

スクレイピング対象サイトの利用規約を遵守し、`robots.txt` を確認の上ご利用ください。
