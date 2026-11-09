# JavaScript バックエンドへの移行設計

## 方針

判定ロジックと保存処理は、すでに画面（Streamlit）から切り離してあります。
`app.py` が呼ぶのは `core/backend.py` の関数だけで、やり取りはすべて JSON にできる形です。
そのため、先に JS の API を完成させ、Streamlit をその API につないで動作を確かめてから、最後に画面を React へ置き換える順番で進められます。

| 現在のファイル | 移行先 | 移行のしかた |
| --- | --- | --- |
| `data/*.json` | そのまま流用 | コピーするだけ |
| `core/scoring.py` | `lib/scoring.mjs` | 下の移植例を使用 |
| `core/backend.py` | API ルート | 下の API 仕様どおりに実装 |
| `core/storage.py` | Supabase / Firestore | テーブル構成はそのまま |
| `app.py`, `ui/`, `assets/` | React / Next.js | API 完成後に置き換え |

推奨構成は Next.js の Route Handlers + Supabase（PostgreSQL）です。将来の React UI と同じリポジトリで管理でき、SQLite のテーブル構成をほぼそのまま移せます。

## 移行の手順

1. `lib/scoring.mjs` を作り、`data/scoring_vectors.json` の全ケースが通ることを確認する
2. 下の API を実装し、DB を Supabase に接続する
3. `core/backend.py` の各関数の中身を HTTP 呼び出しに差し替え、Streamlit から JS バックエンドを使って全画面を確認する
4. React で画面を作り、同じ API につなぐ。Streamlit を停止する

## API 仕様（v1）

判定は必ずサーバー側で行います。ブラウザで判定すると、改ざんされた結果が保存される可能性があるためです。

| メソッドとパス | 対応する関数 | 用途 |
| --- | --- | --- |
| `GET /api/v1/quiz` | `get_quiz()` | 設問と軸の定義を取得 |
| `POST /api/v1/diagnoses` | `submit_diagnosis()` | 回答を送信し、判定結果を取得 |
| `POST /api/v1/diagnoses/{id}/events` | `record_event()` | CTA クリックなどを記録 |
| `POST /api/v1/diagnoses/{id}/email` | `send_result_email()` | 結果をメールで送信 |
| `POST /api/v1/leads` | `create_lead()` | 現在は未使用（予約は Timerex で受付） |

### POST /api/v1/diagnoses

リクエスト:

```json
{ "answers": { "Q01": 1, "Q02": 4, "Q40": 3 } }
```

`answers` には Q01〜Q40 の全問が必要です。値は 1〜5 の整数です。

レスポンス `201`:

```json
{
  "id": "6f0c1a52-…",
  "type": {
    "no": 11, "code": "IHPT", "name": "カリスマ牽引の猛進軍",
    "group": "オーナー・営業会社タイプ",
    "feature": "…", "strength": "…", "weakness": "…", "improvement": "…"
  },
  "axes": [
    {
      "id": "numeric", "name": "数値管理", "score": 42, "min": 10, "max": 50,
      "threshold": 30, "side": "b", "code": "I", "position": 0.8,
      "a": { "code": "D", "short": "データ", "full": "データ・定量" },
      "b": { "code": "I", "short": "直感", "full": "直感・経験" }
    }
  ]
}
```

エラー `422`（未回答または範囲外）:

```json
{ "error": "invalid_answers", "missing": ["Q40"], "invalid": [] }
```

### POST /api/v1/diagnoses/{id}/events

```json
{ "name": "cta_click" }
```

`name` は `cta_click`。レスポンスは `204`。

### POST /api/v1/diagnoses/{id}/email

```json
{ "email": "yamada@example.com" }
```

レスポンスは `202`。アドレスは保存しません。入力エラーは `422`、未設定や送信失敗は `503` を返します。第三者のアドレス宛てに大量送信されないよう、診断ごとの送信回数をサーバー側で制限します（プロトタイプは画面側で3通まで）。

### POST /api/v1/leads

```json
{ "diagnosis_id": "6f0c1a52-…", "company": "株式会社○○", "name": "山田太郎", "email": "yamada@example.com" }
```

レスポンスは `201 { "id": 1 }`、入力エラーは `422 { "errors": { "email": "…" } }`。

## 判定ロジックの移植例

`data/scoring_vectors.json` の全ケースで Python 版と同じ結果になることを確認済みのコードです。

```js
export class AnswerValidationError extends Error {
  constructor(missing, invalid) {
    super(`missing=${missing} invalid=${invalid}`);
    this.missing = missing;
    this.invalid = invalid;
  }
}

export function scoreAnswers(quiz, answers) {
  const { min: low, max: high } = quiz.scale;
  const missing = [];
  const invalid = [];
  for (const { id } of quiz.questions) {
    const value = answers[id];
    if (value === undefined || value === null) missing.push(id);
    else if (!Number.isInteger(value) || value < low || value > high) invalid.push(id);
  }
  if (missing.length || invalid.length) throw new AnswerValidationError(missing, invalid);

  const axes = quiz.axes.map((axis) => {
    const count = axis.question_ids.length;
    const score = axis.question_ids.reduce((sum, id) => sum + answers[id], 0);
    const side = score <= axis.threshold ? "a" : "b";
    const min = count * low;
    const max = count * high;
    return {
      id: axis.id, name: axis.name, score, min, max, threshold: axis.threshold,
      side, code: axis[side].code, position: (score - min) / (max - min),
      a: axis.a, b: axis.b,
    };
  });
  return { type_code: axes.map((axis) => axis.code).join(""), axes };
}
```

## 本番化の前に追加するもの

- 申し込み API のレート制限とボット対策
- プライバシーポリシーへのリンクと、個人情報の取り扱いへの同意
- CRM（HubSpot / Salesforce など）への連携
- 結果メールの自動送信、設問別の回答を見る管理画面
