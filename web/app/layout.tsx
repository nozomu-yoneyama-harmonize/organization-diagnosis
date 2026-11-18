import type { Metadata } from "next";
import { Zen_Kaku_Gothic_New } from "next/font/google";
import "./globals.css";

const zen = Zen_Kaku_Gothic_New({
  variable: "--font-zen",
  weight: ["400", "500", "700", "900"],
  subsets: ["latin"],
  display: "swap",
  preload: false, // 日本語フォントは容量が大きいため、使う文字だけ読み込ませる
});

export const metadata: Metadata = {
  title: "Harmonize 組織診断｜16タイプで自社の組織状態がわかる",
  description:
    "数値管理、組織、業務フロー、会議コミュニケーションの4軸から、貴社の状態を16タイプに分類。全60問・約8〜10分の無料診断です。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className={zen.variable}>
      <body>{children}</body>
    </html>
  );
}
