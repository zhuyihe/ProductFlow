import { motion } from "framer-motion"

import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion"
import { motionTokens } from "../lib/motion-tokens"

interface MiniHeroProps {
  /** 大字标题（Cormorant italic text-5xl 大写）。建议传 'SETTINGS' / 'PRODUCTS' / 'GALLERY' 等单词。 */
  title: string
  /** 顶部 meta 行（mono uppercase tracking-widest），如 'ATELIER · 2026' / 'Recent works · 2026'。可选。 */
  meta?: string
  /** 装饰符号（默认 ❦）。可传 ※ § ★ ❀ 等。设为空字符串以隐藏。 */
  ornament?: string
  /** 自定义容器 className 追加。 */
  className?: string
}

/**
 * Mini Hero — Atelier 工艺风的轻量页面头部。
 *
 * 设计目标：3 痛点页（Settings / ProductList / Gallery）复用，建立视觉一致性。
 * 高度 25vh（min 200px 兜底），跟 Phase 6 Cover Hero 60-80vh 形成节奏差异。
 *
 * 视觉构成：mono meta strip → 大字标题 → hairline vermilion → ornament。
 */
export function MiniHero({ title, meta, ornament = "❦", className = "" }: MiniHeroProps) {
  const reduced = usePrefersReducedMotion()

  return (
    <motion.section
      initial={reduced ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: motionTokens.duration.base,
        ease: motionTokens.ease.out,
      }}
      className={`relative flex min-h-[200px] flex-col items-center justify-center border-b border-atelier-smoke/30 bg-atelier-paper px-6 py-12 dark:border-atelier-cream/15 dark:bg-[#1F1812] ${className}`}
      style={{ minHeight: "max(25vh, 200px)" }}
    >
      {meta ? (
        <p className="mb-5 font-mono text-[10px] uppercase tracking-[0.25em] text-atelier-sepia dark:text-atelier-cream/60">
          {meta}
        </p>
      ) : null}

      <h1 className="font-display text-5xl italic leading-none text-atelier-ink dark:text-atelier-cream">
        {title}
      </h1>

      <div
        aria-hidden="true"
        className="mt-5 h-px w-16 bg-atelier-vermilion/60"
      />

      {ornament ? (
        <span
          aria-hidden="true"
          className="mt-5 font-display text-2xl text-atelier-vermilion/50 dark:text-atelier-cream/40"
        >
          {ornament}
        </span>
      ) : null}
    </motion.section>
  )
}
