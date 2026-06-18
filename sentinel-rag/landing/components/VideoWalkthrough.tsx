"use client";

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
              : "Full 7-clip walkthrough (~58s) generated with MoviePy + Pillow. Replace with your Loom recording via .env.local when ready."}
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
            <div className="relative aspect-video w-full bg-black">
              <video
                className="h-full w-full object-contain"
                controls
                autoPlay
                muted
                loop
                playsInline
                poster="/logo.png"
              >
                <source src="/walkthrough.mp4" type="video/mp4" />
                <source src="/demo.mp4" type="video/mp4" />
                Your browser does not support embedded video.
              </video>
              <p className="absolute bottom-3 right-3 rounded-md bg-[rgba(6,13,20,0.85)] px-2.5 py-1 font-mono text-[10px] text-[var(--text-muted)]">
                Auto-generated demo · replace with Loom via .env.local
              </p>
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
