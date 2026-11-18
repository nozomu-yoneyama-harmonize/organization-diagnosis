// POST /api/v1/diagnoses — 回答を送信し、判定結果を受け取る
import { submitDiagnosis } from "@/lib/diagnosis";
import { AnswerValidationError } from "@/lib/scoring";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const answers = body?.answers;
  if (!answers || typeof answers !== "object" || Array.isArray(answers)) {
    return Response.json({ error: "invalid_request" }, { status: 400 });
  }
  try {
    return Response.json(await submitDiagnosis(answers), { status: 201 });
  } catch (error) {
    if (error instanceof AnswerValidationError) {
      return Response.json(
        { error: "invalid_answers", missing: error.missing, invalid: error.invalid },
        { status: 422 },
      );
    }
    throw error;
  }
}
