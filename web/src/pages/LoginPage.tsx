import { useEffect } from "react"
import { ArrowRight } from "lucide-react"
import { motion } from "framer-motion"
import { useNavigate } from "react-router-dom"

import { AnimatedHeading } from "../components/motion/AnimatedHeading"
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion"
import { motionTokens } from "../lib/motion-tokens"
import { useI18n } from "../lib/preferences"

interface LoginPageProps {
  authenticated: boolean
  ssoStartUrl: string | null
}

export function LoginPage({ authenticated, ssoStartUrl }: LoginPageProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const reduced = usePrefersReducedMotion()

  useEffect(() => {
    if (authenticated) {
      navigate("/products", { replace: true })
    }
  }, [authenticated, navigate])

  const handleAuthorize = () => {
    if (!ssoStartUrl) return
    window.location.assign(ssoStartUrl)
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[2fr_3fr]">
      {/* 左半屏 — paper 背景 + wordmark + tagline + form */}
      <section className="relative flex flex-col justify-between bg-atelier-paper px-12 py-16 dark:bg-[#1F1812]">
        {/* Wordmark */}
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center border border-atelier-smoke/40 bg-atelier-cream dark:border-atelier-cream/20 dark:bg-[#2A2017]">
            <span className="font-display text-3xl italic leading-none text-atelier-ink dark:text-atelier-cream">
              A
            </span>
          </div>
          <span className="font-display text-3xl italic text-atelier-ink dark:text-atelier-cream">
            Atelier
          </span>
        </div>

        {/* Tagline + form */}
        <div className="my-auto max-w-md">
          <AnimatedHeading
            text="Where craft meets code."
            as="h1"
            className="mb-4 font-display text-5xl italic leading-tight text-atelier-ink dark:text-atelier-cream"
          />
          <p className="mb-10 text-sm leading-relaxed text-atelier-sepia dark:text-atelier-cream/60">
            {t("login.description")}
          </p>

          <motion.div
            initial={reduced ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              delay: reduced ? 0 : 1.0,
              duration: motionTokens.duration.base,
              ease: motionTokens.ease.out,
            }}
          >
            <div className="mb-6 border-y border-atelier-smoke/30 py-5 dark:border-atelier-cream/15">
              <p className="font-mono text-[10px] uppercase tracking-widest text-atelier-sepia dark:text-atelier-cream/60">
                {t("auth.login.scope.title")}
              </p>
              <ul className="mt-3 space-y-1 text-xs leading-5 text-atelier-sepia dark:text-atelier-cream/50">
                <li className="flex gap-2">
                  <span aria-hidden="true">·</span>
                  <span>{t("auth.login.scope.accountInfo")}</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              onClick={handleAuthorize}
              disabled={!ssoStartUrl}
              className="group flex w-full items-center justify-between border border-atelier-ink bg-atelier-ink px-6 py-3.5 font-display text-base italic text-atelier-cream transition-colors hover:border-atelier-vermilion hover:bg-atelier-vermilion disabled:cursor-not-allowed disabled:opacity-50 dark:border-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink dark:hover:border-atelier-vermilion dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
            >
              <span>{t("login.submit")}</span>
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </button>

            {!ssoStartUrl ? (
              <p className="mt-3 text-xs leading-5 text-atelier-vermilion-dark dark:text-atelier-vermilion">
                {t("login.ssoUnavailable")}
              </p>
            ) : null}

            <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-widest text-atelier-smoke">
              {t("auth.login.sessionTtl")}
            </p>
          </motion.div>
        </div>

        {/* Footer */}
        <p className="font-mono text-[10px] uppercase tracking-widest text-atelier-smoke">
          atelier · 2026
        </p>
      </section>

      {/* 右半屏 — kraft 背景 + Hero R4 #2 占位 */}
      <motion.section
        initial={reduced ? false : { opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{
          delay: reduced ? 0 : 0.2,
          duration: motionTokens.duration.slow,
          ease: motionTokens.ease.out,
        }}
        className="relative hidden items-center justify-center overflow-hidden bg-atelier-kraft dark:bg-[#241B14] lg:flex"
      >
        {/* R4 #2 Hero illustration — French atelier scene */}
        <picture className="relative block">
          <source
            type="image/avif"
            srcSet="/illustrations/login-hero.avif 1x, /illustrations/login-hero@2x.avif 2x"
          />
          <source
            type="image/webp"
            srcSet="/illustrations/login-hero.webp 1x, /illustrations/login-hero@2x.webp 2x"
          />
          <img
            src="/illustrations/login-hero.webp"
            alt=""
            aria-hidden="true"
            fetchPriority="high"
            decoding="async"
            width={1024}
            height={1280}
            className="block max-h-[78vh] w-auto select-none"
          />
        </picture>

        {/* 装饰 ornament 散点 (UQ10 A wordmark+ornament 简化) */}
        <span
          aria-hidden="true"
          className="absolute left-12 top-20 font-display text-2xl text-atelier-ink/20 dark:text-atelier-cream/20"
        >
          ❦
        </span>
        <span
          aria-hidden="true"
          className="absolute bottom-24 right-16 font-display text-2xl text-atelier-ink/20 dark:text-atelier-cream/20"
        >
          ※
        </span>
      </motion.section>
    </div>
  )
}
