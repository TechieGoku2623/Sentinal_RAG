"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ConfidenceArc } from "./ConfidenceArc";

interface Props {
  answer: string;
  confidence: number;
  retries: number;
  latencyMs: number;
  docCount: number;
  flagged: boolean;
  sources: { id: string; section: string; excerpt: string }[];
  onRate?: (rating: 1 | 2 | 3) => void;
}

export function AnswerCard({
  answer,
  confidence,
  retries,
  latencyMs,
  docCount,
  flagged,
  sources,
  onRate,
}: Props) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const [rated, setRated] = useState<number | null>(null);

  const borderColor =
    confidence >= 85
      ? "rgba(14,199,136,0.2)"
      : confidence >= 75
        ? "rgba(240,165,0,0.2)"
        : "rgba(232,64,64,0.3)";

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-[10px]"
      style={{ background: "var(--bg-surface)", border: `1px solid ${borderColor}` }}
    >
      {flagged && (
        <motion.div
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
          className="absolute bottom-0 left-0 top-0 w-[3px] rounded-l-[10px] bg-[#E84040]"
        />
      )}

      <div className="flex items-start justify-between gap-4 p-5 pb-0">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.4 }}
          className="m-0 flex-1 text-[15px] leading-[1.75] text-[var(--text-primary)]"
        >
          {answer}
        </motion.p>
        <motion.div
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="shrink-0"
        >
          <ConfidenceArc value={confidence} />
        </motion.div>
      </div>

      <AnimatePresence>
        {flagged && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="mx-5 mt-4 overflow-hidden"
          >
            <div
              className="flex items-start gap-2.5 rounded-md px-3.5 py-2.5"
              style={{
                background: "rgba(232,64,64,0.08)",
                border: "1px solid rgba(232,64,64,0.25)",
              }}
            >
              <span className="mt-0.5 text-sm">⚠</span>
              <div>
                <p className="m-0 mb-1 font-mono text-[11px] uppercase tracking-[0.08em] text-[#E84040]">
                  Flagged for clinical review
                </p>
                <p className="m-0 text-[13px] leading-snug text-[var(--text-secondary)]">
                  Confidence below threshold. A qualified clinician must verify this response before
                  clinical use.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.3 }}
        className="mt-4 flex gap-5 border-t border-[var(--border-subtle)] px-5 py-3.5"
      >
        {[
          { label: "Retries", value: retries },
          { label: "Latency", value: `${latencyMs}ms` },
          { label: "Sources", value: docCount },
        ].map((m) => (
          <div key={m.label} className="flex flex-col gap-0.5">
            <span className="text-[11px] uppercase tracking-[0.06em] text-[var(--text-muted)]">
              {m.label}
            </span>
            <span className="font-mono text-sm font-medium text-[var(--text-primary)]">{m.value}</span>
          </div>
        ))}
      </motion.div>

      {sources.length > 0 && (
        <div className="border-t border-[var(--border-subtle)]">
          <button
            type="button"
            onClick={() => setCitationsOpen((o) => !o)}
            className="flex w-full cursor-pointer items-center justify-between border-none bg-transparent px-5 py-2.5 text-[13px] text-[var(--text-secondary)]"
          >
            <span>
              {sources.length} source{sources.length > 1 ? "s" : ""}
            </span>
            <motion.span animate={{ rotate: citationsOpen ? 180 : 0 }} transition={{ duration: 0.22 }}>
              ▼
            </motion.span>
          </button>
          <AnimatePresence>
            {citationsOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                className="overflow-hidden"
              >
                <div className="flex flex-col gap-2 px-5 pb-4">
                  {sources.map((src, i) => (
                    <motion.div
                      key={src.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05, duration: 0.25 }}
                      className="rounded-md border-l-2 border-[var(--teal-dim)] bg-[var(--bg-elevated)] px-3 py-2"
                    >
                      <p className="m-0 mb-1 font-mono text-[11px] text-[var(--teal)]">
                        {src.id} · {src.section}
                      </p>
                      <p className="m-0 text-[13px] leading-snug text-[var(--text-secondary)]">
                        {src.excerpt}
                      </p>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {onRate && (
        <div className="flex items-center gap-2 border-t border-[var(--border-subtle)] px-5 py-2.5">
          <span className="mr-1 text-xs text-[var(--text-muted)]">Rate this response</span>
          {(["👍", "👌", "👎"] as const).map((emoji, i) => (
            <motion.button
              key={emoji}
              type="button"
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => {
                setRated(i + 1);
                onRate((i + 1) as 1 | 2 | 3);
              }}
              className="cursor-pointer rounded-md px-2.5 py-1 text-base"
              style={{
                background: rated === i + 1 ? "var(--bg-elevated)" : "transparent",
                border: `1px solid ${rated === i + 1 ? "var(--border-strong)" : "var(--border-subtle)"}`,
              }}
            >
              {emoji}
            </motion.button>
          ))}
        </div>
      )}
    </motion.div>
  );
}
