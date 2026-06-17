"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "framer-motion";

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
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setDisplay(value);
      return;
    }
    const duration = 1400;
    const start = performance.now();
    let frame: number;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      const current = value * eased;
      setDisplay(decimals > 0 ? parseFloat(current.toFixed(decimals)) : Math.round(current));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, value, decimals, reduce]);

  const formatted = decimals > 0 ? display.toFixed(decimals) : display.toString();

  return (
    <span ref={ref} className={className}>
      {formatted}
      {suffix}
    </span>
  );
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
    <div className="pro-card p-6">
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
