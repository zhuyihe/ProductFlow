import { formatDateTime } from "../../lib/format";
import { formatImageSizeValue } from "../../lib/imageSizes";
import type { ImageSessionGenerationTask, ImageSessionRound } from "../../lib/types";
import type { useI18n } from "../../lib/preferences";
import type { ImageHistoryPlaceholderCandidate } from "./branching";
import {
  imageGenerationRetryMetadata,
  isImageSessionGenerationTaskAutoRetrying,
} from "./branching";

export type ImageChatTranslate = ReturnType<typeof useI18n>["t"];

export function generationTaskQueueText(task: ImageSessionGenerationTask, t: ImageChatTranslate) {
  const retryMetadata = imageGenerationRetryMetadata(task);
  if (isImageSessionGenerationTaskAutoRetrying(task) && retryMetadata?.auto_retry_attempt && retryMetadata.max_attempts) {
    return t("chat.autoRetryText", {
      attempt: Math.min(retryMetadata.auto_retry_attempt + 1, retryMetadata.max_attempts),
      max: retryMetadata.max_attempts,
      reason: retryMetadata.last_failure_reason ?? t("chat.autoRetryGenericReason"),
    });
  }
  if (task.status === "queued") {
    const ahead = task.queued_ahead_count ?? 0;
    const position = task.queue_position
      ? t("chat.queuePosition", { position: task.queue_position })
      : t("chat.queueWaiting");
    return t("chat.queueText", {
      ahead,
      position,
      active: task.queue_active_count,
      max: task.queue_max_concurrent_tasks,
    });
  }
  if (task.status === "running") {
    const providerStatus = task.provider_response_status
      ? t("chat.providerStatus", { status: task.provider_response_status })
      : "";
    return t("chat.runningText", {
      providerStatus,
      progress: task.progress_updated_at ? formatDateTime(task.progress_updated_at) : t("chat.progressJustStarted"),
      running: task.queue_running_count,
      queued: task.queue_queued_count,
    });
  }
  return "";
}

export function imageRoundSizeLabel(round: ImageSessionRound, t: ImageChatTranslate) {
  if (round.actual_size && round.actual_size !== round.size) {
    return t("gallery.sizeActualRequested", { actual: round.actual_size, requested: round.size });
  }
  return round.actual_size ?? round.size;
}

export function placeholderStatusLabel(candidate: ImageHistoryPlaceholderCandidate, t: ImageChatTranslate) {
  const retryMetadata = imageGenerationRetryMetadata(candidate.task);
  if (
    isImageSessionGenerationTaskAutoRetrying(candidate.task) &&
    retryMetadata?.auto_retry_attempt &&
    retryMetadata.max_attempts
  ) {
    return t("chat.statusAutoRetry", {
      attempt: Math.min(retryMetadata.auto_retry_attempt + 1, retryMetadata.max_attempts),
      max: retryMetadata.max_attempts,
    });
  }
  if (candidate.status === "queued") {
    return candidate.task.queue_position
      ? t("chat.statusQueuedPosition", { position: candidate.task.queue_position })
      : t("chat.statusQueued");
  }
  if (candidate.status === "running") {
    return t("chat.statusRunning", { index: candidate.candidate_index, count: candidate.candidate_count });
  }
  if (candidate.status === "completed") {
    return t("chat.statusCompletedRefreshing");
  }
  if (candidate.status === "failed") {
    return t("chat.statusFailed");
  }
  if (candidate.status === "cancelled") {
    return t("chat.statusCancelled");
  }
  return t("chat.statusCompleted");
}

export function placeholderStatusClass(candidate: ImageHistoryPlaceholderCandidate) {
  if (candidate.status === "failed") {
    return "border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion";
  }
  if (candidate.status === "queued") {
    return "border-atelier-smoke/40 bg-atelier-kraft text-atelier-sepia dark:border-atelier-cream/15 dark:bg-atelier-cream/10 dark:text-atelier-cream/70";
  }
  if (candidate.status === "completed") {
    return "border-atelier-smoke/30 bg-atelier-cream text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/40";
  }
  if (candidate.status === "cancelled") {
    return "border-atelier-smoke/30 bg-atelier-cream text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/40";
  }
  return "border-atelier-vermilion/30 bg-atelier-vermilion/5 text-atelier-vermilion dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/10 dark:text-atelier-vermilion";
}

export function placeholderSizeLabel(candidate: ImageHistoryPlaceholderCandidate) {
  return formatImageSizeValue(candidate.size);
}
