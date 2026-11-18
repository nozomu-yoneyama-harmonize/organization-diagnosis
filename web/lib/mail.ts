// 診断結果メールの組み立てと送信（Resend）。core/mailer.py の文面を移植。
import "server-only";
import { Resend } from "resend";
import type { AxisResult, Diagnosis } from "./types";

const SENDER_NAME = "Harmonize 組織診断";

export class MailNotConfigured extends Error {}

const escapeHtml = (text: string) =>
  text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

const axisLine = (axis: AxisResult) => {
  const chosen = axis[axis.side];
  return `${axis.name}：${axis.score}点（${axis.min}〜${axis.max}点）　判定 ${chosen.code}（${chosen.full}）`;
};

export function buildSubject(diagnosis: Diagnosis): string {
  return `【Harmonize 組織診断】診断結果：${diagnosis.type.code}型 ${diagnosis.type.name}`;
}

export function buildText(diagnosis: Diagnosis, bookingUrl: string): string {
  const item = diagnosis.type;
  return [
    "Harmonize 組織診断の結果をお送りします。",
    "",
    `${item.code}型：${item.name}\n${item.group}`,
    "",
    `■ 組織傾向の特徴\n${item.feature}`,
    "",
    `■ 4軸のスコア\n${diagnosis.axes.map(axisLine).join("\n")}`,
    "",
    `■ 組織の強み\n${item.strength}`,
    "",
    `■ 組織の弱み\n${item.weakness}`,
    "",
    `■ 改善に向けたポイント\n${item.improvement}`,
    "",
    `無料ご相談（60分）のお申し込みはこちら\n${bookingUrl}`,
    "",
  ].join("\n");
}

export function buildHtml(diagnosis: Diagnosis, bookingUrl: string): string {
  const item = diagnosis.type;
  const heading = 'style="color:#173156;font-size:16px;margin:28px 0 8px"';
  const paragraph = 'style="margin:0;line-height:1.8"';
  const rows = diagnosis.axes
    .map(
      (axis) =>
        `<tr><td style="padding:6px 12px 6px 0">${escapeHtml(axis.name)}</td>` +
        `<td style="padding:6px 12px 6px 0;white-space:nowrap"><b>${axis.score}点</b></td>` +
        `<td style="padding:6px 0">${axis.code}（${escapeHtml(axis[axis.side].full)}）</td></tr>`,
    )
    .join("");
  return (
    '<div style="max-width:560px;margin:0 auto;padding:24px 16px;color:#1c2b3a;font-size:15px;' +
    "font-family:'Hiragino Sans',Meiryo,sans-serif\">" +
    '<p style="margin:0;color:#5a6b78">Harmonize 組織診断の結果をお送りします。</p>' +
    `<p style="margin:16px 0 0;color:#5a6b78">${escapeHtml(item.group)}</p>` +
    `<h1 style="color:#173156;font-size:40px;line-height:1.2;margin:4px 0">${item.code}型</h1>` +
    `<p style="margin:0;color:#173156;font-size:22px;font-weight:bold">${escapeHtml(item.name)}</p>` +
    `<h2 ${heading}>組織傾向の特徴</h2><p ${paragraph}>${escapeHtml(item.feature)}</p>` +
    `<h2 ${heading}>4軸のスコア</h2><table style="border-collapse:collapse">${rows}</table>` +
    `<h2 ${heading}>組織の強み</h2><p ${paragraph}>${escapeHtml(item.strength)}</p>` +
    `<h2 ${heading}>組織の弱み</h2><p ${paragraph}>${escapeHtml(item.weakness)}</p>` +
    `<h2 ${heading}>改善に向けたポイント</h2><p ${paragraph}>${escapeHtml(item.improvement)}</p>` +
    `<p style="margin:32px 0 0;text-align:center"><a href="${escapeHtml(bookingUrl)}" ` +
    'style="display:inline-block;background:#173156;color:#fff;padding:14px 32px;border-radius:28px;' +
    'font-weight:bold;text-decoration:none">無料ご相談（60分）に申し込む</a></p>' +
    "</div>"
  );
}

export async function sendResultMail(diagnosis: Diagnosis, to: string, bookingUrl: string): Promise<void> {
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.MAIL_FROM;
  if (!apiKey || !from) throw new MailNotConfigured("RESEND_API_KEY / MAIL_FROM が未設定です");
  const { error } = await new Resend(apiKey).emails.send({
    from: `${SENDER_NAME} <${from}>`,
    to,
    subject: buildSubject(diagnosis),
    text: buildText(diagnosis, bookingUrl),
    html: buildHtml(diagnosis, bookingUrl),
  });
  if (error) throw new Error(`Resend: ${error.name} ${error.message}`);
}
