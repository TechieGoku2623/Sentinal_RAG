import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-ibm-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://devasai.github.io/sentinel-rag"),
  title: "Sentinel-RAG · Clinical Protocol Guardian",
  description:
    "Enterprise-grade self-reflective RAG for guideline-grounded clinical protocol validation. Deterministic confidence scoring, cross-model verification, and human escalation.",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  themeColor: "#0A1628",
  openGraph: {
    title: "Sentinel-RAG · Clinical Protocol Guardian",
    description:
      "Self-reflective clinical AI that refuses to be confidently wrong.",
    images: ["/logo.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${ibmPlexMono.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
