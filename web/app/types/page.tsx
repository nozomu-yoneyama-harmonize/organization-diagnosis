// 16タイプ一覧。結果画面から /types#type-XXXX で開くと、そのタイプへ移動して強調表示する（CSS の :target）
import type { Metadata } from "next";
import Link from "next/link";
import { CodeLetters, Logo } from "@/components/parts";
import { quiz, typeList } from "@/lib/quiz";
import type { TypeInfo } from "@/lib/types";

export const metadata: Metadata = { title: "16タイプについて｜Harmonize 組織診断" };

export default function TypesPage() {
  const groups = new Map<string, TypeInfo[]>();
  for (const item of typeList) groups.set(item.group, [...(groups.get(item.group) ?? []), item]);

  return (
    <main className="hz-page hz-types">
      <Logo />
      <h1>16タイプについて</h1>
      <p className="hz-types__lede">
        4つの軸それぞれで、どちらの傾向が強いかを1文字で表し、組み合わせた4文字がタイプ名になります。
      </p>
      <ul className="hz-legend">
        {quiz.axes.map((axis) => (
          <li key={axis.id}>
            <b className="side-a">{axis.a.code}</b>
            {axis.a.short}
            <i>／</i>
            <b className="side-b">{axis.b.code}</b>
            {axis.b.short}
            <small>{axis.name}</small>
          </li>
        ))}
      </ul>

      {[...groups].map(([group, items]) => (
        <section key={group} className="hz-types__group">
          <h2>{group}</h2>
          {items.map((item) => (
            <article key={item.code} id={`type-${item.code}`} className="hz-type">
              <div className="hz-type__code">
                <CodeLetters code={item.code} axes={quiz.axes} />
                <span>型</span>
              </div>
              <h3>{item.name}</h3>
              <p>{item.feature}</p>
            </article>
          ))}
        </section>
      ))}

      <div className="hz-actions">
        <Link className="hz-btn hz-btn--primary" href="/quiz">
          診断をスタートする（無料）
        </Link>
        <Link className="hz-btn hz-btn--quiet" href="/">
          トップに戻る
        </Link>
      </div>
    </main>
  );
}
