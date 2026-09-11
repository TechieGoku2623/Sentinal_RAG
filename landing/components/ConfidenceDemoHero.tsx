"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ConfidenceArc } from "./ConfidenceArc";

const DEMOS = [
  {
    query: "What is the first-line treatment for Type 2 diabetes?",
    answer:
      "Metformin is the recommended first-line pharmacological therapy for adults with type 2 diabetes mellitus unless contraindicated.",
    confidence: 98,
    flagged: false,
    retries: 0,
    source: "GLY-2024 §1",
  },
  {
    query: "Can metformin be used with kidney disease?",
    answer:
      "Metformin can be used in kidney disease only with careful attention to renal function. It is contraindicated when eGFR falls below 30 mL/min/1.73m².",
    confidence: 88,
    flagged: false,
    retries: 1,
    source: "GLY-2024 §4",
  },
  {
    query: "What happens if a patient misses a dose?",
    answer:
      "The provided guidelines do not address missed dose instructions. This information is not in the available protocol.",
    confidence: 27,
    flagged: true,
    retries: 0,
    source: null,
  },
] as const;

export function ConfidenceDemoHero() {
  const [idx, setIdx] = useState(0);
  const demo = DEMOS[idx];

  useEffect(() => {
    const t = setTimeout(() => setIdx((i) => (i + 1) % DEMOS.length), 4500);
    return () => clearTimeout(t);
  }, [idx]);

  const borderColor =
    demo.confidence >= 85
      ? "rgba(14,199,136,0.25)"
      : demo.confidence >= 75
        ? "rgba(240,165,0,0.25)"
        : "rgba(232,64,64,0.3)";

  return (
    <div
      className="overflow-hidden rounded-xl text-left"
      style={{ background: "var(--bg-surface)", border: `1px solid ${borderColor}` }}
    >
      <div
        className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-2.5"
        style={{ background: "var(--bg-elevated)" }}
      >
        {(["#E84040", "#F0A500", "#0EC788"] as const).map((c) => (
          <div key={c} className="h-2.5 w-2.5 rounded-full opacity-60" style={{ background: c }} />
        ))}
        <span className="ml-2 font-mono text-[11px] tracking-[0.06em] text-[var(--text-muted)]">
          sentinel-rag — clinical workspace
        </span>
        <div className="ml-auto flex gap-1.5">
          {DEMOS.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setIdx(i)}
              className="h-1.5 w-1.5 cursor-pointer rounded-full border-none p-0"
              style={{
                background: i === idx ? "var(--teal)" : "rgba(255,255,255,0.15)",
              }}
              aria-label={`Demo ${i + 1}`}
            />
          ))}
        </div>
      </div>

      <div className="px-5 pt-4">
        <AnimatePresence mode="wait">
          <motion.p
            key={demo.query}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            className="mb-3 font-mono text-xs tracking-wide text-[var(--teal)]"
          >
            &gt; {demo.query}
          </motion.p>
        </AnimatePresence>
      </div>

      <div className="flex items-start gap-4 px-5 pb-4">
        <AnimatePresence mode="wait">
          <motion.p
            key={demo.answer}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
            className="m-0 flex-1 text-sm leading-relaxed"
            style={{ color: demo.flagged ? "var(--text-secondary)" : "var(--text-primary)" }}
          >
            {demo.answer}
          </motion.p>
        </AnimatePresence>
        <AnimatePresence mode="wait">
          <motion.div
            key={demo.confidence}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={{ duration: 0.35, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <ConfidenceArc value={demo.confidence} size={72} />
          </motion.div>
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {demo.flagged && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div
              className="mx-5 mb-4 flex items-center gap-2 rounded-md px-3 py-2"
              style={{
                background: "rgba(232,64,64,0.08)",
                border: "1px solid rgba(232,64,64,0.25)",
              }}
            >
              <span className="text-xs">⚠</span>
              <span className="font-mono text-[11px] uppercase tracking-[0.06em] text-[#E84040]">
                Flagged for clinical review
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center gap-5 border-t border-[var(--border-subtle)] px-5 py-2.5">
        {(
          [
            ["Retries", demo.retries],
            ["Source", demo.source ?? "—"],
          ] as const
        ).map(([label, val]) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="text-[11px] uppercase tracking-[0.06em] text-[var(--text-muted)]">
              {label}
            </span>
            <span className="font-mono text-xs text-[var(--text-secondary)]">{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
