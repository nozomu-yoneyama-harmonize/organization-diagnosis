// API ルートから呼ぶ診断の処理（core/backend.py 相当）。
import "server-only";
import { countEvents, DatabaseNotConfigured, findDiagnosis, saveDiagnosis, saveEvent } from "./db";
import { MailNotConfigured, sendResultMail } from "./mail";
import { BOOKING_URL, MAX_EMAILS_PER_DIAGNOSIS, quiz, types } from "./quiz";
import { scoreAnswers } from "./scoring";
import type { Answers, Diagnosis } from "./types";

export const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const EVENT_NAMES = new Set(["cta_click"]);

export const isDiagnosisId = (id: string) => UUID_PATTERN.test(id);

/** 判定して保存する。保存に失敗しても診断結果は返す（利用者の結果表示を止めない）。 */
export async function submitDiagnosis(answers: Record<string, unknown>): Promise<Diagnosis> {
  const result = scoreAnswers(quiz, answers); // 不正な回答は AnswerValidationError
  const id = crypto.randomUUID();
  const cleanAnswers = Object.fromEntries(quiz.questions.map(({ id: qid }) => [qid, answers[qid]])) as Answers;
  try {
    await saveDiagnosis({
      id,
      quiz_version: quiz.version,
      type_code: result.type_code,
      axis_scores: Object.fromEntries(result.axes.map((axis) => [axis.id, axis.score])),
      answers: cleanAnswers,
    });
  } catch (error) {
    if (error instanceof DatabaseNotConfigured) console.warn(`診断を保存しませんでした: ${error.message}`);
    else console.error("failed to save diagnosis", error);
  }
  return { id, type: types[result.type_code], axes: result.axes };
}

/** 計測の失敗は画面に影響させない */
export async function recordEvent(diagnosisId: string, name: string): Promise<void> {
  if (!isDiagnosisId(diagnosisId) || !EVENT_NAMES.has(name)) return;
  try {
    await saveEvent(diagnosisId, name);
  } catch (error) {
    if (!(error instanceof DatabaseNotConfigured)) console.error("failed to save event", error);
  }
}

export type EmailResult = { ok: true } | { ok: false; error: "invalid_email" | "not_found" | "too_many" | "not_configured" | "send_failed" };

/**
 * 結果をメール送信する。改ざんを防ぐため、画面から受け取った結果ではなく
 * 保存済みの回答から結果を組み立て直す。アドレスは保存しない。
 */
export async function sendResultEmail(diagnosisId: string, email: string): Promise<EmailResult> {
  const recipient = email.trim();
  if (!EMAIL_PATTERN.test(recipient)) return { ok: false, error: "invalid_email" };
  try {
    const row = isDiagnosisId(diagnosisId) ? await findDiagnosis(diagnosisId) : null;
    if (!row || row.quiz_version !== quiz.version) return { ok: false, error: "not_found" };
    if ((await countEvents(diagnosisId, "result_email_sent")) >= MAX_EMAILS_PER_DIAGNOSIS) {
      return { ok: false, error: "too_many" };
    }
    const result = scoreAnswers(quiz, row.answers);
    await sendResultMail({ id: diagnosisId, type: types[result.type_code], axes: result.axes }, recipient, BOOKING_URL);
    await saveEvent(diagnosisId, "result_email_sent");
    return { ok: true };
  } catch (error) {
    if (error instanceof MailNotConfigured || error instanceof DatabaseNotConfigured) {
      console.warn(error.message);
      return { ok: false, error: "not_configured" };
    }
    console.error("failed to send result email", error);
    return { ok: false, error: "send_failed" };
  }
}
