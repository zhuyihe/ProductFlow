import { X } from "lucide-react";

import { useI18n } from "../lib/preferences";

export interface PromptPreview {
  title: string;
  text: string;
  meta?: string;
}

interface PromptPreviewDialogProps {
  preview: PromptPreview;
  onClose: () => void;
}

export function PromptPreviewDialog({ preview, onClose }: PromptPreviewDialogProps) {
  const { t } = useI18n();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-atelier-ink/35 p-4 backdrop-blur-sm">
      <div className="max-h-[82vh] w-full max-w-2xl overflow-hidden rounded-paper-lg border border-atelier-smoke/30 bg-atelier-paper shadow-paper-lg dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-black/45 animate-spring-pop-in">
        <div className="flex items-start justify-between gap-4 border-b border-atelier-smoke/30 px-5 py-4 dark:border-atelier-cream/15">
          <div className="min-w-0">
            <div className="font-display text-base italic text-atelier-ink dark:text-atelier-cream">{preview.title}</div>
            {preview.meta ? (
              <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                {preview.meta}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center text-atelier-smoke transition-colors hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream"
            aria-label={t("promptPreview.close")}
          >
            <X size={16} />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">
          <pre className="whitespace-pre-wrap break-words bg-atelier-cream p-4 font-mono text-sm leading-6 text-atelier-sepia dark:bg-atelier-cream/5 dark:text-atelier-cream/80">
            {preview.text}
          </pre>
        </div>
      </div>
    </div>
  );
}
