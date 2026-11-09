# Harmonize 16タイプ組織診断 プロトタイプ

全40問・4軸の回答から16タイプを判定し、結果のメール送信と無料ご相談の予約ページ（Timerex）への案内を行う Streamlit アプリです。

## 起動（Windows PowerShell / VS Code ターミナル）

Python 3.11 以上が必要です（Streamlit 1.67 の要件）。このフォルダを開いて実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで http://localhost:8501 が開きます。

## 主な変更箇所

| 変えたいもの | ファイル |
| --- | --- |
| 設問の文面、判定の閾値（`threshold`） | `data/questions.json` |
| 16タイプの結果文面 | `data/types.json` |
| 色、余白、文字 | `assets/styles.css` |
| 画面の流れ、予約ページの URL（`BOOKING_URL`） | `app.py` |
| 画面の部品 | `ui/components.py` |

コードは `[BLOCK: 名前] START / END` のラベルで区切っています。修正はブロック単位で依頼できます。

閾値を変えた場合は、`data/scoring_vectors.json` の期待値も合わせて更新してください。

## 結果メールの設定

「結果をメールに送る」を使うには、送信元のメールアカウントが必要です。`.streamlit/secrets.toml.example` を `secrets.toml` という名前でコピーし、値を入力してください。未設定の場合、送信時にその旨を画面に表示します。

## データの確認

回答と CTA クリックは `var/harmonize.db`（SQLite）に保存されます。次のコマンドで `var/export/` に Excel で開ける CSV を書き出します。

```powershell
python tools/export_csv.py
```

| ファイル | 内容 |
| --- | --- |
| `diagnoses.csv` | 診断ごとのタイプ、軸別スコア、全回答 |
| `events.csv` | `cta_click`（予約ページへのボタン押下）、`result_email_sent`（結果メール送信） |
| `leads.csv` | 現在は未使用（申し込み情報は Timerex 側に保存） |

## テスト

```powershell
python -m pytest
```

## Streamlit のバージョン

`assets/styles.css` の5段階ボタンは Streamlit 内部の HTML 構造に依存しているため、`requirements.txt` でバージョンを固定しています。更新するときは回答画面の表示を確認してください。

## JavaScript への移行

API 仕様と手順は `docs/migration-to-js.md` にあります。
