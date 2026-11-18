import type { Metadata } from "next";
import { ResultView } from "./result-view";

export const metadata: Metadata = { title: "診断結果｜Harmonize 組織診断" };

export default function ResultPage() {
  return (
    <main className="hz-page">
      <ResultView />
    </main>
  );
}
