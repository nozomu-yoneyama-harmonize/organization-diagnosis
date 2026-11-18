// POST /api/v1/diagnoses/{id}/email — 結果をメールで送る（アドレスは保存しない）
import { sendResultEmail } from "@/lib/diagnosis";

const STATUS = { invalid_email: 422, not_found: 404, too_many: 429, not_configured: 503, send_failed: 503 } as const;

export async function POST(request: Request, ctx: RouteContext<"/api/v1/diagnoses/[id]/email">) {
  const { id } = await ctx.params;
  const body = await request.json().catch(() => null);
  const result = await sendResultEmail(id, typeof body?.email === "string" ? body.email : "");
  if (result.ok) return new Response(null, { status: 202 });
  return Response.json({ error: result.error }, { status: STATUS[result.error] });
}
