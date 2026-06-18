import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { ClinicalWorkspace } from "@/components/ClinicalWorkspace";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: "Live workspace · Sentinel-RAG",
  description:
    "Interactive clinical protocol validation — Next.js workspace connected to the Sentinel-RAG FastAPI agent.",
};

export default function WorkspacePage() {
  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <header className="sticky top-0 z-[100] border-b border-[var(--border-subtle)] bg-[rgba(6,13,20,0.95)] backdrop-blur-sm">
        <div className="mx-auto flex h-[60px] max-w-6xl items-center justify-between px-6 md:px-10">
          <Link href="/" className="flex items-center gap-2.5 no-underline">
            <Image src="/logo.png" alt="Sentinel-RAG" width={28} height={28} className="rounded-md" />
            <span className="text-[15px] font-semibold text-[var(--text-primary)]">Sentinel-RAG</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/" className="nav-link no-underline">
              Home
            </Link>
            <Link href="/insights" className="nav-link no-underline hidden sm:inline">
              Insights
            </Link>
            <a
              href={SITE.githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="nav-link no-underline hidden sm:inline"
            >
              GitHub
            </a>
            <Link
              href="/workspace"
              className="rounded-md bg-[var(--teal)] px-4 py-2 text-sm font-semibold text-[var(--bg-base)] no-underline"
            >
              Live demo
            </Link>
          </nav>
        </div>
      </header>

      <main className="px-6 py-12 md:px-10">
        <ClinicalWorkspace />
      </main>

      <footer className="border-t border-[var(--border-subtle)] px-6 py-8 text-center text-[13px] text-[var(--text-muted)]">
        Research prototype — not for clinical decision-making.{" "}
        <a href={SITE.streamlitUrl} className="text-[var(--teal)] no-underline hover:underline">
          Open Streamlit workspace
        </a>
      </footer>
    </div>
  );
}
