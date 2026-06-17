"use client";



import { motion, useScroll, useTransform } from "framer-motion";

import Image from "next/image";

import { SITE } from "@/lib/site";



export function NavMotion() {

  const { scrollY } = useScroll();

  const bg = useTransform(scrollY, [0, 80], ["rgba(10, 22, 40, 0.94)", "rgba(10, 22, 40, 0.99)"]);

  const shadow = useTransform(

    scrollY,

    [0, 80],

    ["0 0 0 rgba(0,0,0,0)", "0 4px 24px rgba(0,0,0,0.2)"],

  );



  return (

    <motion.header

      style={{ backgroundColor: bg, boxShadow: shadow }}

      className="sticky top-0 z-50 border-b border-white/8 backdrop-blur-md"

    >

      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">

        <motion.a

          href="#"

          className="flex items-center gap-3"

          whileHover={{ opacity: 0.92 }}

          transition={{ duration: 0.15 }}

        >

          <Image

            src="/logo.png"

            alt="Sentinel-RAG"

            width={36}

            height={36}

            className="rounded-[10px]"

          />

          <div>

            <p className="text-sm font-semibold tracking-tight text-white">Sentinel-RAG</p>

            <p className="text-[11px] font-medium text-slate-400">Clinical Protocol Guardian</p>

          </div>

        </motion.a>

        <nav className="hidden items-center gap-7 text-sm text-slate-300 md:flex">

          {[

            ["#demo", "Demo"],

            ["#pricing", "Pricing"],

            ["#platform", "Platform"],

            ["#insights", "Insights"],

            ["#metrics", "Metrics"],

            ["#docs", "Docs"],

          ].map(([href, label]) => (

            <a

              key={href}

              href={href}

              className="font-medium transition-colors hover:text-white"

            >

              {label}

            </a>

          ))}

          <a

            href={SITE.workspaceUrl}

            className="rounded-lg bg-brand px-3.5 py-1.5 text-xs font-semibold text-white transition-colors hover:opacity-90"

          >

            Open app

          </a>

          <a

            href="https://github.com/devasai/sentinel-rag"

            className="rounded-lg border border-white/15 px-3.5 py-1.5 text-xs font-semibold text-white transition-colors hover:border-white/30 hover:bg-white/5"

            target="_blank"

            rel="noopener noreferrer"

          >

            GitHub

          </a>

        </nav>

      </div>

    </motion.header>

  );

}

