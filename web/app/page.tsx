// 入口（ランディング）画面
import Link from "next/link";
import { Logo } from "@/components/parts";
import { quiz } from "@/lib/quiz";

export default function Home() {
  return (
    <main className="hz-page hz-landing">
      <Logo />
      <p className="hz-landing__pain">売上は上がっているのに、なぜか現場が疲弊している。</p>
      {/* 文節単位の塊にして、語の途中（「どん｜な」等）で改行されないようにする */}
      <h1>
        <span className="hz-nb">「自社の組織って</span>
        <span className="hz-nb">どんな状態？」</span>
        <span className="hz-nb">がわかる</span>
        <span className="hz-landing__big">16タイプ診断</span>
      </h1>
      <p className="hz-landing__sub">
        数値管理、組織、業務フロー、会議コミュニケーションの4軸から、貴社の状態をMBTI風の16タイプに分類。痛みを伴う「組織の限界」と、次の一手（処方箋）を明らかにします。
      </p>
      <p className="hz-landing__meta">
        <span>全{quiz.questions.length}問</span>
        <span>所要時間：約8〜10分</span>
      </p>

      <section className="hz-gains">
        <h2>✨ この診断でわかること・得られるもの</h2>
        <ul>
          <li>16タイプ分類で、自社の「強み」と「見えない弱点」が丸裸に。</li>
          <li>明日から使える「具体的な改善アクションプラン」がわかる。</li>
        </ul>
      </section>
      <aside className="hz-gift">
        <b>🎁 特典</b>
        <p>診断完了後、希望者には専門家（外部COO）による「無料オンライン壁打ち（60分）」をプレゼント。</p>
      </aside>

      <div className="hz-actions">
        <Link className="hz-btn hz-btn--primary" href="/quiz">
          診断をスタートする（無料）
        </Link>
        <Link className="hz-btn" href="/types">
          16タイプについて知る
        </Link>
      </div>

      <p className="hz-supervisor">
        <span>監修</span>Harmonize 代表 米山 望<small>現場主義で組織変革に伴走する専門家</small>
      </p>
    </main>
  );
}
