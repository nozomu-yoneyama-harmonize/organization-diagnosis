"use client";
// sessionStorage に保存する小さなストア。タブを閉じるまで回答の途中経過と結果を保持する。
// useSyncExternalStore で読むため、サーバー描画時は null（未読み込み）として扱う。
import { useSyncExternalStore } from "react";

const listeners = new Set<() => void>();

function read(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null; // プライベートブラウズ等で使えない場合
  }
}

export function writeSession(key: string, value: unknown): void {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // 保存できなくても画面は動かす
  }
  listeners.forEach((notify) => notify());
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

/** 保存値の生文字列を返す。undefined = サーバー描画中（まだ読めない） */
export function useSessionRaw(key: string): string | null | undefined {
  return useSyncExternalStore(
    subscribe,
    () => read(key),
    () => undefined,
  );
}

export function parse<T>(raw: string | null | undefined): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export const QUIZ_KEY = "hz_quiz";
export const DIAGNOSIS_KEY = "hz_diagnosis";
