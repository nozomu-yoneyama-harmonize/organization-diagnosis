import type { Metadata } from "next";
import { QuizForm } from "./quiz-form";

export const metadata: Metadata = { title: "診断中｜Harmonize 組織診断" };

export default function QuizPage() {
  return (
    <main className="hz-page">
      <QuizForm />
    </main>
  );
}
