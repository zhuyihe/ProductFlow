import { useEffect } from "react";
import { ArrowRight, LayoutGrid } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useI18n } from "../lib/preferences";

interface LoginPageProps {
  authenticated: boolean;
  ssoStartUrl: string | null;
}

export function LoginPage({ authenticated, ssoStartUrl }: LoginPageProps) {
  const { t } = useI18n();
  const navigate = useNavigate();

  useEffect(() => {
    if (authenticated) {
      navigate("/products", { replace: true });
    }
  }, [authenticated, navigate]);

  const handleAuthorize = () => {
    if (!ssoStartUrl) {
      return;
    }
    window.location.assign(ssoStartUrl);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-[#060a12] dark:text-slate-100">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#e4e4e7_1px,transparent_1px),linear-gradient(to_bottom,#e4e4e7_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-50 [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)] dark:bg-[linear-gradient(to_right,rgba(71,85,105,0.34)_1px,transparent_1px),linear-gradient(to_bottom,rgba(71,85,105,0.34)_1px,transparent_1px)] dark:opacity-70" />

      <div className="relative w-full max-w-md px-6">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-zinc-900 shadow-sm shadow-zinc-900/20 dark:border dark:border-violet-400/35 dark:bg-violet-500/18 dark:shadow-violet-950/30">
            <LayoutGrid size={20} className="text-white" strokeWidth={2} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-white">
              ProductFlow
            </h1>
            <p className="mt-1 text-sm text-zinc-500 dark:text-slate-400">
              {t("login.subtitle")}
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-zinc-200/80 bg-white px-5 py-6 shadow-sm shadow-zinc-200/60 dark:border-slate-700/80 dark:bg-[#0b1220] dark:shadow-[0_16px_44px_rgba(0,0,0,0.24)] sm:px-6">
          <p className="text-sm leading-6 text-zinc-600 dark:text-slate-300">
            {t("login.description")}
          </p>

          <button
            type="button"
            onClick={handleAuthorize}
            disabled={!ssoStartUrl}
            className="mt-5 flex w-full items-center justify-center rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-zinc-900/20 transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gradient-to-r dark:from-indigo-500 dark:to-violet-500 dark:shadow-violet-900/35 dark:ring-1 dark:ring-violet-300/35"
          >
            {t("login.submit")} <ArrowRight size={14} className="ml-2 opacity-70" />
          </button>

          {!ssoStartUrl ? (
            <p className="mt-3 text-xs leading-5 text-amber-600 dark:text-amber-300">
              {t("login.ssoUnavailable")}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
