import { motion, type HTMLMotionProps } from "framer-motion"
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion"
import { motionTokens } from "../../lib/motion-tokens"

// R3.6 — LoginPage 标题逐字浮现.
// Splits a string into per-character motion spans with staggered entrance.
// Honors prefers-reduced-motion by rendering plain text and skipping the
// stagger (no decoration, no motion, no per-char wrapping).

type HeadingTag = "h1" | "h2" | "h3"

interface AnimatedHeadingProps {
  text: string
  as?: HeadingTag
  className?: string
}

export function AnimatedHeading({
  text,
  as = "h1",
  className,
}: AnimatedHeadingProps) {
  const reduced = usePrefersReducedMotion()

  if (reduced) {
    return renderPlain(as, text, className)
  }

  const chars = Array.from(text)
  const tagProps: HTMLMotionProps<"h1"> = {
    className,
    initial: "hidden",
    animate: "visible",
    variants: {
      visible: {
        transition: { staggerChildren: motionTokens.stagger.tight },
      },
    },
    "aria-label": text,
  }

  const Inner = (
    <>
      {chars.map((char, i) => (
        <motion.span
          key={i}
          aria-hidden="true"
          style={{
            display: "inline-block",
            whiteSpace: char === " " ? "pre" : "normal",
          }}
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 },
          }}
          transition={{
            duration: motionTokens.duration.base,
            ease: motionTokens.ease.out,
          }}
        >
          {char === " " ? " " : char}
        </motion.span>
      ))}
    </>
  )

  if (as === "h2") return <motion.h2 {...tagProps}>{Inner}</motion.h2>
  if (as === "h3") return <motion.h3 {...tagProps}>{Inner}</motion.h3>
  return <motion.h1 {...tagProps}>{Inner}</motion.h1>
}

function renderPlain(as: HeadingTag, text: string, className?: string) {
  if (as === "h2") return <h2 className={className}>{text}</h2>
  if (as === "h3") return <h3 className={className}>{text}</h3>
  return <h1 className={className}>{text}</h1>
}
