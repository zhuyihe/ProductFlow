import { useI18n } from "../../lib/preferences";

export function AuthFooter() {
  const { t } = useI18n();
  return (
    <p className="mt-6 text-center text-xs leading-5 text-zinc-500 dark:text-slate-400">
      {t("auth.layout.footer.connectedTo")}
    </p>
  );
}
