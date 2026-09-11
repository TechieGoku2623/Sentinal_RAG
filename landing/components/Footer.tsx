"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { SITE } from "@/lib/site";

export function Footer() {
  return (
    <footer className="border-t border-[var(--border-subtle)] px-10 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-[var(--text-secondary)] md:flex-row"
      >
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="" width={28} height={28} className="rounded-[6px]" />
          <span>Sentinel-RAG · Research prototype — not a medical device</span>
        </div>
        <p>
          Built by{" "}
          <a
            href={SITE.linkedinUrl}
            className="text-[var(--teal)] transition-colors hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Devasai Pranatheswar
          </a>
        </p>
      </motion.div>
    </footer>
  );
}
