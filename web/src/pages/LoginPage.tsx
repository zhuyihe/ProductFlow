import { useEffect } from "react";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AuthLayout } from "../components/auth/AuthLayout";
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
    <AuthLayout>
      <div className="rounded-lg border border-zinc-200/80 bg-white px-5 py-6 shadow-sm shadow-zinc-200/60 dark:border-slate-700/80 dark:bg-[#0b1220] dark:shadow-[0_16px_44px_rgba(0,0,0,0.24)] sm:px-6">
        <p className="text-sm leading-6 text-zinc-600 dark:text-slate-300">
          {t("login.description")}
        </p>

        <div className="mt-4 rounded-md border border-zinc-200/70 bg-zinc-50/80 px-3.5 py-3 dark:border-slate-700/60 dark:bg-slate-900/40">
          <p className="text-xs font-medium text-zinc-700 dark:text-slate-200">
            {t("auth.login.scope.title")}
          </p>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-zinc-600 dark:text-slate-400">
            <li className="flex gap-2">
              <span aria-hidden="true">·</span>
              <span>{t("auth.login.scope.accountInfo")}</span>
            </li>
          </ul>
          <p className="mt-2.5 text-xs leading-5 text-zinc-500 dark:text-slate-500">
            {t("auth.login.scope.passwordRedline")}
          </p>
        </div>

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

        <p className="mt-4 text-center text-[11px] leading-5 text-zinc-400 dark:text-slate-500">
          {t("auth.login.sessionTtl")}
        </p>
      </div>
    </AuthLayout>
  );
}
