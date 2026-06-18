import {
  animate,
  createTimeline,
  stagger,
  type JSAnimation,
  type Timeline,
} from "animejs";

export type AnimInstance = JSAnimation | Timeline;

export const MOTION = {
  duration: { fast: 400, base: 550, slow: 900, counter: 1400 },
  ease: {
    out: "out(3)",
    inOut: "inOut(3)",
    spring: "outElastic(1, 0.55)",
  },
} as const;

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function revertAnim(anim: AnimInstance | null | undefined): void {
  anim?.revert?.();
}

type FadeOptions = {
  delay?: number;
  duration?: number;
  y?: number;
  x?: number;
  staggerMs?: number;
};

export function fadeUp(
  targets: Element | Element[] | NodeListOf<Element>,
  opts: FadeOptions = {},
): AnimInstance | null {
  if (prefersReducedMotion()) return null;

  const els =
    targets instanceof NodeList
      ? [...targets]
      : Array.isArray(targets)
        ? targets
        : [targets];

  const params: Record<string, unknown> = {
    opacity: { from: 0, to: 1 },
    duration: opts.duration ?? MOTION.duration.base,
    ease: MOTION.ease.out,
  };

  if (opts.y !== undefined && opts.y !== 0) {
    params.y = { from: opts.y, to: 0 };
  }
  if (opts.x !== undefined && opts.x !== 0) {
    params.x = { from: opts.x, to: 0 };
  }
  if (opts.staggerMs) {
    params.delay = stagger(opts.staggerMs, { start: opts.delay ?? 0 });
  } else if (opts.delay) {
    params.delay = opts.delay;
  }

  return animate(els, params);
}

export function animateCounter(
  onUpdate: (value: number) => void,
  to: number,
  opts?: {
    from?: number;
    duration?: number;
    decimals?: number;
    delay?: number;
    onComplete?: () => void;
  },
): AnimInstance | null {
  const from = opts?.from ?? 0;

  if (prefersReducedMotion()) {
    onUpdate(to);
    return null;
  }

  const state = { value: from };
  return animate(state, {
    value: to,
    duration: opts?.duration ?? MOTION.duration.counter,
    delay: opts?.delay ?? 0,
    ease: MOTION.ease.out,
    onUpdate: () => {
      const raw = state.value;
      const value =
        opts?.decimals && opts.decimals > 0
          ? parseFloat(raw.toFixed(opts.decimals))
          : Math.round(raw);
      onUpdate(value);
    },
    onComplete: opts?.onComplete,
  });
}

export function heroEntrance(root: HTMLElement): AnimInstance | null {
  if (prefersReducedMotion()) return null;

  const label = root.querySelector("[data-hero-label]");
  const stat = root.querySelector("[data-hero-stat]");
  const title = root.querySelector("[data-hero-title]");
  const body = root.querySelector("[data-hero-body]");
  const actions = root.querySelectorAll("[data-hero-action]");
  const panel = root.querySelector("[data-hero-panel]");

  const tl = createTimeline({
    defaults: { ease: MOTION.ease.out, duration: MOTION.duration.base },
  });

  if (label) {
    tl.add(label, { opacity: { from: 0, to: 1 }, y: { from: 14, to: 0 }, duration: 480 }, 0);
  }
  if (stat) {
    tl.add(
      stat,
      { opacity: { from: 0, to: 1 }, scale: { from: 0.94, to: 1 }, duration: 720, ease: MOTION.ease.spring },
      80,
    );
  }
  if (title) {
    tl.add(title, { opacity: { from: 0, to: 1 }, y: { from: 18, to: 0 }, duration: 560 }, 120);
  }
  if (body) {
    tl.add(body, { opacity: { from: 0, to: 1 }, y: { from: 16, to: 0 }, duration: 520 }, 200);
  }
  if (actions.length) {
    tl.add(
      actions,
      {
        opacity: { from: 0, to: 1 },
        y: { from: 12, to: 0 },
        delay: stagger(70, { start: 260 }),
        duration: 440,
      },
      0,
    );
  }
  if (panel) {
    tl.add(
      panel,
      { opacity: { from: 0, to: 1 }, x: { from: 28, to: 0 }, duration: 680, ease: MOTION.ease.inOut },
      140,
    );
  }

  return tl;
}

export function pipelineEntrance(root: HTMLElement): AnimInstance | null {
  if (prefersReducedMotion()) return null;

  const line = root.querySelector("[data-pipeline-line]");
  const steps = root.querySelectorAll("[data-pipeline-step]");

  const tl = createTimeline({ defaults: { ease: MOTION.ease.out } });

  if (line) {
    tl.add(
      line,
      {
        scaleX: { from: 0, to: 1 },
        duration: MOTION.duration.slow,
        ease: MOTION.ease.inOut,
      },
      0,
    );
  }

  if (steps.length) {
    tl.add(
      steps,
      {
        opacity: { from: 0, to: 1 },
        y: { from: 22, to: 0 },
        delay: stagger(85, { start: 120 }),
        duration: 460,
      },
      0,
    );
  }

  return tl;
}

export { animate, createTimeline, stagger };
