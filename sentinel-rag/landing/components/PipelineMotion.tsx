"use client";

import { useEffect, useRef } from "react";
import {
  pipelineEntrance,
  prefersReducedMotion,
  revertAnim,
  type AnimInstance,
} from "@/lib/motion/anime";

const STEPS = [
  { step: "01", name: "Retrieve", desc: "Parent-child semantic search over guidelines" },
  { step: "02", name: "Generate", desc: "Llama 3.1 8B with strict clinical prompt contract" },
  { step: "03", name: "Reflect", desc: "Auditable grounding score in [0, 1]" },
  { step: "04", name: "Validate", desc: "Independent second-model fact-check" },
  { step: "05", name: "Govern", desc: "Recency warnings, audit logs, clinician feedback" },
];

export function PipelineMotion() {
  const rootRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<AnimInstance | null>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    if (prefersReducedMotion()) {
      root.querySelectorAll<HTMLElement>("[data-pipeline-step]").forEach((el) => {
        el.style.opacity = "1";
      });
      const line = root.querySelector<HTMLElement>("[data-pipeline-line]");
      if (line) line.style.transform = "scaleX(1)";
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        animRef.current = pipelineEntrance(root);
      },
      { threshold: 0.15, rootMargin: "-20px" },
    );

    observer.observe(root);
    return () => {
      observer.disconnect();
      revertAnim(animRef.current);
    };
  }, []);

  return (
    <div ref={rootRef} className="relative mt-12">
      <div className="pointer-events-none absolute left-[10%] right-[10%] top-7 hidden h-px overflow-hidden bg-slate-line md:block">
        <div
          data-pipeline-line
          className="h-full origin-left bg-brand"
          style={{ transform: "scaleX(0)" }}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        {STEPS.map((s) => (
          <div
            key={s.step}
            data-pipeline-step
            className="surface-card pipeline-card p-5 text-center"
            style={{ opacity: 0 }}
          >
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
              {s.step}
            </span>
            <h3 className="mt-3 font-semibold text-navy">{s.name}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-muted">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
