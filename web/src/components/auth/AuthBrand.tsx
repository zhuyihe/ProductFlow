import { LayoutGrid } from "lucide-react";

import { useI18n } from "../../lib/preferences";

export function AuthBrand() {
  const { t } = useI18n();
  return (
    <div className="mb-8 flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-zinc-900 shadow-sm shadow-zinc-900/20 dark:border dark:border-violet-400/35 dark:bg-violet-500/18 dark:shadow-violet-950/30">
        <LayoutGrid size={20} className="text-white" strokeWidth={2} />
      </div>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-white">
          Atelier
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-slate-400">
          {t("login.subtitle")}
        </p>
      </div>
    </div>
  );
}
