import { describe, expect, it } from "vitest";
import vectors from "../../data/scoring_vectors.json";
import { quiz, types } from "./quiz";
import { AnswerValidationError, scoreAnswers } from "./scoring";

const toAnswers = (values: number[]) =>
  Object.fromEntries(values.map((value, index) => [`Q${String(index + 1).padStart(2, "0")}`, value]));

describe("データの整合性", () => {
  it("Q01〜Q60 の60問がそろっている", () => {
    expect(quiz.questions.map((q) => q.id)).toEqual(
      Array.from({ length: 60 }, (_, i) => `Q${String(i + 1).padStart(2, "0")}`),
    );
    expect(quiz.questions.every((q) => q.theme && q.a && q.b)).toBe(true);
  });

  it("16タイプすべてに文面がある", () => {
    let codes = [""];
    for (const axis of quiz.axes) codes = codes.flatMap((prefix) => [prefix + axis.a.code, prefix + axis.b.code]);
    expect(new Set(Object.keys(types))).toEqual(new Set(codes));
    expect(Object.values(types).every((t) => t.name && t.group && t.feature && t.strength && t.weakness && t.improvement)).toBe(true);
  });
});

describe("Python 版と共通のテストデータ", () => {
  it.each(vectors.cases)("$name", (testCase) => {
    const result = scoreAnswers(quiz, toAnswers(testCase.answers));
    expect(result.type_code).toBe(testCase.expected.type_code);
    expect(result.axes.map((axis) => axis.score)).toEqual(testCase.expected.scores);
  });

  it.each(vectors.errors)("$name", (testCase) => {
    try {
      scoreAnswers(quiz, toAnswers(testCase.answers));
      expect.unreachable();
    } catch (error) {
      expect(error).toBeInstanceOf(AnswerValidationError);
      expect((error as AnswerValidationError)[testCase.error as "missing" | "invalid"]).toEqual(testCase.ids);
    }
  });
});
