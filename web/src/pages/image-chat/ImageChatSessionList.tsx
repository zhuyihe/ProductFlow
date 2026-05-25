import { History, Loader2, MessagesSquare, Trash2 } from "lucide-react";

import { api } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { ImageSessionSummary } from "../../lib/types";
import type { ImageChatTranslate } from "./display";

interface ImageChatSessionListProps {
  items: ImageSessionSummary[];
  isLoading: boolean;
  selectedSessionId: string | null;
  deletingSessionId: string | null;
  deletionEnabled: boolean;
  variant: "desktop" | "mobile";
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  t: ImageChatTranslate;
}

export function ImageChatSessionList({
  items,
  isLoading,
  selectedSessionId,
  deletingSessionId,
  deletionEnabled,
  variant,
  onSelectSession,
  onDeleteSession,
  t,
}: ImageChatSessionListProps) {
  const containerClassName =
    variant === "desktop"
      ? "flex gap-3 overflow-x-auto p-3 lg:min-h-0 lg:flex-1 lg:flex-col lg:gap-2 lg:overflow-x-visible lg:overflow-y-auto"
      : "min-h-0 flex-1 space-y-2 overflow-y-auto p-3";

  return (
    <div className={containerClassName}>
      {isLoading ? (
        <div className="flex gap-3 overflow-x-auto lg:flex-col lg:gap-2 lg:overflow-x-visible">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className={`flex shrink-0 items-center gap-3 border border-atelier-smoke/30 bg-atelier-paper p-2.5 dark:border-atelier-cream/15 dark:bg-[#1F1812] ${
                variant === "desktop" ? "w-64 lg:w-auto" : "w-full"
              }`}
            >
              <div className="h-16 w-16 shrink-0 bg-atelier-kraft dark:bg-[#241B14] animate-shimmer" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 bg-atelier-cream dark:bg-atelier-cream/10 animate-shimmer" />
                <div className="h-3 w-1/2 bg-atelier-cream dark:bg-atelier-cream/10 animate-shimmer" />
                <div className="h-3 w-1/3 bg-atelier-cream dark:bg-atelier-cream/10 animate-shimmer" />
              </div>
            </div>
          ))}
        </div>
      ) : items.length ? (
        items.map((item) => (
          <ImageChatSessionCard
            key={item.id}
            item={item}
            active={item.id === selectedSessionId}
            deleting={deletingSessionId === item.id}
            deletionEnabled={deletionEnabled}
            variant={variant}
            onSelectSession={onSelectSession}
            onDeleteSession={onDeleteSession}
            t={t}
          />
        ))
      ) : (
        <div className="border border-dashed border-atelier-smoke/40 p-5 text-center text-sm text-atelier-smoke dark:border-atelier-cream/15 dark:text-atelier-cream/40">
          {t("chat.noSessions")}
        </div>
      )}
    </div>
  );
}

interface ImageChatSessionCardProps {
  item: ImageSessionSummary;
  active: boolean;
  deleting: boolean;
  deletionEnabled: boolean;
  variant: "desktop" | "mobile";
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  t: ImageChatTranslate;
}

function ImageChatSessionCard({
  item,
  active,
  deleting,
  deletionEnabled,
  variant,
  onSelectSession,
  onDeleteSession,
  t,
}: ImageChatSessionCardProps) {
  const cardClassName = `group relative overflow-hidden border-l-2 transition-colors ${
    variant === "desktop" ? "w-64 shrink-0 lg:w-auto " : ""
  }${
    active
      ? "border-atelier-vermilion bg-atelier-vermilion/5 dark:bg-atelier-vermilion/10"
      : "border-transparent bg-atelier-paper hover:border-atelier-smoke/50 hover:bg-atelier-cream dark:bg-[#1F1812] dark:hover:border-atelier-cream/30 dark:hover:bg-[#241B14]"
  }`;
  const selectClassName =
    variant === "desktop"
      ? "flex w-full items-center gap-3 p-2.5 pr-10 text-left"
      : "flex min-h-20 w-full items-center gap-3 p-2.5 pr-12 text-left active:scale-[0.99] focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion";
  const deleteClassName =
    variant === "desktop"
      ? "absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center bg-atelier-paper/95 text-atelier-smoke opacity-100 ring-1 ring-atelier-smoke/30 transition-colors hover:text-atelier-vermilion-dark disabled:opacity-60 dark:bg-[#241B14]/88 dark:text-atelier-cream/40 dark:ring-atelier-cream/15 dark:hover:text-atelier-vermilion md:opacity-0 md:group-hover:opacity-100"
      : "absolute right-2 top-2 inline-flex h-11 w-11 items-center justify-center bg-atelier-paper/95 text-atelier-smoke ring-1 ring-atelier-smoke/30 transition-colors active:scale-[0.98] hover:text-atelier-vermilion-dark disabled:opacity-60 dark:bg-[#241B14]/88 dark:text-atelier-cream/40 dark:ring-atelier-cream/15 dark:hover:text-atelier-vermilion";

  return (
    <div className={cardClassName}>
      <button type="button" onClick={() => onSelectSession(item.id)} className={selectClassName}>
        <div className="relative flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden bg-atelier-cream text-atelier-smoke ring-1 ring-atelier-smoke/30 dark:bg-[#241B14] dark:text-atelier-cream/40 dark:ring-atelier-cream/15">
          {item.latest_generated_asset ? (
            <img
              src={api.toApiUrl(item.latest_generated_asset.thumbnail_url)}
              alt={item.title}
              loading="lazy"
              decoding="async"
              className="h-full w-full object-cover"
            />
          ) : (
            <MessagesSquare size={18} />
          )}
          {active ? <div className="absolute inset-0 ring-2 ring-inset ring-atelier-vermilion/60" /> : null}
        </div>
        <div className="min-w-0 flex-1">
          <div className={`truncate font-display text-base italic ${active ? "text-atelier-ink dark:text-atelier-cream" : "text-atelier-ink dark:text-atelier-cream"}`}>
            {item.title}
          </div>
          <div className="mt-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
            <History size={11} />
            <span>{t("chat.roundCount", { count: item.rounds_count })}</span>
          </div>
          <div className="mt-0.5 truncate font-mono text-[10px] text-atelier-smoke dark:text-atelier-cream/40">{formatDateTime(item.updated_at)}</div>
        </div>
      </button>
      <button
        type="button"
        aria-label={t("chat.deleteSession")}
        onClick={() => onDeleteSession(item.id)}
        disabled={deleting || !deletionEnabled}
        title={deletionEnabled ? t("chat.deleteSession") : t("chat.deleteDisabled")}
        className={deleteClassName}
      >
        {deleting ? <Loader2 size={variant === "desktop" ? 13 : 14} className="animate-spin" /> : <Trash2 size={variant === "desktop" ? 13 : 15} />}
      </button>
    </div>
  );
}
