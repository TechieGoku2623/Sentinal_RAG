"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const FEATURES = [
  {
    tag: "RETRIEVE",
    title: "Grounded answers",
    body: "Strict context-only generation with dated source citations and provenance metadata.",
  },
  {
    tag: "REFLECT",
    title: "Self-audit loop",
    body: "Deterministic four-factor confidence scoring before any answer reaches a clinician.",
  },
  {
    tag: "ESCALATE",
    title: "Human escalation",
    body: "Low-confidence outputs are flagged for review — uncertainty is a safety success.",
  },
  {
    tag: "GOVERN",
    title: "Privacy-first",
    body: "Local ChromaDB, CPU embeddings, and a self-hostable open-weights LLM path.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export function FeatureGrid() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section className="mx-auto max-w-6xl px-10 py-24">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 32 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="mb-12"
      >
        <p className="section-label">Why Sentinel-RAG</p>
        <h2 className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)] md:text-4xl">
          Built for clinical trust, not chatbot fluency
        </h2>
      </motion.div>

      <motion.div
        variants={container}
        initial="hidden"
        animate={inView ? "show" : "hidden"}
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      >
        {FEATURES.map((f) => (
          <motion.div
            key={f.tag}
            variants={item}
            className="surface-card p-6"
            whileHover={{ borderColor: "var(--border-strong)", y: -2 }}
            transition={{ duration: 0.12 }}
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--teal)]">
              {f.tag}
            </p>
            <h3 className="mt-2 font-display text-lg font-semibold text-[var(--text-primary)]">
              {f.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{f.body}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
