// POST /api/v1/diagnoses/{id}/events — CTA クリックなどを記録する
import { recordEvent } from "@/lib/diagnosis";

export async function POST(request: Request, ctx: RouteContext<"/api/v1/diagnoses/[id]/events">) {
  const { id } = await ctx.params;
  const body = await request.json().catch(() => null);
  if (typeof body?.name === "string") await recordEvent(id, body.name);
  return new Response(null, { status: 204 });
}
