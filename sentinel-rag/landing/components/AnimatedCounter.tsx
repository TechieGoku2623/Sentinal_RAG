"use client";

import { useEffect, useRef } from "react";
import {
  animateCounter,
  prefersReducedMotion,
  revertAnim,
  type AnimInstance,
} from "@/lib/motion/anime";
import { useAnimeInView } from "@/hooks/useAnimeInView";

type AnimatedCounterProps = {
  value: number;
  suffix?: string;
  decimals?: number;
  className?: string;
};

export function AnimatedCounter({
  value,
  suffix = "",
  decimals = 0,
  className = "",
}: AnimatedCounterProps) {
  const { ref, inView } = useAnimeInView<HTMLSpanElement>({ rootMargin: "-40px" });
  const animRef = useRef<AnimInstance | null>(null);

  useEffect(() => {
    if (!inView || !ref.current) return;

    const el = ref.current;

    const render = (current: number) => {
      const formatted = decimals > 0 ? current.toFixed(decimals) : current.toString();
      el.textContent = `${formatted}${suffix}`;
    };

    if (prefersReducedMotion()) {
      render(value);
      return;
    }

    render(0);
    animRef.current = animateCounter(render, value, { decimals, duration: 1400 });

    return () => revertAnim(animRef.current);
  }, [inView, value, suffix, decimals]);

  return <span ref={ref} className={className} aria-live="polite" />;
}

export function AnimatedMetric({
  label,
  display,
  numericValue,
  suffix = "",
  decimals = 0,
}: {
  label: string;
  display: string;
  numericValue?: number;
  suffix?: string;
  decimals?: number;
}) {
  const isNumeric = numericValue !== undefined && !Number.isNaN(numericValue);

  return (
    <div className="surface-card metric-card p-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-muted">{label}</p>
      <p className="mt-2 font-mono text-3xl font-bold text-navy">
        {isNumeric ? (
          <AnimatedCounter value={numericValue} suffix={suffix} decimals={decimals} />
        ) : (
          display
        )}
      </p>
    </div>
  );
}
