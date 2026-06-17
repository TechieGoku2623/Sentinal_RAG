"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import { SITE } from "@/lib/site";
import { FadeIn } from "./FadeIn";

export function LoomDemo() {
  const reduce = useReducedMotion();
  const hasLoom = Boolean(SITE.loomEmbedUrl);

  return (
    <section id="demo" className="bg-navy px-6 py-20 text-white">
      <div className="mx-auto max-w-6xl">
        <FadeIn>
          <p className="section-label text-brand-light">Product demo</p>
          <h2 className="mt-2 text-3xl font-bold md:text-4xl">
            Watch Sentinel-RAG in action
          </h2>
          <p className="mt-4 max-w-2xl text-slate-300">
            {hasLoom
              ? "2-minute walkthrough: protocol validation, confidence scoring, flagging, and clinical recollection — built for recruiters and hiring managers evaluating LangGraph + clinical AI work."
              : "Embed your Loom recording here. Until then, use the animated preview below or follow the recording script in docs/LOOM_DEMO.md."}
          </p>
        </FadeIn>

        <motion.div
          className="mt-10 overflow-hidden rounded-2xl border border-white/10 shadow-2xl"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        >
          {hasLoom ? (
            <div className="relative aspect-video w-full bg-black">
              <iframe
                src={SITE.loomEmbedUrl}
                title="Sentinel-RAG Loom demo"
                allowFullScreen
                className="absolute inset-0 h-full w-full"
              />
            </div>
          ) : (
            <div className="relative">
              <Image
                src="/demo.gif"
                alt="Sentinel-RAG animated demo preview"
                width={1200}
                height={680}
                unoptimized
                className="h-auto w-full opacity-90"
              />
              <div className="absolute inset-0 flex items-center justify-center bg-navy/60 backdrop-blur-[2px]">
                <div className="mx-4 max-w-lg rounded-xl border border-brand/30 bg-navy/95 p-8 text-center">
                  <p className="text-lg font-semibold text-brand-light">Loom demo slot</p>
                  <p className="mt-3 text-sm text-slate-300">
                    Record with{" "}
                    <a
                      href="https://www.loom.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-light underline"
                    >
                      Loom
                    </a>
                    , then set{" "}
                    <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
                      NEXT_PUBLIC_LOOM_EMBED_URL
                    </code>{" "}
                    in <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">landing/.env.local</code>
                  </p>
                  <a
                    href="../docs/LOOM_DEMO.md"
                    className="mt-6 inline-block rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white"
                  >
                    Open recording script →
                  </a>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {SITE.loomShareUrl ? (
          <p className="mt-4 text-center text-sm text-slate-400">
            Share link:{" "}
            <a href={SITE.loomShareUrl} className="text-brand-light hover:underline" target="_blank" rel="noopener noreferrer">
              {SITE.loomShareUrl}
            </a>
          </p>
        ) : null}
      </div>
    </section>
  );
}
