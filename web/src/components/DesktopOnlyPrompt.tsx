// UQ11 (D) — Atelier locks itself to desktop creation tooling. <1024px viewports
// see this prompt instead of the app. Rendered outside Router / Query context,
// so we read locale directly from navigator rather than via useI18n.
//
// R4 #8 illustration is currently a typographic placeholder; the AI-generated
// "desktop-only.webp" will replace the monogram block once illustrations land.

export function DesktopOnlyPrompt() {
  const isChinese =
    typeof navigator !== "undefined" && /^zh\b/i.test(navigator.language ?? "")

  return (
    <div className="flex min-h-screen items-center justify-center bg-atelier-cream p-8 font-body text-atelier-ink">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-10 flex h-32 w-32 items-center justify-center border border-atelier-smoke/40 bg-atelier-paper">
          <span className="font-display text-7xl italic leading-none text-atelier-ink">
            A
          </span>
        </div>

        <h1 className="mb-4 font-display text-3xl italic text-atelier-ink">
          Atelier blooms on desktop
        </h1>
        <p className="mb-6 text-sm leading-relaxed text-atelier-sepia">
          {isChinese
            ? "请在桌面浏览器中访问 Atelier，获得完整的创作体验。"
            : "Open Atelier in a desktop browser for the full studio experience."}
        </p>
        <p className="font-mono text-xs uppercase tracking-widest text-atelier-smoke">
          viewport ≥ 1024px
        </p>
      </div>
    </div>
  )
}
