"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { SITE } from "@/lib/site";

const LINKS = [
  ["#platform", "Platform"],
  ["#metrics", "Metrics"],
  ["#demo", "Demo"],
  ["#walkthrough", "Video"],
  ["#docs", "Docs"],
] as const;

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.48, ease: [0.16, 1, 0.3, 1] }}
      className={`fixed left-0 right-0 top-0 z-[100] flex h-[60px] items-center justify-between px-10 transition-[background,border-color,box-shadow] duration-[220ms] ${
        scrolled ? "border-b border-[var(--border-subtle)] bg-[rgba(6,13,20,0.95)] shadow-[0_4px_24px_rgba(0,0,0,0.25)]" : "border-b border-transparent bg-transparent"
      }`}
    >
      <Link href="/" className="flex items-center gap-2.5 no-underline">
        <Image src="/logo.png" alt="Sentinel-RAG" width={32} height={32} className="rounded-md" />
        <span className="text-[15px] font-semibold text-[var(--text-primary)]">Sentinel-RAG</span>
      </Link>

      <div className="hidden items-center gap-8 md:flex">
        {LINKS.map(([href, label]) => (
          <a key={href} href={href} className="nav-link no-underline">
            {label}
          </a>
        ))}
        <Link href="/insights" className="nav-link no-underline">
          Insights
        </Link>
        <Link href="/workspace">
          <motion.span
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            className="inline-block cursor-pointer rounded-md bg-[var(--teal)] px-4 py-2 text-sm font-semibold text-[var(--bg-base)] no-underline"
          >
            Live demo
          </motion.span>
        </Link>
      </div>
    </motion.nav>
  );
}
