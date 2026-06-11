import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DotaSense",
  description: "个人 Dota 2 教练 Dashboard",
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
