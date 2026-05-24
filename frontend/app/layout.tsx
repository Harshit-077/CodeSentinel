import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CodeSentinel | AI Code Review",
  description: "Multi-agent autonomous code review and security intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body className="bg-gray-950 text-gray-100 antialiased selection:bg-brand-500/30 selection:text-brand-100">
        {children}
      </body>
    </html>
  );
}