# Harmonize 16タイプ組織診断（Next.js / Vercel 版）

Streamlit 版（リポジトリ直下の `app.py`）を Next.js に置き換えたものです。移行が終わるまでは両方が動きます。
設問・タイプの文面はリポジトリ直下の `data/` を **両方の版で共有** しています（`web/` 側にコピーはありません）。

## 構成

| 役割 | 使うもの |
| --- | --- |
| 画面・API | Next.js 16（App Router）+ TypeScript + Tailwind CSS v4 |
| ホスティング | Vercel |
| 診断結果・クリック記録の保存 | Supabase（PostgreSQL） |
| 結果メールの送信 | Resend |

| 画面 | パス |
| --- | --- |
| 入口 | `/` |
| 16タイプ一覧 | `/types`（`/types#type-DHST` でそのタイプへ移動・強調） |
| 設問（4ページ×15問） | `/quiz` |
| 結果 | `/result` |

回答の途中経過と結果はブラウザの sessionStorage に保存されます（タブを閉じると消えます）。判定は必ずサーバー（`POST /api/v1/diagnoses`）で行います。

## ローカルで起動

Node.js 20.9 以上が必要です。

環境変数（秘密情報）は **Doppler**（project: `organization-diagnosis`）で管理します。必要な変数の一覧は `.env.example` です。

```powershell
cd web
npm install
doppler login          # 初回のみ。ブラウザで認証
doppler setup          # 初回のみ。doppler.yaml の設定（organization-diagnosis / dev）が選ばれる
npm run dev:doppler    # Doppler の値を注入して起動
```

http://localhost:3000 を開きます。`npm run dev`（Doppler なし）でも起動でき、その場合は保存されず、結果メールは「設定が完了していない」と表示されます。

```powershell
npm test         # 判定ロジック（Python 版と共通のテストデータ data/scoring_vectors.json）
npm run lint
npm run build
```

## 本番の準備（初回のみ）

### 1. Supabase
1. https://supabase.com でプロジェクトを作成（リージョンは Tokyo）
2. SQL Editor で `supabase/schema.sql` の中身を実行
3. Project Settings の **Project URL**（Data API）と、API Keys の **Secret key**（`sb_secret_...`。Publishable key ではない）を控える

### 2. Resend
1. https://resend.com で送信元ドメイン（例: harmonize-inc.jp）を追加し、表示される DNS レコードを登録
2. API Keys でキーを発行

### 3. Doppler
1. https://dashboard.doppler.com で Project `organization-diagnosis` を作成（環境 `dev` / `stg` / `prd` が自動で作られる）
2. 各環境に次の4つを登録（`dev` と `prd` で別の Supabase / キーを使い分けてもよい）

| 名前 | 値 |
| --- | --- |
| `SUPABASE_URL` | Supabase の Project URL |
| `SUPABASE_SECRET_KEY` | Supabase の Secret key `sb_secret_...`（ブラウザには出ません） |
| `RESEND_API_KEY` | Resend の API キー |
| `MAIL_FROM` | Resend で認証したドメインのアドレス（例: info@harmonize-inc.jp） |

### 4. Vercel
1. https://vercel.com で「Add New → Project」から GitHub の `organization-diagnosis` を取り込む
2. **Root Directory に `web` を指定**（Framework は Next.js が自動選択される）
3. 「Include files outside the root directory in the Build Step」は有効のまま（`../data` を読むため）
4. 環境変数は Vercel に直接入力せず、Doppler の **Integrations → Vercel** で同期する
   - `prd` → Production、`stg` → Preview、`dev` → Development に対応づける
   - 以降、Doppler で値を変えると Vercel 側にも反映される（反映後に再デプロイが必要）
5. デプロイ

以降は main に push するたびに自動でデプロイされます。ブランチを push するとプレビュー用の URL が発行されます。

## データの確認

Supabase の Table Editor で `diagnoses`（診断ごとのタイプ・軸別スコア・全回答）と `events`（`cta_click` / `result_email_sent`）を見られます。CSV にも書き出せます。
集計するときは `quiz_version`（現在は `2026-11-v60`）で絞り込んでください。設問が変わる前のデータと混ざらないようにするためです。

## 主な変更箇所

| 変えたいもの | ファイル |
| --- | --- |
| 設問の文面、判定の閾値（`threshold`） | `../data/questions.json`（変えたら `../data/scoring_vectors.json` の期待値も更新） |
| 16タイプの結果文面 | `../data/types.json` |
| 予約ページの URL、メール送信の上限 | `lib/quiz.ts` |
| 色、余白、文字 | `app/globals.css` |
| 入口 / 一覧 / 設問 / 結果の画面 | `app/page.tsx` / `app/types/page.tsx` / `app/quiz/quiz-form.tsx` / `app/result/result-view.tsx` |
| 結果メールの文面 | `lib/mail.ts` |
