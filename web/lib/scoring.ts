// 診断の判定ロジック。core/scoring.py と同じ結果になること（data/scoring_vectors.json で検証）。
import type { Answers, AxisResult, Quiz } from "./types";

export class AnswerValidationError extends Error {
  constructor(
    public missing: string[],
    public invalid: string[],
  ) {
    super(`missing=${missing} invalid=${invalid}`);
  }
}

export function validateAnswers(quiz: Quiz, answers: Record<string, unknown>): asserts answers is Answers {
  const { min: low, max: high } = quiz.scale;
  const missing: string[] = [];
  const invalid: string[] = [];
  for (const { id } of quiz.questions) {
    const value = answers[id];
    if (value === undefined || value === null) missing.push(id);
    else if (typeof value !== "number" || !Number.isInteger(value) || value < low || value > high) invalid.push(id);
  }
  if (missing.length || invalid.length) throw new AnswerValidationError(missing, invalid);
}

/** 軸ごとに加算し、合計が threshold 以下なら A 側、超えたら B 側と判定する。 */
export function scoreAnswers(quiz: Quiz, answers: Record<string, unknown>): { type_code: string; axes: AxisResult[] } {
  validateAnswers(quiz, answers);
  const { min: low, max: high } = quiz.scale;
  const axes = quiz.axes.map((axis): AxisResult => {
    const count = axis.question_ids.length;
    const score = axis.question_ids.reduce((sum, id) => sum + answers[id], 0);
    const side = score <= axis.threshold ? "a" : "b";
    const min = count * low;
    const max = count * high;
    return {
      id: axis.id,
      name: axis.name,
      score,
      min,
      max,
      threshold: axis.threshold,
      side,
      code: axis[side].code,
      position: (score - min) / (max - min),
      a: axis.a,
      b: axis.b,
    };
  });
  return { type_code: axes.map((axis) => axis.code).join(""), axes };
}
