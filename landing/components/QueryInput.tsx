"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export function QueryInput({
  onSubmit,
  isLoading,
}: {
  onSubmit: (q: string) => void;
  isLoading: boolean;
}) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);

  const submit = () => {
    const q = value.trim();
    if (q && !isLoading) onSubmit(q);
  };

  return (
    <div className="mb-6">
      <motion.div
        animate={{
          borderColor: focused ? "rgba(14,199,136,0.4)" : "rgba(255,255,255,0.09)",
          boxShadow: focused ? "0 0 0 3px rgba(14,199,136,0.08)" : "0 0 0 0 transparent",
        }}
        transition={{ duration: 0.18 }}
        className="overflow-hidden rounded-lg border bg-[var(--bg-surface)]"
      >
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask a clinical protocol question..."
          rows={3}
          className="w-full resize-none border-none bg-transparent p-4 text-[15px] leading-relaxed text-[var(--text-primary)] outline-none"
          style={{ fontFamily: "var(--font-body)" }}
        />
        <div className="flex items-center justify-between border-t border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2">
          <span className="font-mono text-[11px] text-[var(--text-muted)]">⌘↵ to submit</span>
          <motion.button
            type="button"
            whileHover={!isLoading && value.trim() ? { scale: 1.02 } : {}}
            whileTap={!isLoading && value.trim() ? { scale: 0.97 } : {}}
            onClick={submit}
            disabled={!value.trim() || isLoading}
            className="flex min-w-[100px] items-center justify-center gap-2 rounded-md px-4 py-1.5 text-[13px] font-semibold"
            style={{
              background: value.trim() && !isLoading ? "var(--teal)" : "var(--bg-overlay)",
              color: value.trim() && !isLoading ? "var(--bg-base)" : "var(--text-muted)",
              cursor: value.trim() && !isLoading ? "pointer" : "not-allowed",
            }}
          >
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div
                  key="spinner"
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.7 }}
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-[var(--text-secondary)]"
                />
              ) : (
                <motion.span key="label" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  Validate
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
