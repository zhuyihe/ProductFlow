import { motion, type HTMLMotionProps } from "framer-motion"
import { Children, type ReactNode } from "react"
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion"
import { motionTokens } from "../../lib/motion-tokens"

// R3.7 — Generic stagger entrance for grids and lists.
// Wraps each direct child in a motion.div with fade+rise variants, then
// staggers them by `stagger` seconds. The container element defaults to <div>
// but can be overridden via `as` (e.g. <ul>, <section>).

interface StaggerGridProps extends Omit<HTMLMotionProps<"div">, "children"> {
  children: ReactNode
  stagger?: number
  /** Per-item rise distance in px. */
  rise?: number
}

export function StaggerGrid({
  children,
  stagger = motionTokens.stagger.base,
  rise = 10,
  className,
  ...rest
}: StaggerGridProps) {
  const reduced = usePrefersReducedMotion()
  const items = Children.toArray(children)

  if (reduced) {
    return (
      <div className={className}>
        {items.map((child, i) => (
          <div key={i}>{child}</div>
        ))}
      </div>
    )
  }

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        visible: { transition: { staggerChildren: stagger } },
      }}
      {...rest}
    >
      {items.map((child, i) => (
        <motion.div
          key={i}
          variants={{
            hidden: { opacity: 0, y: rise },
            visible: { opacity: 1, y: 0 },
          }}
          transition={{
            duration: motionTokens.duration.base,
            ease: motionTokens.ease.out,
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}
