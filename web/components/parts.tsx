// 画面共通の小さな部品
import Image from "next/image";
import type { AxisDef, AxisResult } from "@/lib/types";

export function Logo() {
  return <Image className="hz-logo" src="/logo.png" alt="Harmonize" width={92} height={92} priority />;
}

/** タイプコードを1文字ずつ、左側(a)は紺・右側(b)はティールで描く */
export function CodeLetters({ code, axes }: { code: string; axes: AxisDef[] }) {
  return (
    <>
      {axes.map((axis, index) => (
        <b key={axis.id} className={code[index] === axis.a.code ? "side-a" : "side-b"}>
          {code[index]}
        </b>
      ))}
    </>
  );
}

const ROW_HEIGHT = 84;
const TRACK_CENTER = 66;
/** 両端の点が枠で切れないよう、0〜1 を 4〜96% に写す */
const spineX = (position: number) => 4 + 92 * position;

/** 4軸を縦に並べ、各軸の位置を線でつないだ「組織の骨格図」 */
export function Spine({ axes }: { axes: AxisResult[] }) {
  const points = axes.map((axis, i) => `${spineX(axis.position).toFixed(2)},${i * ROW_HEIGHT + TRACK_CENTER}`).join(" ");
  return (
    <div className="hz-spine">
      <svg className="hz-spine__line" viewBox={`0 0 100 ${axes.length * ROW_HEIGHT}`} preserveAspectRatio="none" aria-hidden="true">
        <polyline points={points} fill="none" stroke="var(--hz-mist)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
      {axes.map((axis) => (
        <div
          key={axis.id}
          className="hz-spine__row"
          title={`${axis.name}：${axis.score}点（${axis.min}〜${axis.max}点、${axis.threshold}点以下は${axis.a.short}側）`}
        >
          <div className="hz-spine__labels">
            <span className={axis.side === "a" ? "is-on" : ""}>{axis.a.short}</span>
            <span className="hz-spine__axis">
              {axis.name} <strong>{axis.score}点</strong>
            </span>
            <span className={axis.side === "b" ? "is-on" : ""}>{axis.b.short}</span>
          </div>
          <div className="hz-spine__track">
            <i />
            <b className={`hz-spine__dot side-${axis.side}`} style={{ left: `${spineX(axis.position).toFixed(2)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
