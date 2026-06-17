"use client";

import { motion, useReducedMotion } from "framer-motion";

const STEPS = [
  { step: "01", name: "Retrieve", desc: "Parent-child semantic search over guidelines" },
  { step: "02", name: "Generate", desc: "Llama 3.1 8B with strict clinical prompt contract" },
  { step: "03", name: "Reflect", desc: "Auditable grounding score in [0, 1]" },
  { step: "04", name: "Validate", desc: "Independent second-model fact-check" },
  { step: "05", name: "Govern", desc: "Recency warnings, audit logs, clinician feedback" },
];

export function PipelineMotion() {
  const reduce = useReducedMotion();

  return (
    <div className="relative mt-12">
      <div className="pointer-events-none absolute left-[10%] right-[10%] top-7 hidden h-px overflow-hidden bg-slate-line md:block">
        <motion.div
          className="h-full origin-left bg-brand"
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.step}
            className="pro-card p-5 text-center"
            initial={reduce ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-20px" }}
            transition={{ duration: 0.45, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
              {s.step}
            </span>
            <h3 className="mt-3 font-semibold text-navy">{s.name}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-muted">{s.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
