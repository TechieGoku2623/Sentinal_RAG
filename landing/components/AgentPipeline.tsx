"use client";

import { motion, AnimatePresence } from "framer-motion";

export type AgentStage = "retrieve" | "generate" | "reflect" | "output" | "flag" | "idle";

const STAGES: { id: AgentStage; label: string; icon: string }[] = [
  { id: "retrieve", label: "Retrieve", icon: "⬡" },
  { id: "generate", label: "Generate", icon: "◈" },
  { id: "reflect", label: "Reflect", icon: "◎" },
  { id: "output", label: "Output", icon: "◆" },
];

export function AgentPipeline({ stage }: { stage: AgentStage }) {
  const currentIdx = STAGES.findIndex((s) => s.id === stage);

  return (
    <div
      className="flex items-center gap-0 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3"
      style={{ marginBottom: 16 }}
    >
      {STAGES.map((s, i) => {
        const isActive = s.id === stage;
        const isDone = currentIdx > i;
        const isFlagged = stage === "flag" && s.id === "reflect";

        return (
          <div key={s.id} className="flex items-center">
            <motion.div
              animate={{
                color: isActive
                  ? "#0EC788"
                  : isDone
                    ? "#0A7A55"
                    : isFlagged
                      ? "#E84040"
                      : "var(--text-muted)",
                scale: isActive ? 1.1 : 1,
              }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col items-center gap-1"
            >
              <div className="relative h-7 w-7">
                <AnimatePresence>
                  {isActive && (
                    <motion.div
                      key="ring"
                      initial={{ scale: 0.6, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 1.4, opacity: 0 }}
                      className="absolute inset-[-4px] rounded-full border border-[rgba(14,199,136,0.4)]"
                      style={{ animation: "pulseRing 2s ease infinite" }}
                    />
                  )}
                </AnimatePresence>
                <div
                  className="flex h-7 w-7 items-center justify-center rounded-full text-[13px]"
                  style={{
                    background: isActive ? "rgba(14,199,136,0.12)" : "transparent",
                    border: `1px solid ${isActive ? "rgba(14,199,136,0.4)" : "var(--border-subtle)"}`,
                  }}
                >
                  {isDone ? "✓" : s.icon}
                </div>
              </div>
              <span className="font-mono text-[9px] uppercase tracking-[0.08em]">{s.label}</span>
            </motion.div>

            {i < STAGES.length - 1 && (
              <div
                className="relative mx-1 mb-4 h-px w-8 bg-[var(--border-subtle)]"
                style={{ marginBottom: 16 }}
              >
                <motion.div
                  animate={{ width: isDone ? "100%" : "0%" }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="absolute inset-0 h-full bg-[var(--teal-dim)]"
                />
              </div>
            )}
          </div>
        );
      })}

      <AnimatePresence>
        {stage === "retrieve" && (
          <motion.div
            key="retry"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="ml-auto rounded px-2 py-0.5 font-mono text-[11px] text-[var(--amber)]"
            style={{
              background: "rgba(240,165,0,0.1)",
              border: "1px solid rgba(240,165,0,0.2)",
            }}
          >
            re-querying
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
