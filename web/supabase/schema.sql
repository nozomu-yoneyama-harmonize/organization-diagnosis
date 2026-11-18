-- Harmonize 組織診断のテーブル。Supabase の SQL Editor で一度だけ実行する。
-- 読み書きはサーバー（Secret key）からのみ行うため、RLS を有効にしてポリシーは作らない。

create table if not exists public.diagnoses (
  id uuid primary key,
  created_at timestamptz not null default now(),
  quiz_version text not null,          -- 例: 2026-11-v60。集計はこの値で分けること
  type_code text not null,
  axis_scores jsonb not null,          -- {"numeric": 45, "organization": 60, ...}
  answers jsonb not null               -- {"Q01": 3, ..., "Q60": 5}
);

create table if not exists public.events (
  id bigint generated always as identity primary key,
  diagnosis_id uuid not null references public.diagnoses(id) on delete cascade,
  name text not null,                  -- cta_click / result_email_sent
  created_at timestamptz not null default now()
);

create index if not exists events_diagnosis_name_idx on public.events (diagnosis_id, name);
create index if not exists diagnoses_version_created_idx on public.diagnoses (quiz_version, created_at);

alter table public.diagnoses enable row level security;
alter table public.events enable row level security;
