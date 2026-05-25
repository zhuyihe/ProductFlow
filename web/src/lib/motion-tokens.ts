// Motion tokens for the Atelier design system (UQ8 中度动效).
// All animations MUST source duration / easing / stagger from this module —
// hard-coded values create drift between components and break the "中度" budget.

export const motionTokens = {
  duration: {
    instant: 0.1,
    quick: 0.2,
    base: 0.4,
    slow: 0.8,
  },
  ease: {
    // ease-out-quart — the workhorse for entrances and hover transitions.
    out: [0.16, 1, 0.3, 1] as [number, number, number, number],
    // Symmetric in-out for routed transitions.
    inOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
  },
  stagger: {
    tight: 0.06,
    base: 0.1,
    loose: 0.2,
  },
} as const

export type MotionTokens = typeof motionTokens
