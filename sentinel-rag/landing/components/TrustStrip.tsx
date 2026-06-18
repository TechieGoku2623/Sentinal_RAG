"use client";

import { useEffect, useRef } from "react";
import { Shield, Timer, CheckCircle2, AlertTriangle } from "lucide-react";
import { METRICS } from "@/lib/metrics";
import { fadeUp, prefersReducedMotion, revertAnim, type AnimInstance } from "@/lib/motion/anime";
import { useAnimeInView } from "@/hooks/useAnimeInView";

const STRIP = [
  {
    icon: CheckCircle2,
    label: "Keyword match",
    value: METRICS.keywordMatch,
    detail: `${METRICS.questions} eval questions`,
  },
  {
    icon: Shield,
    label: "Validation agree",
    value: METRICS.validationAgreement,
    detail: "Cross-model fact-check",
  },
  {
    icon: AlertTriangle,
    label: "Flag rate",
    value: METRICS.flagRate,
    detail: "Escalated for review",
  },
  {
    icon: Timer,
    label: "Avg latency",
    value: METRICS.avgLatency,
    detail: "Standard profile",
  },
] as const;

export function TrustStrip() {
  const { ref, inView } = useAnimeInView<HTMLElement>({ rootMargin: "-30px" });
  const labelRef = useRef<HTMLParagraphElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<AnimInstance | null>(null);

  useEffect(() => {
    if (!inView) return;

    if (prefersReducedMotion()) {
      if (labelRef.current) labelRef.current.style.opacity = "1";
      cardsRef.current?.querySelectorAll<HTMLElement>("[data-trust-card]").forEach((el) => {
        el.style.opacity = "1";
      });
      return;
    }

    const labelAnim = labelRef.current
      ? fadeUp(labelRef.current, { duration: 420, y: 12 })
      : null;

    const cards = cardsRef.current?.querySelectorAll("[data-trust-card]");
    const cardsAnim = cards?.length
      ? fadeUp(cards, { staggerMs: 90, delay: 80, duration: 480, y: 20 })
      : null;

    animRef.current = cardsAnim ?? labelAnim;

    return () => revertAnim(animRef.current);
  }, [inView]);

  return (
    <section
      ref={ref}
      id="trust"
      className="border-y border-[var(--color-rule)] bg-[var(--color-paper-2)] px-6 py-8"
      aria-label="Evaluation metrics"
    >
      <div className="mx-auto max-w-6xl">
        <p
          ref={labelRef}
          className="section-label text-center md:text-left"
          style={{ opacity: prefersReducedMotion() ? 1 : 0 }}
        >
          Measured trust signals
        </p>
        <div ref={cardsRef} className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STRIP.map((item) => (
            <div
              key={item.label}
              data-trust-card
              className="surface-card trust-card flex cursor-default items-start gap-3 p-4"
              style={{ opacity: prefersReducedMotion() ? 1 : 0 }}
            >
              <item.icon
                className="mt-0.5 size-5 shrink-0 text-[var(--color-accent)]"
                aria-hidden
              />
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--color-ink-2)]">
                  {item.label}
                </p>
                <p className="font-display mt-1 text-2xl font-semibold tabular-nums text-[var(--color-ink)]">
                  {item.value}
                </p>
                <p className="mt-1 text-xs text-[var(--color-ink-2)]">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
