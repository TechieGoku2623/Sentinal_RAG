"use client";

import { useReducedMotion as useFramerReducedMotion } from "framer-motion";

export function useReducedMotion(): boolean {
  return useFramerReducedMotion() ?? false;
}

export function useSafeMotion() {
  const reduced = useFramerReducedMotion();
  return {
    transition: reduced ? { duration: 0 } : undefined,
    skip: reduced,
  };
}
