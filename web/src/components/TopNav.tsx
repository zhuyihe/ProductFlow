import {
  BookOpen,
  GalleryHorizontalEnd,
  Languages,
  LayoutGrid,
  LogOut,
  MessagesSquare,
  Monitor,
  Moon,
  Settings,
  Sun,
  Wand2,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { LOCALES, type Locale, type TranslationKey } from "../lib/i18n";
import { usePreferences } from "../lib/preferences";
import { THEME_PREFERENCES, type ThemePreference } from "../lib/theme";
import type { SessionState } from "../lib/types";

interface TopNavProps {
  breadcrumbs?: string;
  onHome?: () => void;
  onLogout?: () => void;
  session?: SessionState | null;
}

const navItems = [
  {
    labelKey: "nav.products",
    to: "/products",
    icon: LayoutGrid,
    match: (pathname: string) => pathname.startsWith("/products") && !pathname.endsWith("/image-chat"),
  },
  {
    labelKey: "nav.imageChat",
    to: "/image-chat",
    icon: MessagesSquare,
    match: (pathname: string) => pathname.includes("image-chat"),
  },
  {
    labelKey: "nav.gallery",
    to: "/gallery",
    icon: GalleryHorizontalEnd,
    match: (pathname: string) => pathname.startsWith("/gallery"),
  },
  {
    labelKey: "nav.help",
    to: "/help",
    icon: BookOpen,
    match: (pathname: string) => pathname.startsWith("/help"),
  },
  {
    labelKey: "nav.settings",
    to: "/settings",
    icon: Settings,
    match: (pathname: string) => pathname.startsWith("/settings"),
  },
] as const;

const adminOnlyNavTargets = new Set(["/settings"]);

const themeIcons: Record<ThemePreference, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

const localeLabelKey: Record<Locale, TranslationKey> = {
  "zh-CN": "locale.zhCN",
  "en-US": "locale.enUS",
  "ja-JP": "locale.jaJP",
};

function navItemClassName(active: boolean) {
  return [
    "inline-flex h-10 w-10 shrink-0 items-center justify-center text-sm font-semibold transition-colors sm:w-auto sm:px-4 lg:px-5",
    active
      ? "bg-atelier-paper text-atelier-vermilion shadow-paper-sm ring-1 ring-atelier-vermilion/30 dark:bg-atelier-cream/10 dark:text-atelier-vermilion dark:ring-atelier-cream/15"
      : "text-atelier-smoke hover:bg-atelier-paper/70 hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream",
  ].join(" ");
}

export function TopNav({ breadcrumbs, onHome, onLogout, session }: TopNavProps) {
  const location = useLocation();
  const { locale, setLocale, t, themePreference, setThemePreference } = usePreferences();
  const CurrentThemeIcon = themeIcons[themePreference];
  const nextThemePreference =
    THEME_PREFERENCES[(THEME_PREFERENCES.indexOf(themePreference) + 1) % THEME_PREFERENCES.length];
  const nextLocale = LOCALES[(LOCALES.indexOf(locale) + 1) % LOCALES.length];
  const visibleNavItems =
    session?.principal_kind === "admin"
      ? navItems
      : navItems.filter((item) => !adminOnlyNavTargets.has(item.to));

  return (
    <>
      <nav className="z-50 flex flex-col gap-3 overflow-x-hidden border-b border-atelier-smoke/30 bg-atelier-paper/95 px-3 py-3 shadow-paper-sm backdrop-blur dark:border-atelier-cream/15 dark:bg-atelier-cream/5 sm:px-4 lg:grid lg:min-h-14 lg:grid-cols-[minmax(180px,1fr)_auto_minmax(180px,1fr)] lg:items-center lg:gap-4 lg:px-6">
        <div className="flex min-w-0 items-center justify-between gap-2 text-sm">
          <div className="flex min-w-0 max-w-[calc(100%-6.5rem)] items-center space-x-2 overflow-hidden">
            <button
              type="button"
              className="flex min-w-0 shrink-0 items-center text-base font-semibold text-atelier-ink transition-colors hover:text-atelier-vermilion dark:text-atelier-cream dark:hover:text-atelier-vermilion"
              onClick={onHome}
            >
              <span className="mr-2 inline-flex h-8 w-8 items-center justify-center bg-atelier-ink text-atelier-cream shadow-paper-md">
                <Wand2 size={17} />
              </span>
              <span className="hidden sm:inline">Atelier</span>
            </button>
            {breadcrumbs ? (
              <>
                <span className="text-atelier-smoke dark:text-atelier-cream/40">/</span>
                <span className="truncate font-medium text-atelier-sepia dark:text-atelier-cream/60">{breadcrumbs}</span>
              </>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-1 lg:hidden">
            <button
              type="button"
              onClick={() => setLocale(nextLocale)}
              aria-label={`${t("nav.language")}: ${t(localeLabelKey[locale])}`}
              title={t(localeLabelKey[locale])}
              className="inline-flex h-11 w-11 items-center justify-center border border-atelier-smoke/30 bg-atelier-paper text-atelier-sepia shadow-paper-sm transition-colors active:scale-[0.98] hover:border-atelier-vermilion/30 hover:text-atelier-vermilion focus:outline-none focus-visible:ring-2 focus-visible:ring-atelier-vermilion dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-cream"
            >
              <Languages size={16} />
            </button>
            <button
              type="button"
              onClick={() => setThemePreference(nextThemePreference)}
              aria-label={`${t("nav.theme")}: ${t(`theme.${themePreference}`)}`}
              title={t(`theme.${themePreference}`)}
              className="inline-flex h-11 w-11 items-center justify-center border border-atelier-smoke/30 bg-atelier-paper text-atelier-sepia shadow-paper-sm transition-colors active:scale-[0.98] hover:border-atelier-vermilion/30 hover:text-atelier-vermilion focus:outline-none focus-visible:ring-2 focus-visible:ring-atelier-vermilion dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-cream"
            >
              <CurrentThemeIcon size={16} />
            </button>
          </div>
        </div>

        <div className="hidden min-w-0 justify-start overflow-x-auto lg:flex lg:justify-center">
          <div className="flex min-w-max items-center gap-1 border border-atelier-smoke/30 bg-atelier-cream/80 p-1 shadow-paper-press dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:shadow-none">
            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              const active = item.match(location.pathname);
              const label = t(item.labelKey);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  aria-current={active ? "page" : undefined}
                  aria-label={label}
                  className={navItemClassName(active)}
                  title={label}
                >
                  <Icon size={16} className="sm:mr-2" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="hidden min-w-0 flex-wrap items-center justify-start gap-2 lg:flex lg:justify-end">
          <div className="inline-flex items-center gap-1 border border-atelier-smoke/30 bg-atelier-paper p-1 dark:border-atelier-cream/15 dark:bg-atelier-cream/5">
            <Languages size={14} className="ml-1 text-atelier-smoke" aria-hidden="true" />
            {LOCALES.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setLocale(item)}
                aria-label={`${t("nav.language")}: ${t(localeLabelKey[item])}`}
                className={`h-7 px-2 text-xs font-semibold transition-colors ${
                  locale === item
                    ? "bg-atelier-paper text-atelier-vermilion shadow-paper-sm dark:bg-atelier-cream/10 dark:text-atelier-vermilion"
                    : "text-atelier-smoke hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
                }`}
              >
                {t(localeLabelKey[item])}
              </button>
            ))}
          </div>
          <div className="inline-flex items-center gap-1 border border-atelier-smoke/30 bg-atelier-paper p-1 dark:border-atelier-cream/15 dark:bg-atelier-cream/5">
            {THEME_PREFERENCES.map((item) => {
              const Icon = themeIcons[item];
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => setThemePreference(item)}
                  aria-label={`${t("nav.theme")}: ${t(`theme.${item}`)}`}
                  title={t(`theme.${item}`)}
                  className={`inline-flex h-7 w-7 items-center justify-center transition-colors ${
                    themePreference === item
                      ? "bg-atelier-paper text-atelier-vermilion shadow-paper-sm dark:bg-atelier-cream/10 dark:text-atelier-vermilion"
                      : "text-atelier-smoke hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
                  }`}
                >
                  <Icon size={14} />
                </button>
              );
            })}
          </div>
          {onLogout ? (
            <button
              type="button"
              onClick={onLogout}
              aria-label={t("nav.logout")}
              title={t("nav.logout")}
              className="flex items-center px-3 py-2 text-sm font-medium text-atelier-smoke transition-colors hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream"
            >
              <LogOut size={15} className="sm:mr-1.5" /> <span className="hidden sm:inline">{t("nav.logout")}</span>
            </button>
          ) : null}
        </div>
      </nav>

      <div
        aria-label={t("nav.mobile")}
        className="fixed inset-x-0 bottom-0 z-50 border-t border-atelier-smoke/30 bg-atelier-paper/96 px-2 pt-1.5 pb-[calc(env(safe-area-inset-bottom)+0.4rem)] shadow-[0_-10px_30px_rgba(61,40,23,0.10)] backdrop-blur dark:border-atelier-cream/15 dark:bg-[#1F1812]/94 dark:shadow-[0_-18px_40px_rgba(0,0,0,0.35)] lg:hidden"
      >
        <div className="mx-auto grid w-full max-w-md grid-cols-5 gap-1">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = item.match(location.pathname);
            const label = t(item.labelKey);
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? "page" : undefined}
                aria-label={label}
                className={`flex min-h-12 min-w-0 flex-col items-center justify-center px-0.5 text-[10px] font-semibold transition-colors active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-atelier-vermilion ${
                  active
                    ? "bg-atelier-vermilion/5 text-atelier-vermilion dark:bg-atelier-vermilion/12 dark:text-atelier-cream"
                    : "text-atelier-smoke hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/5 dark:hover:text-atelier-cream"
                }`}
              >
                <Icon size={18} aria-hidden="true" />
                <span className="mt-0.5 truncate">{label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </>
  );
}
