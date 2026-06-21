import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eterna Studio",
  description: "General AI workflow canvas"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
