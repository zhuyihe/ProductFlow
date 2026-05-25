import { useEffect, useRef, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";

import type { PromptPreview } from "../../components/PromptPreviewDialog";
import { getVerticalWheelMappedScrollLeft } from "./resizableLayout";
import type { ImageHistoryBranch } from "./branching";
import type { ImageChatTranslate } from "./display";
import { HistoryBranchStrip } from "./HistoryBranchStrip";

function handleHistoryWheelScroll(event: WheelEvent, container: HTMLDivElement) {
  if (event.ctrlKey) {
    return;
  }
  const nextScrollLeft = getVerticalWheelMappedScrollLeft(container, event);
  if (nextScrollLeft === null) {
    return;
  }
  event.preventDefault();
  container.scrollLeft = nextScrollLeft;
}

interface ImageChatHistoryPanelProps {
  historyBranches: ImageHistoryBranch[];
  selectedGeneratedAssetId: string | null;
  selectedTaskPlaceholderId: string | null;
  branchBaseAssetId: string | null;
  branchBaseSelected: boolean;
  variant?: "desktop" | "mobileDrawer";
  style?: CSSProperties;
  onResizeStart?: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  onSelectRound: (assetId: string) => void;
  onSelectPlaceholder: (placeholderId: string) => void;
  onPreviewPrompt: (preview: PromptPreview) => void;
  t: ImageChatTranslate;
}

export function ImageChatHistoryPanel({
  historyBranches,
  selectedGeneratedAssetId,
  selectedTaskPlaceholderId,
  branchBaseAssetId,
  branchBaseSelected,
  variant = "desktop",
  style,
  onResizeStart,
  onSelectRound,
  onSelectPlaceholder,
  onPreviewPrompt,
  t,
}: ImageChatHistoryPanelProps) {
  const desktopHistoryScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = desktopHistoryScrollRef.current;
    if (!container) {
      return;
    }
    const handleWheel = (event: WheelEvent) => handleHistoryWheelScroll(event, container);
    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheel);
    };
  }, [variant, historyBranches.length]);

  if (variant === "mobileDrawer") {
    return (
      <div className="flex min-h-0 flex-1 flex-col bg-atelier-paper dark:bg-[#1F1812]">
        {historyBranches.length ? (
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-3">
            {historyBranches.map((branch) => (
              <HistoryBranchStrip
                key={branch.id}
                branch={branch}
                selectedGeneratedAssetId={selectedGeneratedAssetId}
                selectedTaskPlaceholderId={selectedTaskPlaceholderId}
                branchBaseAssetId={branchBaseAssetId}
                variant="mobileDrawer"
                onSelectRound={onSelectRound}
                onSelectPlaceholder={onSelectPlaceholder}
                onPreviewPrompt={onPreviewPrompt}
                t={t}
              />
            ))}
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 items-center justify-center px-2 py-6">
            <div className="flex min-h-24 w-full items-center justify-center border border-dashed border-atelier-smoke/40 bg-atelier-cream/60 px-2 text-center font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/40">
              {t("chat.resultsAppearHere")}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="relative hidden shrink-0 flex-col border-t border-atelier-smoke/30 bg-atelier-paper px-2.5 py-2 dark:border-atelier-cream/15 dark:bg-[#1F1812] lg:flex lg:h-[var(--image-chat-history-panel-height)] lg:px-3 lg:py-2.5"
      style={style}
    >
      {onResizeStart ? (
        <button
          type="button"
          aria-label={t("chat.resizeHistory")}
          title={t("chat.resizeHistoryTitle")}
          onPointerDown={onResizeStart}
          className="absolute inset-x-0 -top-1 z-20 hidden h-3 cursor-row-resize items-center justify-center transition-colors hover:bg-atelier-vermilion/10 focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:hover:bg-atelier-vermilion/15 lg:flex"
        >
          <span className="h-1 w-12 rounded-full bg-atelier-smoke/50 dark:bg-atelier-cream/30" />
        </button>
      ) : null}
      <div className="mb-1 flex items-center justify-between gap-3 lg:mb-2">
        <div>
          <div className="font-display text-base italic text-atelier-ink dark:text-atelier-cream">{t("chat.history")}</div>
        </div>
        {branchBaseSelected ? (
          <div className="border border-atelier-vermilion/40 bg-atelier-vermilion/5 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-atelier-vermilion dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/10 dark:text-atelier-vermilion">
            {t("chat.clickHistoryBase")}
          </div>
        ) : null}
      </div>

      {historyBranches.length ? (
        <div
          ref={desktopHistoryScrollRef}
          className="image-chat-history-scroll flex min-h-0 flex-1 gap-3 overflow-x-auto overscroll-x-contain pb-1"
        >
          {historyBranches.map((branch) => (
            <HistoryBranchStrip
              key={branch.id}
              branch={branch}
              selectedGeneratedAssetId={selectedGeneratedAssetId}
              selectedTaskPlaceholderId={selectedTaskPlaceholderId}
              branchBaseAssetId={branchBaseAssetId}
              onSelectRound={onSelectRound}
              onSelectPlaceholder={onSelectPlaceholder}
              onPreviewPrompt={onPreviewPrompt}
              t={t}
            />
          ))}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 items-center justify-center border border-dashed border-atelier-smoke/40 bg-atelier-cream/60 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/40">
          {t("chat.resultsAppearHere")}
        </div>
      )}
    </div>
  );
}
