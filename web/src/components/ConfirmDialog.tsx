import { useEffect, useId } from "react";
import { Loader2, TriangleAlert } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  busy?: boolean;
  destructive?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  busy = false,
  destructive = true,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [busy, onClose, open]);

  if (!open) {
    return null;
  }

  const confirmClassName = destructive
    ? "bg-atelier-vermilion-dark text-atelier-cream hover:bg-atelier-vermilion focus-visible:ring-atelier-vermilion-dark dark:bg-atelier-vermilion-dark dark:hover:bg-atelier-vermilion"
    : "bg-atelier-ink text-atelier-cream hover:bg-atelier-vermilion focus-visible:ring-atelier-vermilion dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream";

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-atelier-ink/55 px-4 py-6 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) {
          onClose();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="w-full max-w-md overflow-hidden rounded-paper-lg border border-atelier-smoke/30 bg-atelier-paper shadow-paper-lg dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-black/45 animate-spring-pop-in"
      >
        <div className="flex items-start gap-3 px-5 pt-5">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion">
            <TriangleAlert size={18} />
          </div>
          <div className="min-w-0">
            <h2 id={titleId} className="font-display text-lg italic text-atelier-ink dark:text-atelier-cream">
              {title}
            </h2>
            <p id={descriptionId} className="mt-2 text-sm leading-6 text-atelier-sepia dark:text-atelier-cream/60">
              {description}
            </p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2 border-t border-atelier-smoke/20 bg-atelier-cream px-5 py-3 dark:border-atelier-cream/15 dark:bg-[#1A1410]/45">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="inline-flex h-9 min-w-[72px] items-center justify-center border border-atelier-smoke/30 bg-atelier-paper px-3 text-sm font-medium text-atelier-sepia transition-colors hover:bg-atelier-cream focus:outline-none focus-visible:ring-2 focus-visible:ring-atelier-smoke disabled:opacity-60 dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/80 dark:hover:bg-atelier-cream/10"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={`inline-flex h-9 min-w-[72px] items-center justify-center px-3 text-sm font-semibold shadow-paper-sm transition-colors focus:outline-none focus-visible:ring-2 disabled:opacity-60 ${confirmClassName}`}
          >
            {busy ? <Loader2 size={15} className="mr-2 animate-spin" /> : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
