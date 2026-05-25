import { motion, useScroll, useTransform } from "framer-motion"
import { useRef, type ImgHTMLAttributes } from "react"
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion"

// R3.4 — GalleryPage scroll-linked subtle scale.
// As an image scrolls through the viewport, scale it from 0.95 → 1 → 1.02.
// Effect is purely decorative; reduced-motion users get a static image with
// identical layout (no scale at all).

interface ScrollScaleImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  src: string
  alt: string
  wrapperClassName?: string
}

export function ScrollScaleImage({
  src,
  alt,
  wrapperClassName,
  className,
  loading = "lazy",
  ...rest
}: ScrollScaleImageProps) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.95, 1, 1.02])

  if (reduced) {
    return (
      <div ref={ref} className={wrapperClassName}>
        <img src={src} alt={alt} loading={loading} className={className} {...rest} />
      </div>
    )
  }

  return (
    <motion.div ref={ref} style={{ scale }} className={wrapperClassName}>
      <img src={src} alt={alt} loading={loading} className={className} {...rest} />
    </motion.div>
  )
}
