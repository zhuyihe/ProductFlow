import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import { AnimatedHeading } from "../components/motion/AnimatedHeading";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";
import { motionTokens } from "../lib/motion-tokens";
import { useI18n } from "../lib/preferences";

interface NotFoundPageProps {
  authenticated: boolean;
}

export function NotFoundPage({ authenticated }: NotFoundPageProps) {
  const { t } = useI18n();
  const reduced = usePrefersReducedMotion();
  const target = authenticated ? "/products" : "/login";
  const actionLabel = authenticated
    ? t("notFound.actionAuthenticated")
    : t("notFound.actionUnauthenticated");

  return (
    <div className="flex min-h-screen items-center justify-center bg-atelier-cream px-6 py-24 dark:bg-[#1A1410]">
      <div className="relative flex max-w-2xl flex-col items-center text-center">
        {/* ornament 装饰 */}
        <span
          aria-hidden="true"
          className="absolute -left-16 top-8 hidden font-display text-3xl italic text-atelier-smoke/40 dark:text-atelier-cream/15 lg:inline"
        >
          ❦
        </span>
        <span
          aria-hidden="true"
          className="absolute -right-12 bottom-16 hidden font-display text-3xl italic text-atelier-smoke/40 dark:text-atelier-cream/15 lg:inline"
        >
          ※
        </span>

        {/* eyebrow */}
        <motion.p
          initial={reduced ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: motionTokens.duration.base, ease: motionTokens.ease.out }}
          className="font-mono text-[10px] uppercase tracking-[0.3em] text-atelier-smoke dark:text-atelier-cream/40"
        >
          404 · page not found
        </motion.p>

        {/* hero 数字 */}
        <motion.div
          initial={reduced ? false : { opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            delay: reduced ? 0 : 0.2,
            duration: motionTokens.duration.slow,
            ease: motionTokens.ease.out,
          }}
          className="mt-6 font-display text-[10rem] italic leading-none text-atelier-ink dark:text-atelier-cream"
        >
          404
        </motion.div>

        {/* title */}
        <AnimatedHeading
          text={t("notFound.title")}
          as="h1"
          className="mt-6 font-display text-3xl italic text-atelier-ink dark:text-atelier-cream"
        />

        {/* subtitle */}
        <motion.p
          initial={reduced ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            delay: reduced ? 0 : 0.6,
            duration: motionTokens.duration.base,
            ease: motionTokens.ease.out,
          }}
          className="mt-4 max-w-md text-sm leading-relaxed text-atelier-sepia dark:text-atelier-cream/60"
        >
          {t("notFound.subtitle")}
        </motion.p>

        {/* action */}
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            delay: reduced ? 0 : 0.8,
            duration: motionTokens.duration.base,
            ease: motionTokens.ease.out,
          }}
          className="mt-10"
        >
          <Link
            to={target}
            className="group inline-flex items-center gap-2 border border-atelier-ink bg-atelier-ink px-6 py-3 font-display text-base italic text-atelier-cream transition-colors hover:border-atelier-vermilion hover:bg-atelier-vermilion dark:border-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink dark:hover:border-atelier-vermilion dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
          >
            <span>{actionLabel}</span>
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>

        {/* footer */}
        <p className="mt-16 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
          atelier · 2026
        </p>
      </div>
    </div>
  );
}
