import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Care Plan Generator",
  description: "AI-powered care plan generator for specialty pharmacy",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
