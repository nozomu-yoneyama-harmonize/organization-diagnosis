"use client";
// 設問画面。1ページ＝1軸（15問）。回答はタブを閉じるまで sessionStorage に保持する。
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { quiz } from "@/lib/quiz";
import { DIAGNOSIS_KEY, parse, QUIZ_KEY, useSessionRaw, writeSession } from "@/lib/session-store";
import type { Answers, Diagnosis } from "@/lib/types";

type Progress = { answers: Answers; page: number };
const EMPTY: Progress = { answers: {}, page: 0 };
const SCALE = Object.entries(quiz.scale.labels).map(([value, label]) => ({ value: Number(value), label }));

function scrollToTarget(target: Element | null) {
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (target) target.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" });
  else window.scrollTo({ top: 0 });
}

export function QuizForm() {
  const router = useRouter();
  const raw = useSessionRaw(QUIZ_KEY);
  const { answers, page } = parse<Progress>(raw) ?? EMPTY;
  const [missing, setMissing] = useState<string[]>([]);
  const [attempt, setAttempt] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const axis = quiz.axes[page];
  const questions = quiz.questions.filter((q) => q.axis === axis.id);
  const isLast = page === quiz.axes.length - 1;
  const answered = Object.keys(answers).length;

  // ページ切替・未回答の指摘時にスクロールする
  useEffect(() => {
    scrollToTarget(missing.length ? document.getElementById(`q-${missing[0]}`) : null);
    // missing は attempt と同時に変わるため attempt だけで判定する
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, attempt]);

  if (raw === undefined) return null; // サーバー描画時は保存済みの回答をまだ読めない

  const save = (next: Progress) => writeSession(QUIZ_KEY, next);

  const choose = (questionId: string, value: number) => {
    save({ answers: { ...answers, [questionId]: value }, page });
    setMissing((current) => current.filter((id) => id !== questionId));
  };

  const goTo = (nextPage: number) => {
    setMissing([]);
    setError("");
    save({ answers, page: nextPage });
  };

  const flagMissing = (ids: string[], onPage: number) => {
    if (onPage !== page) save({ answers, page: onPage });
    setMissing(ids);
    setAttempt((n) => n + 1);
  };

  const submit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch("/api/v1/diagnoses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      if (response.status === 422) {
        // 想定外の未回答・範囲外があれば、そのページへ戻す
        const body: { missing: string[]; invalid: string[] } = await response.json();
        const ids = [...body.missing, ...body.invalid];
        const first = quiz.questions.find((q) => ids.includes(q.id))!;
        const target = quiz.axes.findIndex((a) => a.id === first.axis);
        flagMissing(ids.filter((id) => quiz.axes[target].question_ids.includes(id)), target);
        return;
      }
      if (!response.ok) throw new Error(`status ${response.status}`);
      const diagnosis: Diagnosis = await response.json();
      writeSession(DIAGNOSIS_KEY, diagnosis);
      writeSession(QUIZ_KEY, null);
      router.push("/result");
    } catch {
      setError("通信できませんでした。電波の良い場所で、もう一度「結果を見る」を押してください。");
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => {
    const unanswered = questions.filter((q) => answers[q.id] === undefined).map((q) => q.id);
    if (unanswered.length) return flagMissing(unanswered, page);
    if (isLast) return void submit();
    goTo(page + 1);
  };

  return (
    <>
      <div
        className="hz-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={quiz.questions.length}
        aria-valuenow={answered}
        aria-label="回答の進み具合"
      >
        <div className="hz-progress__meta">
          <span>{axis.name}</span>
          <strong>
            {answered} / {quiz.questions.length}問
          </strong>
        </div>
        <div className="hz-progress__bars">
          {quiz.axes.map((item, index) => {
            const done = item.question_ids.filter((id) => answers[id] !== undefined).length;
            return (
              <span key={item.id} className={index === page ? "is-current" : ""}>
                <i style={{ width: `${(done / item.question_ids.length) * 100}%` }} />
              </span>
            );
          })}
        </div>
      </div>

      <div className="hz-intro">
        <p>
          {page + 1} / {quiz.axes.length} ページ
        </p>
        <h2>
          {axis.a.short}か、{axis.b.short}か
        </h2>
        <p>理想ではなく、いまの実態に近いほうを選んでください。円が大きいほど、その傾向が強いことを表します。</p>
      </div>

      {questions.map((question) => {
        const isMissing = missing.includes(question.id);
        return (
          <fieldset key={question.id} id={`q-${question.id}`} className="hz-q">
            <legend className="sr-only-hz">
              {question.id} {question.theme}
            </legend>
            <div className="hz-q__head" aria-hidden="true">
              <span>{question.id}</span>
              <h3>{question.theme}</h3>
              {isMissing && <em className="hz-q__missing">未回答</em>}
            </div>
            <div className="hz-q__poles">
              <p className="is-a">{question.a}</p>
              <p className="is-b">{question.b}</p>
            </div>
            <div className="hz-likert">
              {SCALE.map(({ value, label }) => (
                <label key={value} title={label}>
                  <input
                    type="radio"
                    name={question.id}
                    value={value}
                    checked={answers[question.id] === value}
                    onChange={() => choose(question.id, value)}
                    aria-label={label}
                  />
                  <i />
                </label>
              ))}
            </div>
          </fieldset>
        );
      })}

      {missing.length > 0 && (
        <div className="hz-alert" role="alert">
          未回答が{missing.length}問あります（{missing.join("、")}）。すべて回答すると次へ進めます。
        </div>
      )}
      {error && (
        <div className="hz-alert" role="alert">
          {error}
        </div>
      )}

      <div className="hz-nav">
        {page > 0 && (
          <button type="button" className="hz-btn" onClick={() => goTo(page - 1)}>
            前へ戻る
          </button>
        )}
        <button type="button" className="hz-btn hz-btn--primary" onClick={next} disabled={submitting}>
          {isLast ? (submitting ? "判定しています…" : "結果を見る") : "次へ進む"}
        </button>
      </div>
    </>
  );
}
