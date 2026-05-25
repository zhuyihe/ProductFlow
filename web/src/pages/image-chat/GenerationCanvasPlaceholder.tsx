import { Loader2, OctagonX, RotateCcw, Sparkles } from "lucide-react";

import { formatImageSizeValue } from "../../lib/imageSizes";
import type { ImageSessionGenerationTask } from "../../lib/types";
import {
  imageGenerationRetryMetadata,
  isImageSessionGenerationTaskCancelable,
  isImageSessionGenerationTaskRegeneratable,
  isImageSessionGenerationTaskRetryable,
} from "./branching";
import type { ImageHistoryPlaceholderCandidate } from "./branching";
import type { ImageChatTranslate } from "./display";
import { generationTaskQueueText, placeholderStatusLabel } from "./display";

interface GenerationCanvasPlaceholderProps {
  candidate: ImageHistoryPlaceholderCandidate;
  retrying: boolean;
  cancelling: boolean;
  regenerating: boolean;
  onRetry: (task: ImageSessionGenerationTask) => void;
  onCancel: (task: ImageSessionGenerationTask) => void;
  onRegenerate: (task: ImageSessionGenerationTask) => void;
  t: ImageChatTranslate;
}

export function GenerationCanvasPlaceholder({
  candidate,
  retrying,
  cancelling,
  regenerating,
  onRetry,
  onCancel,
  onRegenerate,
  t,
}: GenerationCanvasPlaceholderProps) {
  const active = candidate.status === "queued" || candidate.status === "running";
  const failed = candidate.status === "failed";
  const cancelled = candidate.status === "cancelled";
  const retryable = isImageSessionGenerationTaskRetryable(candidate.task);
  const regeneratable = isImageSessionGenerationTaskRegeneratable(candidate.task);
  const queueText = generationTaskQueueText(candidate.task, t);
  const retryMetadata = imageGenerationRetryMetadata(candidate.task);
  const nonRetryableReason = candidate.failure_reason ?? retryMetadata?.last_failure_reason;

  return (
    <div className="relative z-0 flex h-full min-h-0 w-full items-center justify-center px-6 pb-6 pt-16">
      <div className="flex max-w-md flex-col items-center text-center">
        <div
          className={`relative flex h-72 w-72 items-center justify-center overflow-hidden rounded-[40px] border shadow-sm transition-[border-color,box-shadow,transform] transition-spring ${
            failed
              ? "border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion"
              : active
                ? "border-transparent bg-atelier-vermilion/10 text-atelier-vermilion animate-running-glow shadow-paper-md"
                : "border-atelier-vermilion/30 bg-atelier-vermilion/5 text-atelier-vermilion dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/10 dark:text-atelier-cream"
          }`}
        >
          {active ? (
            <>
              <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-[40px]">
                <div className="absolute inset-0 bg-gradient-to-b from-atelier-vermilion/5 via-atelier-vermilion/10 to-atelier-vermilion/15 dark:from-atelier-ink/10 dark:to-atelier-ink/20" />
                <div className="absolute left-[30%] bottom-0 w-5 h-5 rounded-full bg-atelier-vermilion/40 blur-[3px] animate-large-p1" />
                <div className="absolute left-[52%] bottom-0 w-4 h-4 rounded-full bg-atelier-vermilion/35 blur-[2px] animate-large-p2" />
                <div className="absolute left-[40%] bottom-0 w-6 h-6 rounded-full bg-atelier-vermilion/30 blur-[4px] animate-large-p3" />
                <div className="absolute left-[62%] bottom-0 w-3 h-3 rounded-full bg-atelier-vermilion/50 blur-[1px] animate-large-p4" />
                <div className="absolute left-[35%] bottom-0 w-5.5 h-5.5 rounded-full bg-atelier-vermilion/30 blur-[3px] animate-large-p5" />
                <div className="absolute left-[45%] bottom-0 w-4.5 h-4.5 rounded-full bg-atelier-vermilion/40 blur-[2px] animate-large-p6" />
              </div>
              <div className="absolute inset-6 rounded-[32px] bg-atelier-vermilion/20 blur-2xl animate-pulse" />
              <Loader2 size={48} className="relative z-10 animate-spin text-atelier-vermilion dark:text-atelier-vermilion" />
            </>
          ) : (
            <Sparkles size={48} className="relative" />
          )}
        </div>
        <div className="mt-4 font-display text-base italic text-atelier-ink dark:text-atelier-cream">{placeholderStatusLabel(candidate, t)}</div>
        <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
          {t("chat.candidate", { index: candidate.candidate_index, count: candidate.candidate_count })} · {formatImageSizeValue(candidate.size)}
        </div>
        {queueText ? <div className="mt-3 max-w-sm text-xs leading-5 text-atelier-smoke dark:text-atelier-cream/40">{queueText}</div> : null}
        <div className="mt-4 line-clamp-3 max-w-sm rounded-xl border border-atelier-smoke/30 bg-atelier-paper/80 px-3 py-2 text-xs font-medium leading-5 text-atelier-sepia shadow-sm dark:border-atelier-cream/15 dark:bg-atelier-ink/75 dark:text-atelier-cream/70">
          {candidate.prompt}
        </div>
        {isImageSessionGenerationTaskCancelable(candidate.task) ? (
          <button
            type="button"
            onClick={() => onCancel(candidate.task)}
            disabled={cancelling}
            className="mt-5 inline-flex items-center justify-center rounded-xl border border-atelier-vermilion-dark/30 bg-atelier-paper px-4 py-2 text-sm font-semibold text-atelier-vermilion-dark shadow-sm transition-colors hover:bg-atelier-vermilion-dark/5 disabled:opacity-60 dark:border-atelier-vermilion/40 dark:bg-[#1F1812] dark:text-atelier-vermilion dark:hover:bg-atelier-vermilion-dark/15"
          >
            {cancelling ? <Loader2 size={15} className="mr-2 animate-spin" /> : <OctagonX size={15} className="mr-2" />}
            {t("chat.cancelGeneration")}
          </button>
        ) : null}
        {failed && retryable ? (
          <button
            type="button"
            onClick={() => onRetry(candidate.task)}
            disabled={retrying}
            className="mt-5 inline-flex items-center justify-center rounded-xl bg-atelier-vermilion-dark px-4 py-2 text-sm font-semibold text-atelier-cream shadow-paper-md transition-colors hover:bg-atelier-vermilion disabled:opacity-60"
          >
            {retrying ? <Loader2 size={15} className="mr-2 animate-spin" /> : <RotateCcw size={15} className="mr-2" />}
            {t("chat.retryGeneration")}
          </button>
        ) : failed ? (
          <div className="mt-5 max-w-sm rounded-xl border border-atelier-vermilion-dark/30 bg-atelier-paper px-3 py-2 text-xs font-medium leading-5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-[#1F1812] dark:text-atelier-vermilion">
            <div>{t("chat.notRetryable")}</div>
            {nonRetryableReason ? <div className="mt-1 text-atelier-vermilion-dark/80 dark:text-atelier-vermilion/80">{nonRetryableReason}</div> : null}
          </div>
        ) : cancelled ? (
          <>
            <div className="mt-5 rounded-xl border border-atelier-smoke/30 bg-atelier-paper px-3 py-2 text-xs font-medium text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke">
              {t("chat.taskCancelled")}
            </div>
            {regeneratable ? (
              <button
                type="button"
                onClick={() => onRegenerate(candidate.task)}
                disabled={regenerating}
                className="mt-3 inline-flex items-center justify-center rounded-xl bg-atelier-ink px-4 py-2 text-sm font-semibold text-atelier-cream shadow-paper-md transition-colors hover:bg-atelier-vermilion disabled:opacity-60 dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
              >
                {regenerating ? <Loader2 size={15} className="mr-2 animate-spin" /> : <RotateCcw size={15} className="mr-2" />}
                {t("chat.regenerateCancelled")}
              </button>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
