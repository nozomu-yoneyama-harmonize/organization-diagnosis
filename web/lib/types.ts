// 診断データの型。data/*.json と API のやり取りはすべてこの形に従う。

export type Pole = { code: string; short: string; full: string };

export type AxisDef = {
  id: string;
  no: number;
  name: string;
  a: Pole;
  b: Pole;
  threshold: number;
  question_ids: string[];
};

export type Question = { id: string; axis: string; theme: string; a: string; b: string };

export type Quiz = {
  version: string;
  scale: { min: number; max: number; labels: Record<string, string> };
  axes: AxisDef[];
  questions: Question[];
};

export type TypeInfo = {
  no: number;
  code: string;
  name: string;
  group: string;
  feature: string;
  strength: string;
  weakness: string;
  improvement: string;
};

export type Side = "a" | "b";

export type AxisResult = {
  id: string;
  name: string;
  score: number;
  min: number;
  max: number;
  threshold: number;
  side: Side;
  code: string;
  position: number;
  a: Pole;
  b: Pole;
};

export type Answers = Record<string, number>;

export type Diagnosis = { id: string; type: TypeInfo; axes: AxisResult[] };
