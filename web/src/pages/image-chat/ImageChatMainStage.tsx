import { Layers3, Sparkles } from "lucide-react";

import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { ImageSessionGenerationTask, ImageSessionRound } from "../../lib/types";
import type { ImageHistoryPlaceholderCandidate } from "./branching";
import { GenerationCanvasPlaceholder } from "./GenerationCanvasPlaceholder";
import type { ImageChatTranslate } from "./display";
import { placeholderSizeLabel, placeholderStatusLabel } from "./display";

interface ImageChatMainStageProps {
  selectedRound: ImageSessionRound | null;
  selectedPlaceholder: ImageHistoryPlaceholderCandidate | null;
  branchBaseRound: ImageSessionRound | null;
  retryingTaskId: string | null;
  cancellingTaskId: string | null;
  regenerating: boolean;
  onPreviewRound: (round: ImageSessionRound) => void;
  onRetryGenerationTask: (task: ImageSessionGenerationTask) => void;
  onCancelGenerationTask: (task: ImageSessionGenerationTask) => void;
  onRegenerateGenerationTask: (task: ImageSessionGenerationTask) => void;
  t: ImageChatTranslate;
}

export function ImageChatMainStage({
  selectedRound,
  selectedPlaceholder,
  branchBaseRound,
  retryingTaskId,
  cancellingTaskId,
  regenerating,
  onPreviewRound,
  onRetryGenerationTask,
  onCancelGenerationTask,
  onRegenerateGenerationTask,
  t,
}: ImageChatMainStageProps) {
  return (
    <div className="relative flex min-h-[18rem] flex-1 items-center justify-center overflow-hidden rounded-3xl border border-atelier-smoke/30 bg-atelier-paper shadow-paper-sm dark:border-atelier-cream/15 dark:bg-[#1A1410] dark:shadow-paper-md sm:min-h-[22rem] lg:min-h-[360px]">
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-center justify-between gap-3 px-5 py-4">
        {selectedRound ? (
          <div className="hidden min-w-0 max-w-[calc(100%-5.5rem)] truncate rounded-full bg-atelier-paper/90 px-3 py-1.5 text-xs font-medium text-atelier-sepia shadow-sm ring-1 ring-atelier-smoke/30 backdrop-blur dark:bg-atelier-ink/82 dark:text-atelier-cream dark:ring-atelier-cream/15 lg:block">
            {formatDateTime(selectedRound.created_at)} · {selectedRound.model_name}
          </div>
        ) : selectedPlaceholder ? (
          <div className="hidden min-w-0 max-w-[calc(100%-5.5rem)] truncate rounded-full bg-atelier-paper/90 px-3 py-1.5 text-xs font-medium text-atelier-sepia shadow-sm ring-1 ring-atelier-smoke/30 backdrop-blur dark:bg-atelier-ink/82 dark:text-atelier-cream dark:ring-atelier-cream/15 lg:block">
            {placeholderStatusLabel(selectedPlaceholder, t)} · {placeholderSizeLabel(selectedPlaceholder)}
          </div>
        ) : (
          <div className="hidden rounded-full bg-atelier-paper/90 px-3 py-1.5 text-xs font-medium text-atelier-smoke shadow-sm ring-1 ring-atelier-smoke/30 backdrop-blur dark:border dark:border-atelier-vermilion/40 dark:bg-atelier-ink/82 dark:text-atelier-cream dark:ring-atelier-vermilion/20 lg:block">
            {t("chat.waitingFirstResult")}
          </div>
        )}
        <div className="ml-auto flex shrink-0 items-center gap-2">
          {branchBaseRound ? (
            <div className="hidden h-8 items-center gap-1.5 rounded-full bg-atelier-ink px-3 text-xs font-semibold text-atelier-cream shadow-sm shadow-paper-md dark:bg-atelier-vermilion/15 dark:text-atelier-cream dark:ring-1 dark:ring-atelier-vermilion/40 sm:inline-flex">
              <Layers3 size={13} />
              {t("chat.baseSelected")}
            </div>
          ) : null}
        </div>
      </div>

      {selectedRound ? (
        <div className="absolute inset-0 z-0 flex min-h-0 w-full items-center justify-center px-2 py-2 sm:px-3 sm:py-3 lg:pt-14">
          <button
            type="button"
            onClick={() => onPreviewRound(selectedRound)}
            className="flex h-full w-full items-center justify-center rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-atelier-vermilion dark:focus-visible:ring-atelier-vermilion"
            aria-label={t("chat.previewCurrent")}
            title={t("chat.previewCurrent")}
          >
            <img
              src={api.toApiUrl(selectedRound.generated_asset.preview_url)}
              alt={t("chat.currentResultAlt")}
              decoding="async"
              className="max-h-full max-w-full object-contain drop-shadow-2xl"
            />
          </button>
        </div>
      ) : selectedPlaceholder ? (
        <GenerationCanvasPlaceholder
          candidate={selectedPlaceholder}
          retrying={retryingTaskId === selectedPlaceholder.task_id}
          cancelling={cancellingTaskId === selectedPlaceholder.task_id}
          regenerating={regenerating}
          onRetry={onRetryGenerationTask}
          onCancel={onCancelGenerationTask}
          onRegenerate={onRegenerateGenerationTask}
          t={t}
        />
      ) : (
        <div className="relative z-0 flex flex-col items-center gap-4 text-center text-atelier-smoke dark:text-atelier-cream">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-atelier-paper shadow-sm ring-1 ring-atelier-smoke/30 dark:bg-atelier-ink/86 dark:text-atelier-vermilion dark:ring-atelier-vermilion/30">
            <Sparkles size={28} />
          </div>
          <div>
            <div className="text-sm font-semibold text-atelier-sepia dark:text-atelier-cream">{t("chat.noResult")}</div>
          </div>
        </div>
      )}
    </div>
  );
}
