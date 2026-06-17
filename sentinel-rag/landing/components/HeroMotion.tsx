"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import { SITE } from "@/lib/site";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

export function HeroMotion() {
  const reduce = useReducedMotion();

  return (
    <section className="gradient-hero relative overflow-hidden px-6 pb-20 pt-14 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.03)_0%,transparent_40%)]" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <motion.div
          variants={reduce ? undefined : container}
          initial={reduce ? false : "hidden"}
          animate="show"
        >
          <motion.div
            variants={reduce ? undefined : item}
            className="mb-6 flex items-center gap-3"
          >
            <Image src="/logo.png" alt="" width={44} height={44} className="rounded-xl" />
            <span className="rounded-md border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-300">
              Enterprise Clinical AI
            </span>
          </motion.div>
          <motion.h1
            variants={reduce ? undefined : item}
            className="text-4xl font-bold leading-[1.12] tracking-tight md:text-5xl"
          >
            Guideline-grounded clinical AI that refuses to be confidently wrong
          </motion.h1>
          <motion.p
            variants={reduce ? undefined : item}
            className="mt-5 max-w-xl text-base leading-relaxed text-slate-300 md:text-lg"
          >
            Sentinel-RAG validates clinical protocol questions against your guideline
            corpus — with deterministic confidence scoring, cross-model verification,
            and human escalation built into every response.
          </motion.p>
          <motion.div variants={reduce ? undefined : item} className="mt-9 flex flex-wrap gap-3">
            <motion.a
              href={SITE.workspaceUrl}
              className="rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white shadow-glow"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              Open clinical workspace
            </motion.a>
            <motion.a
              href="#platform"
              className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/5"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              Explore the platform
            </motion.a>
            <motion.a
              href="#demo"
              className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/5"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              Watch demo
            </motion.a>
            <motion.a
              href="/insights"
              className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-semibold text-slate-200 transition-colors hover:bg-white/5"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              Insights
            </motion.a>
          </motion.div>
        </motion.div>

        <motion.div
          initial={reduce ? false : { opacity: 0, x: 32 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          className="relative"
        >
          <div className="overflow-hidden rounded-xl border border-white/10 bg-navy-mid/40 shadow-2xl">
            <Image
              src="/demo.gif"
              alt="Sentinel-RAG demo"
              width={1100}
              height={640}
              unoptimized
              className="h-auto w-full"
              priority
            />
          </div>
          {!reduce && (
            <div className="absolute -bottom-3 -right-3 rounded-lg border border-brand/30 bg-navy px-3 py-1.5 text-[11px] font-semibold text-brand-light shadow-card">
              Audit-ready confidence scoring
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
