"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const STEPS = [
  { id: "01", name: "Retrieve", desc: "Semantic search over guidelines" },
  { id: "02", name: "Generate", desc: "Strict clinical prompt contract" },
  { id: "03", name: "Reflect", desc: "Auditable grounding score" },
  { id: "04", name: "Validate", desc: "Second-model fact-check" },
  { id: "05", name: "Govern", desc: "Audit logs & escalation" },
];

export function ArchitectureDiagram() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section id="platform" className="section-band px-10 py-24">
      <div className="mx-auto max-w-6xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 32 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <p className="section-label">Safety architecture</p>
          <h2 className="mt-2 font-display text-3xl font-bold text-[var(--text-primary)] md:text-4xl">
            Five-layer validation pipeline
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--text-secondary)]">
            A LangGraph state machine replaces linear RAG with a cycle that can re-retrieve,
            self-correct, or escalate — mirroring how careful clinicians reason under uncertainty.
          </p>
        </motion.div>

        <div className="relative mt-12">
            <svg
            viewBox="0 0 900 120"
            className="mb-8 hidden w-full md:block"
            aria-hidden
          >
            <line x1="90" y1="40" x2="810" y2="40" stroke="rgba(255,255,255,0.06)" strokeWidth="2" />
            <motion.line
              x1="90"
              y1="40"
              x2="810"
              y2="40"
              stroke="#0A7A55"
              strokeWidth="2"
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : { opacity: 0 }}
              transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            />
            {STEPS.map((s, i) => {
              const x = 90 + i * 180;
              return (
                <g key={s.id}>
                  <circle cx={x} cy={40} r="18" fill="#0C1825" stroke="#0EC788" strokeWidth="2" />
                  <text
                    x={x}
                    y={45}
                    textAnchor="middle"
                    fill="#0EC788"
                    fontSize="11"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {s.id}
                  </text>
                  <text
                    x={x}
                    y={85}
                    textAnchor="middle"
                    fill="#7A9AB8"
                    fontSize="12"
                    fontFamily="Inter, sans-serif"
                  >
                    {s.name}
                  </text>
                </g>
              );
            })}
            <path
              d="M 720 58 Q 780 90 810 100"
              fill="none"
              stroke="#E84040"
              strokeWidth="1.5"
              strokeDasharray="4 4"
            />
            <text x="780" y="112" fill="#E84040" fontSize="10" fontFamily="JetBrains Mono, monospace">
              FLAG
            </text>
          </svg>

          <div className="grid gap-4 md:grid-cols-5">
            {STEPS.map((s, i) => (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, y: 20 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.1 + i * 0.08, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                className="surface-card p-5 text-center"
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--teal-border)] bg-[var(--teal-muted)] font-mono text-xs font-bold text-[var(--teal)]">
                  {s.id}
                </span>
                <h3 className="mt-3 font-semibold text-[var(--text-primary)]">{s.name}</h3>
                <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
