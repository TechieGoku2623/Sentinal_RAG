import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const syne = Syne({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://devasai.github.io/sentinel-rag"),
  title: "Sentinel-RAG — Clinical Protocol Guardian",
  description:
    "Enterprise-grade self-reflective RAG for guideline-grounded clinical protocol validation.",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "Sentinel-RAG · Clinical Protocol Guardian",
    description: "Self-reflective clinical AI that refuses to be confidently wrong.",
    images: ["/logo.png"],
  },
};

export const viewport: Viewport = {
  themeColor: "#060D14",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={cn(syne.variable, inter.variable, jetbrains.variable)}
    >
      <body className="min-h-screen bg-[var(--bg-base)] font-sans antialiased text-[var(--text-primary)]">
        {children}
      </body>
    </html>
  );
}
