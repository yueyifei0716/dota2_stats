import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DotaSense - Dota 2 训练驾驶舱",
  description: "用最近比赛生成三局训练挑战、英雄百分位评分卡和证据化复盘。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
