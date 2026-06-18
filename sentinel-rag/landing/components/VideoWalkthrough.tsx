"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { SITE } from "@/lib/site";
import { FadeIn } from "./FadeIn";

export function VideoWalkthrough() {
  const hasLoom = Boolean(SITE.loomEmbedUrl);
  const hasYouTube = Boolean(SITE.youtubeEmbedId);
  const hasVideo = hasLoom || hasYouTube;

  const embedSrc = hasLoom
    ? SITE.loomEmbedUrl
    : hasYouTube
      ? `https://www.youtube.com/embed/${SITE.youtubeEmbedId}`
      : null;

  const shareUrl = SITE.loomShareUrl || SITE.youtubeWatchUrl;

  return (
    <section id="walkthrough" className="graphite-band border-y border-[var(--border-subtle)] px-6 py-24 md:px-10">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="section-label">Video walkthrough</p>
          <h2 className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)] md:text-4xl">
            Watch Sentinel-RAG in action
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--text-secondary)]">
            {hasVideo
              ? "Protocol validation, confidence scoring, self-correction, and human escalation — a full product tour for GitHub and LinkedIn."
              : "Record a 3-minute walkthrough with the script in docs/VIDEO_WALKTHROUGH.md, then embed your Loom or YouTube link below."}
          </p>
        </FadeIn>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 overflow-hidden rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[0_24px_64px_rgba(0,0,0,0.35)]"
        >
          {hasVideo && embedSrc ? (
            <div className="relative aspect-video w-full bg-black">
              <iframe
                src={embedSrc}
                title="Sentinel-RAG video walkthrough"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="absolute inset-0 h-full w-full border-0"
              />
            </div>
          ) : (
            <div className="relative">
              <Image
                src="/demo.gif"
                alt="Sentinel-RAG animated demo preview"
                width={1200}
                height={680}
                unoptimized
                className="h-auto w-full opacity-80"
              />
              <div className="absolute inset-0 flex items-center justify-center bg-[rgba(6,13,20,0.72)] backdrop-blur-[2px]">
                <div className="mx-4 max-w-lg rounded-xl border border-[rgba(14,199,136,0.25)] bg-[var(--bg-elevated)] p-8 text-center">
                  <p className="text-lg font-semibold text-[var(--text-primary)]">Record your walkthrough</p>
                  <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                    Follow{" "}
                    <code className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 text-xs text-[var(--teal)]">
                      docs/VIDEO_WALKTHROUGH.md
                    </code>
                    , upload to Loom or YouTube, then set{" "}
                    <code className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 text-xs text-[var(--teal)]">
                      NEXT_PUBLIC_LOOM_EMBED_URL
                    </code>{" "}
                    in{" "}
                    <code className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 text-xs text-[var(--teal)]">
                      landing/.env.local
                    </code>
                  </p>
                  <Link
                    href="/workspace"
                    className="mt-5 inline-block rounded-lg bg-[var(--teal)] px-5 py-2.5 text-sm font-semibold text-[var(--bg-base)] no-underline"
                  >
                    Try live workspace instead →
                  </Link>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-sm text-[var(--text-muted)]">
          {shareUrl ? (
            <a
              href={shareUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--teal)] no-underline hover:underline"
            >
              Open full video →
            </a>
          ) : null}
          <Link href="/workspace" className="text-[var(--teal)] no-underline hover:underline">
            Interactive demo
          </Link>
          <a
            href={`${SITE.docsUrl}/VIDEO_WALKTHROUGH.md`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--teal)] no-underline hover:underline"
          >
            Recording script
          </a>
        </div>
      </div>
    </section>
  );
}
