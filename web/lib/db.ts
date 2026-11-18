// Supabase への保存。サーバー専用（Secret key はブラウザに出さない）。
import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { Answers } from "./types";

let client: SupabaseClient | null | undefined;

/** 環境変数が未設定なら null（ローカル開発で DB なしでも診断は動かす） */
function db(): SupabaseClient | null {
  if (client !== undefined) return client;
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SECRET_KEY;
  client = url && key ? createClient(url, key, { auth: { persistSession: false } }) : null;
  return client;
}

export class DatabaseNotConfigured extends Error {}

function requireDb(): SupabaseClient {
  const connection = db();
  if (!connection) throw new DatabaseNotConfigured("SUPABASE_URL / SUPABASE_SECRET_KEY が未設定です");
  return connection;
}

export async function saveDiagnosis(row: {
  id: string;
  quiz_version: string;
  type_code: string;
  axis_scores: Record<string, number>;
  answers: Answers;
}): Promise<void> {
  const { error } = await requireDb().from("diagnoses").insert(row);
  if (error) throw error;
}

export async function saveEvent(diagnosisId: string, name: string): Promise<void> {
  const { error } = await requireDb().from("events").insert({ diagnosis_id: diagnosisId, name });
  if (error) throw error;
}

export async function findDiagnosis(id: string): Promise<{ quiz_version: string; answers: Answers } | null> {
  const { data, error } = await requireDb()
    .from("diagnoses")
    .select("quiz_version, answers")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function countEvents(diagnosisId: string, name: string): Promise<number> {
  const { count, error } = await requireDb()
    .from("events")
    .select("id", { count: "exact", head: true })
    .eq("diagnosis_id", diagnosisId)
    .eq("name", name);
  if (error) throw error;
  return count ?? 0;
}
