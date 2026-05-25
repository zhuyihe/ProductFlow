import type { ProductWorkflowState } from "../lib/types";
import { useI18n } from "../lib/preferences";

// G6/G7 决策：B 去饱和保留语义色。copy_ready/poster_ready 的 blue/emerald 是
// token-migration-map.md Section 9.1 批准的局部例外。
const CONFIG: Record<
  ProductWorkflowState,
  { textKey: "status.draft" | "status.copyReady" | "status.posterReady" | "status.failed"; classes: string; dot: string }
> = {
  draft: {
    textKey: "status.draft",
    classes:
      "bg-atelier-cream text-atelier-smoke border-atelier-smoke/30 dark:bg-atelier-cream/5 dark:text-atelier-cream/40 dark:border-atelier-cream/15",
    dot: "bg-atelier-smoke dark:bg-atelier-cream/30",
  },
  copy_ready: {
    textKey: "status.copyReady",
    classes:
      "bg-blue-50/40 text-blue-800 border-blue-200/60 dark:bg-blue-500/10 dark:text-blue-200 dark:border-blue-400/30",
    dot: "bg-blue-500 dark:bg-blue-400",
  },
  poster_ready: {
    textKey: "status.posterReady",
    classes:
      "bg-emerald-50/40 text-emerald-800 border-emerald-200/60 dark:bg-emerald-500/10 dark:text-emerald-200 dark:border-emerald-400/30",
    dot: "bg-emerald-500 dark:bg-emerald-400",
  },
  failed: {
    textKey: "status.failed",
    classes:
      "bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark border-atelier-vermilion-dark/30 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion dark:border-atelier-vermilion/40",
    dot: "bg-atelier-vermilion-dark dark:bg-atelier-vermilion",
  },
};

export function StatusPill({ status }: { status: ProductWorkflowState }) {
  const { t } = useI18n();
  const config = CONFIG[status];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${config.classes}`}>
      <span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {t(config.textKey)}
    </span>
  );
}
