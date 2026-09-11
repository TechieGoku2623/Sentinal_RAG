"use client";

import { useEffect } from "react";
import {
  motion,
  useMotionValue,
  useTransform,
  animate,
  useReducedMotion,
} from "framer-motion";

interface Props {
  value: number;
  size?: number;
  strokeWidth?: number;
  animate?: boolean;
}

const arcColor = (v: number) =>
  v >= 85 ? "#0EC788" : v >= 75 ? "#F0A500" : "#E84040";

function AnimatedNumber({ value }: { value: number }) {
  const reduce = useReducedMotion();
  const count = useMotionValue(0);
  const rounded = useTransform(count, Math.round);

  useEffect(() => {
    if (reduce) {
      count.set(value);
      return;
    }
    const controls = animate(count, value, {
      duration: 1.4,
      ease: [0.16, 1, 0.3, 1],
    });
    return controls.stop;
  }, [value, reduce, count]);

  return <motion.span>{rounded}</motion.span>;
}

export function ConfidenceArc({
  value,
  size = 88,
  strokeWidth = 6,
  animate: shouldAnimate = true,
}: Props) {
  const reduce = useReducedMotion();
  const r = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const arcLength = circumference * 0.75;

  const count = useMotionValue(0);
  const dashoffset = useTransform(count, [0, 100], [arcLength, 0]);

  useEffect(() => {
    if (!shouldAnimate || reduce) {
      count.set(value);
      return;
    }
    const controls = animate(count, value, {
      duration: 1.4,
      ease: [0.16, 1, 0.3, 1],
    });
    return controls.stop;
  }, [value, shouldAnimate, reduce, count]);

  const color = arcColor(value);

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-225deg)" }}>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
        />
        <motion.circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={reduce ? arcLength * (1 - value / 100) : dashoffset}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 1,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: size < 70 ? 13 : 17,
            fontWeight: 500,
            color,
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          <AnimatedNumber value={value} />%
        </span>
        <span
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 9,
            color: "var(--text-muted)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          conf
        </span>
      </div>
    </div>
  );
}
