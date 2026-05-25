import { Download, X } from "lucide-react";
import type { ReactNode } from "react";

import { api } from "../lib/api";

export interface GalleryPreviewMetadataRow {
  label: string;
  value: string;
}

interface GalleryImagePreviewDialogProps {
  ariaLabel: string;
  imageUrl: string;
  imageAlt: string;
  title: string;
  subtitle?: string;
  body: ReactNode;
  metadataRows?: GalleryPreviewMetadataRow[];
  providerNotes?: string[];
  providerNotesTitle: string;
  downloadUrl: string;
  downloadLabel: string;
  actions?: ReactNode;
  closeLabel: string;
  onClose: () => void;
}

export function GalleryImagePreviewDialog({
  ariaLabel,
  imageUrl,
  imageAlt,
  title,
  subtitle,
  body,
  metadataRows = [],
  providerNotes = [],
  providerNotesTitle,
  downloadUrl,
  downloadLabel,
  actions,
  closeLabel,
  onClose,
}: GalleryImagePreviewDialogProps) {
  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center overflow-hidden bg-atelier-ink/86 p-2 backdrop-blur-sm sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      onClick={onClose}
    >
      <div
        className="grid h-[calc(100svh-1rem)] max-h-[calc(100svh-1rem)] w-full max-w-[calc(100vw-1rem)] min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,42svh)] overflow-hidden rounded-paper-lg bg-atelier-paper shadow-paper-lg dark:bg-[#1F1812] sm:h-[calc(100svh-2rem)] sm:max-h-[calc(100svh-2rem)] sm:max-w-[calc(100vw-2rem)] lg:grid-cols-[minmax(0,1fr)_minmax(320px,380px)] lg:grid-rows-1 xl:max-w-[92rem] animate-spring-pop-in"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex min-h-0 items-center justify-center bg-atelier-ink">
          <img src={imageUrl} alt={imageAlt} decoding="async" className="h-full max-h-full w-full object-contain" />
        </div>
        <aside className="flex min-h-0 flex-col border-t border-atelier-smoke/30 dark:border-atelier-cream/15 lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between border-b border-atelier-smoke/30 px-4 py-3 dark:border-atelier-cream/15">
            <div className="min-w-0">
              <div className="font-display text-base italic text-atelier-ink dark:text-atelier-cream">{title}</div>
              {subtitle ? (
                <div className="mt-0.5 truncate font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                  {subtitle}
                </div>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center text-atelier-smoke transition-colors hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream"
              aria-label={closeLabel}
            >
              <X size={18} />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div className="whitespace-pre-wrap break-words text-sm leading-6 text-atelier-sepia dark:text-atelier-cream/80">
              {body}
            </div>
            {metadataRows.length ? (
              <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
                {metadataRows.map((row) => (
                  <div key={row.label} className="min-w-0">
                    <div className="font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                      {row.label}
                    </div>
                    <div className="mt-1 truncate font-medium text-atelier-sepia dark:text-atelier-cream/80">{row.value}</div>
                  </div>
                ))}
              </div>
            ) : null}
            {providerNotes.length ? (
              <div className="mt-6 border-t border-atelier-smoke/30 pt-4 dark:border-atelier-cream/15">
                <div className="font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                  {providerNotesTitle}
                </div>
                <ul className="mt-2 space-y-1 text-xs leading-5 text-atelier-sepia dark:text-atelier-cream/60">
                  {providerNotes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          <div className="space-y-3 border-t border-atelier-smoke/30 p-4 dark:border-atelier-cream/15">
            <a
              href={api.toApiUrl(downloadUrl)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-full items-center justify-center bg-atelier-ink px-3 py-2.5 font-display text-base italic text-atelier-cream transition-colors hover:bg-atelier-vermilion dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
            >
              <Download size={16} className="mr-2" />
              {downloadLabel}
            </a>
            {actions ? <div className="grid gap-2">{actions}</div> : null}
          </div>
        </aside>
      </div>
    </div>
  );
}
