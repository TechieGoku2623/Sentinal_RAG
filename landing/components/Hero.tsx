"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ConfidenceDemoHero } from "./ConfidenceDemoHero";

export function Hero() {
  return (
    <section
      id="demo"
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-10 pb-20 pt-[120px] text-center"
    >
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(14,199,136,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(14,199,136,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, black, transparent)",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-[1] mb-7"
      >
        <span
          className="inline-block rounded px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--teal)]"
          style={{
            background: "rgba(14,199,136,0.1)",
            border: "1px solid rgba(14,199,136,0.2)",
          }}
        >
          Clinical AI Safety Layer
        </span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-[1] m-0 mb-6 max-w-[700px] font-display text-[clamp(40px,6vw,72px)] font-extrabold leading-[1.08] tracking-[-0.03em] text-[var(--text-primary)]"
      >
        Clinical AI that knows
        <br />
        <span className="text-[var(--teal)]">when to say &ldquo;I don&apos;t know.&rdquo;</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-[1] m-0 mb-12 max-w-[520px] text-lg leading-relaxed text-[var(--text-secondary)]"
      >
        Sentinel-RAG validates clinical protocols against your own guidelines — and escalates instead
        of hallucinating.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-[1] mb-[72px] flex gap-3"
      >
        <motion.a
          href="#platform"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          className="flex items-center gap-2 rounded-lg bg-[var(--teal)] px-7 py-3 text-[15px] font-semibold text-[var(--bg-base)] no-underline"
        >
          See the pipeline →
        </motion.a>
        <Link href="/workspace">
          <motion.span
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            className="inline-block cursor-pointer rounded-lg border border-[var(--border-default)] px-7 py-3 text-[15px] font-medium text-[var(--text-secondary)] no-underline"
          >
            Open live workspace
          </motion.span>
        </Link>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 0.45, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-[1] w-full max-w-[640px]"
      >
        <ConfidenceDemoHero />
      </motion.div>
    </section>
  );
}
