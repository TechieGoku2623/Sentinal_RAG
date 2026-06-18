"use client";

import { useEffect, useRef } from "react";
import { animate, stagger, type JSAnimation } from "animejs";
import type { ReactNode } from "react";
import { MOTION, prefersReducedMotion, revertAnim } from "@/lib/motion/anime";

type FadeInProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
  duration?: number;
};

function directionOffset(direction: FadeInProps["direction"]) {
  const offset = 28;
  switch (direction) {
    case "down":
      return { y: -offset, x: 0 };
    case "left":
      return { y: 0, x: offset };
    case "right":
      return { y: 0, x: -offset };
    case "none":
      return { y: 0, x: 0 };
    default:
      return { y: offset, x: 0 };
  }
}

export function FadeIn({
  children,
  className = "",
  delay = 0,
  direction = "up",
  duration = 550,
}: FadeInProps) {
  const ref = useRef<HTMLDivElement>(null);
  const animRef = useRef<JSAnimation | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (prefersReducedMotion()) {
      el.style.opacity = "1";
      el.style.transform = "none";
      return;
    }

    const { y, x } = directionOffset(direction);

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();

        const params: Record<string, unknown> = {
          opacity: { from: 0, to: 1 },
          duration,
          delay: delay * 1000,
          ease: MOTION.ease.out,
        };
        if (y) params.y = { from: y, to: 0 };
        if (x) params.x = { from: x, to: 0 };

        animRef.current = animate(el, params);
      },
      { threshold: 0.1, rootMargin: "-60px" },
    );

    observer.observe(el);
    return () => {
      observer.disconnect();
      revertAnim(animRef.current);
    };
  }, [delay, direction, duration]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ opacity: prefersReducedMotion() ? 1 : 0 }}
    >
      {children}
    </div>
  );
}

export function StaggerContainer({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const animRef = useRef<JSAnimation | null>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const items = container.querySelectorAll<HTMLElement>("[data-stagger-item]");
    if (!items.length) return;

    if (prefersReducedMotion()) {
      items.forEach((item) => {
        item.style.opacity = "1";
        item.style.transform = "none";
      });
      return;
    }

    items.forEach((item) => {
      item.style.opacity = "0";
    });

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();

        animRef.current = animate(items, {
          opacity: { from: 0, to: 1 },
          y: { from: 24, to: 0 },
          delay: stagger(100, { start: 50 }),
          duration: 500,
          ease: MOTION.ease.out,
        });
      },
      { threshold: 0.08, rootMargin: "-40px" },
    );

    observer.observe(container);
    return () => {
      observer.disconnect();
      revertAnim(animRef.current);
    };
  }, []);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

export function StaggerItem({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div data-stagger-item className={className} style={{ opacity: 0 }}>
      {children}
    </div>
  );
}
