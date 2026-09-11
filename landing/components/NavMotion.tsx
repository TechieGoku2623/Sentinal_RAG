"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { animate, type JSAnimation } from "animejs";
import { SITE } from "@/lib/site";
import { MOTION, prefersReducedMotion, revertAnim } from "@/lib/motion/anime";

const LINKS = [
  ["#platform", "Platform"],
  ["#metrics", "Metrics"],
  ["#pricing", "Pricing"],
  ["#faq", "FAQ"],
  ["#docs", "Docs"],
] as const;

export function NavMotion() {
  const headerRef = useRef<HTMLElement>(null);
  const animRef = useRef<JSAnimation | null>(null);

  useEffect(() => {
    const header = headerRef.current;
    if (!header) return;

    const onScroll = () => {
      header.classList.toggle("nav-bar--scrolled", window.scrollY > 6);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    if (!prefersReducedMotion()) {
      animRef.current = animate(header, {
        opacity: { from: 0, to: 1 },
        y: { from: -10, to: 0 },
        duration: 480,
        ease: MOTION.ease.out,
      });
    }

    return () => {
      window.removeEventListener("scroll", onScroll);
      revertAnim(animRef.current);
    };
  }, []);

  return (
    <header ref={headerRef} className="nav-bar sticky top-0 z-50">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <a href="#" className="flex items-center gap-3 transition-opacity hover:opacity-90">
          <Image src="/logo.png" alt="Sentinel-RAG" width={32} height={32} className="rounded-md" />
          <div>
            <p className="font-display text-sm font-semibold text-[var(--color-ink)]">Sentinel-RAG</p>
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--color-ink-2)]">
              Protocol Guardian
            </p>
          </div>
        </a>

        <nav className="hidden items-center gap-6 md:flex">
          {LINKS.map(([href, label]) => (
            <a key={href} href={href} className="nav-link">
              {label}
            </a>
          ))}
          <a href={SITE.workspaceUrl} className="btn-primary cursor-pointer text-xs">
            Open app
          </a>
        </nav>
      </div>
    </header>
  );
}
