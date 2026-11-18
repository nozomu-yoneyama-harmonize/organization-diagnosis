// 設問とタイプの定義。Streamlit 版と共有しているリポジトリ直下の data/ を読む。
import questions from "../../data/questions.json";
import typesFile from "../../data/types.json";
import type { Quiz, TypeInfo } from "./types";

export const quiz = questions as Quiz;
export const types = typesFile.types as Record<string, TypeInfo>;

/** 番号順に並べた16タイプ */
export const typeList: TypeInfo[] = Object.values(types).sort((x, y) => x.no - y.no);

export const BOOKING_URL = "https://timerex.net/s/harmonize-inc/744bcdd8";
export const MAX_EMAILS_PER_DIAGNOSIS = 3;
