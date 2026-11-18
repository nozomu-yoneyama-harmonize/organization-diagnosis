"use client";
// 結果画面。判定結果は設問画面が sessionStorage に保存したものを表示する。
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { CodeLetters, Logo, Spine } from "@/components/parts";
import { BOOKING_URL, quiz, typeList } from "@/lib/quiz";
import { DIAGNOSIS_KEY, parse, QUIZ_KEY, useSessionRaw, writeSession } from "@/lib/session-store";
import type { Diagnosis } from "@/lib/types";

const EMAIL_ERRORS: Record<string, string> = {
  invalid_email: "メールアドレスは name@example.com の形式で入力してください",
  too_many: "送信できるのは1回の診断につき3通までです",
  not_found: "この診断結果は保存されていないため送信できません。お手数ですが、もう一度診断してください",
  not_configured: "メール送信の設定が完了していないため送信できません",
  send_failed: "送信できませんでした。アドレスを確認して、もう一度お試しください",
};

function recordEvent(diagnosisId: string, name: string) {
  // ページ移動中でも送信が途切れないよう keepalive を付ける
  fetch(`/api/v1/diagnoses/${diagnosisId}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
    keepalive: true,
  }).catch(() => {});
}

export function ResultView() {
  const router = useRouter();
  const raw = useSessionRaw(DIAGNOSIS_KEY);
  const diagnosis = parse<Diagnosis>(raw);

  if (raw === undefined) return null; // サーバー描画時
  if (!diagnosis) {
    return (
      <div className="hz-result">
        <Logo />
        <h1>診断結果が見つかりません</h1>
        <p className="hz-result__lede">結果はブラウザのタブを閉じると消えます。お手数ですが、もう一度診断してください。</p>
        <div className="hz-actions">
          <Link className="hz-btn hz-btn--primary" href="/quiz">
            診断をスタートする（無料）
          </Link>
        </div>
      </div>
    );
  }

  const item = diagnosis.type;
  const threshold = diagnosis.axes[0].threshold;
  const restart = () => {
    writeSession(QUIZ_KEY, null);
    writeSession(DIAGNOSIS_KEY, null);
    router.push("/quiz");
  };

  return (
    <>
      <div className="hz-result">
        <Logo />
        <p className="hz-result__group">{item.group}</p>
        <div className="hz-code" aria-label={`${item.code}型`}>
          {diagnosis.axes.map((axis) => (
            <div key={axis.id} className={`side-${axis.side}`}>
              <b>{axis.code}</b>
              <span>{axis[axis.side].short}</span>
            </div>
          ))}
          <div className="hz-code__suffix">
            <b>型</b>
          </div>
        </div>
        <h1>{item.name}</h1>
        <p className="hz-result__lede">{item.feature}</p>
      </div>

      <section className="hz-block">
        <h2>組織の骨格図</h2>
        <Spine axes={diagnosis.axes} />
        <p className="hz-spine__note">
          中央の目盛りが判定の境目です。{threshold}点以下で左側、{threshold + 1}点以上で右側のタイプになります。
        </p>
      </section>
      <div className="hz-pair">
        <section>
          <h2>組織の強み</h2>
          <p>{item.strength}</p>
        </section>
        <section>
          <h2>組織の弱み</h2>
          <p>{item.weakness}</p>
        </section>
      </div>

      <section className="hz-block">
        <h2>16タイプ一覧</h2>
        <p className="hz-alltypes__note">タイプ名を押すと、新しいタブで各タイプの特徴を確認できます。</p>
        <div className="hz-typelinks">
          {typeList.map((type) => (
            <a
              key={type.code}
              className={`hz-typelink${type.code === item.code ? " is-current" : ""}`}
              href={`/types#type-${type.code}`}
              target="_blank"
              rel="noopener"
            >
              <span className="hz-typelink__code">
                <CodeLetters code={type.code} axes={quiz.axes} />
              </span>
              <span className="hz-typelink__name">{type.name}</span>
            </a>
          ))}
        </div>
      </section>

      <NextStep diagnosis={diagnosis} />

      <div className="hz-actions" style={{ marginTop: 8 }}>
        <button type="button" className="hz-btn hz-btn--quiet" onClick={restart}>
          もう一度診断する
        </button>
      </div>
    </>
  );
}

function NextStep({ diagnosis }: { diagnosis: Diagnosis }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [sentTo, setSentTo] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const send = async (form: HTMLFormElement) => {
    const email = String(new FormData(form).get("email") ?? "").trim();
    setSending(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/diagnoses/${diagnosis.id}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (response.ok) {
        setSentTo(email);
        form.reset();
        dialog.current?.close();
        return;
      }
      const body = await response.json().catch(() => ({ error: "send_failed" }));
      setError(EMAIL_ERRORS[body.error] ?? EMAIL_ERRORS.send_failed);
    } catch {
      setError(EMAIL_ERRORS.send_failed);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="hz-next">
      <h2>改善に向けたポイント</h2>
      <p>{diagnosis.type.improvement}</p>
      <p className="hz-next__note">
        60分の無料ご相談で、自社では何から着手するかを一緒に整理します。日程は予約ページからお選びいただけます。
      </p>
      <a
        className="hz-btn"
        href={BOOKING_URL}
        target="_blank"
        rel="noopener"
        onClick={() => recordEvent(diagnosis.id, "cta_click")}
      >
        無料ご相談（60分）に申し込む
      </a>
      <button
        type="button"
        className="hz-btn hz-btn--outline"
        onClick={() => {
          setError("");
          dialog.current?.showModal();
        }}
      >
        結果をメールに送る
      </button>
      {sentTo && (
        <p className="hz-next__done" role="status">
          {sentTo} に診断結果を送信しました。
        </p>
      )}

      <dialog ref={dialog} className="hz-dialog" aria-labelledby="email-title">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void send(event.currentTarget);
          }}
        >
          <h2 id="email-title">結果をメールに送る</h2>
          <label htmlFor="email">メールアドレス</label>
          <input id="email" name="email" type="email" autoComplete="email" required />
          <p className="hz-dialog__caption">入力したアドレスは、この診断結果の送信にのみ使用し、保存しません。</p>
          {error && (
            <p className="hz-dialog__error" role="alert">
              {error}
            </p>
          )}
          <div className="hz-actions" style={{ marginTop: 20 }}>
            <button type="submit" className="hz-btn hz-btn--primary" disabled={sending}>
              {sending ? "送信しています…" : "送信する"}
            </button>
            <button type="button" className="hz-btn hz-btn--quiet" onClick={() => dialog.current?.close()}>
              閉じる
            </button>
          </div>
        </form>
      </dialog>
    </section>
  );
}
