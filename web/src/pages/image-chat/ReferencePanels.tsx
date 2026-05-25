import { Check, Image as ImageIcon, ImagePlus, Loader2, Trash2 } from "lucide-react";

import { ImageDropZone } from "../../components/ImageDropZone";
import { SelectField } from "../../components/SelectField";
import { api } from "../../lib/api";
import { formatImageSizeValue } from "../../lib/imageSizes";
import type { ImageSessionAsset, ImageSessionRound, ProductDetail, ProductSummary, SourceAsset } from "../../lib/types";
import type { ImageChatTranslate } from "./display";

interface SessionReferencePanelProps {
  assets: ImageSessionAsset[];
  selectedAssetIds: string[];
  maxSelectedCount: number;
  uploadBusy: boolean;
  deletingAssetId: string | null;
  disabled: boolean;
  onFiles: (files: File[]) => void;
  onToggle: (assetId: string, checked: boolean) => void;
  onDelete: (assetId: string) => void;
  t: ImageChatTranslate;
}

export function SessionReferencePanel({
  assets,
  selectedAssetIds,
  maxSelectedCount,
  uploadBusy,
  deletingAssetId,
  disabled,
  onFiles,
  onToggle,
  onDelete,
  t,
}: SessionReferencePanelProps) {
  return (
    <div className="border border-atelier-smoke/30 bg-atelier-paper p-4 dark:border-atelier-cream/15 dark:bg-[#1F1812]">
      <div className="mb-2 font-display text-sm italic text-atelier-ink dark:text-atelier-cream">{t("chat.sessionReferences")}</div>
      <ImageDropZone
        ariaLabel={t("chat.uploadSessionReference")}
        multiple
        disabled={disabled || uploadBusy}
        className="flex cursor-pointer items-center justify-center border border-dashed border-atelier-smoke/50 bg-atelier-cream px-4 py-4 text-sm text-atelier-sepia transition-colors hover:border-atelier-vermilion/30 hover:bg-atelier-vermilion/5 dark:border-atelier-cream/15 dark:bg-[#1A1410] dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:bg-atelier-vermilion/10"
        onFiles={onFiles}
      >
        {({ isDragging }) => (
          <>
            {uploadBusy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <ImagePlus size={16} className="mr-2" />}
            {isDragging ? t("chat.dropUpload") : t("chat.uploadReference")}
          </>
        )}
      </ImageDropZone>
      <div className="mt-2 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
        {t("chat.selectedReferences", { selected: selectedAssetIds.length, max: maxSelectedCount })}
      </div>
      {assets.length ? (
        <div className="mt-3 grid grid-cols-4 gap-2">
          {assets.map((asset) => {
            const deleting = deletingAssetId === asset.id;
            const selected = selectedAssetIds.includes(asset.id);
            const selectionLimitReached = !selected && selectedAssetIds.length >= maxSelectedCount;
            return (
              <div
                key={asset.id}
                className={`group relative overflow-hidden rounded-xl border bg-atelier-cream dark:bg-[#1A1410] ${
                  selected
                    ? "border-atelier-vermilion ring-2 ring-atelier-vermilion/30 dark:border-atelier-vermilion dark:ring-atelier-vermilion/40"
                    : "border-atelier-smoke/30 dark:border-atelier-cream/15"
                }`}
              >
                <a href={api.toApiUrl(asset.preview_url)} target="_blank" rel="noreferrer" title={asset.original_filename}>
                  <img
                    src={api.toApiUrl(asset.thumbnail_url)}
                    alt={asset.original_filename}
                    loading="lazy"
                    decoding="async"
                    className="h-20 w-full object-cover"
                  />
                </a>
                <label className="absolute bottom-1 left-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-atelier-paper/95 text-atelier-sepia shadow-paper-sm ring-1 ring-atelier-smoke/30 dark:bg-[#241B14]/90 dark:text-atelier-cream dark:ring-atelier-cream/15">
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={selectionLimitReached}
                    onChange={(event) => onToggle(asset.id, event.target.checked)}
                    aria-label={t("chat.useReference")}
                    className="h-3 w-3 border-atelier-smoke/50 text-atelier-vermilion focus:ring-atelier-vermilion"
                  />
                  <span className="sr-only">{t("chat.useReference")}</span>
                </label>
                <button
                  type="button"
                  aria-label={t("chat.deleteSessionReference")}
                  onClick={() => onDelete(asset.id)}
                  disabled={deleting}
                  className="absolute right-1 top-1 inline-flex h-7 w-7 items-center justify-center rounded-md bg-atelier-paper/90 text-atelier-smoke opacity-100 shadow-paper-sm ring-1 ring-atelier-smoke/30 transition-colors hover:text-atelier-vermilion-dark disabled:opacity-60 dark:bg-[#241B14]/90 dark:text-atelier-cream/40 dark:ring-atelier-cream/15 dark:hover:text-atelier-vermilion md:opacity-0 md:group-hover:opacity-100"
                >
                  {deleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

interface ProductAssociationPanelProps {
  isProductMode: boolean;
  product: ProductDetail | undefined;
  products: ProductSummary[];
  targetProductId: string;
  sourceImage: SourceAsset | null;
  referenceImages: SourceAsset[];
  selectedRound: ImageSessionRound | null;
  attachBusy: boolean;
  deletingReferenceAssetId: string | null;
  onTargetProductChange: (value: string) => void;
  onDeleteReference: (assetId: string) => void;
  onAttach: (target: "reference" | "main_source") => void;
  t: ImageChatTranslate;
}

export function ProductAssociationPanel({
  isProductMode,
  product,
  products,
  targetProductId,
  sourceImage,
  referenceImages,
  selectedRound,
  attachBusy,
  deletingReferenceAssetId,
  onTargetProductChange,
  onDeleteReference,
  onAttach,
  t,
}: ProductAssociationPanelProps) {
  const saveDisabled = attachBusy || !selectedRound || (!isProductMode && !targetProductId);

  return (
    <div className="border border-atelier-smoke/30 bg-atelier-cream p-4 dark:border-atelier-cream/15 dark:bg-[#1F1812]">
      <div className="mb-3 font-display text-sm italic text-atelier-ink dark:text-atelier-cream">{t("chat.saveToProduct")}</div>
      {isProductMode ? (
        product ? (
          <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3">
            <ProductThumbnail sourceImage={sourceImage} alt={product.name} />
            <div className="min-w-0 self-center">
              <div className="truncate font-display text-sm italic text-atelier-ink dark:text-atelier-cream">{product.name}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">{t("chat.productReferenceCount", { count: referenceImages.length })}</div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-6 text-atelier-smoke">
            <Loader2 size={16} className="animate-spin" />
          </div>
        )
      ) : (
        <label className="block">
          <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-widest text-atelier-sepia dark:text-atelier-cream/60">{t("chat.targetProduct")}</span>
          <SelectField
            value={targetProductId}
            options={
              products.length
                ? products.map((item) => ({ value: item.id, label: item.name }))
                : [{ value: "", label: t("chat.noProducts"), disabled: true }]
            }
            onChange={onTargetProductChange}
          />
        </label>
      )}

      {referenceImages.length ? (
        <div className="mt-3 grid grid-cols-4 gap-2">
          {referenceImages.slice(0, 4).map((asset) => {
            const deleting = deletingReferenceAssetId === asset.id;
            return (
              <div key={asset.id} className="group relative overflow-hidden rounded-md border border-atelier-smoke/30 bg-atelier-paper dark:border-atelier-cream/15 dark:bg-[#1A1410]">
                <a href={api.toApiUrl(asset.preview_url)} target="_blank" rel="noreferrer" title={asset.original_filename}>
                  <img
                    src={api.toApiUrl(asset.thumbnail_url)}
                    alt={asset.original_filename}
                    loading="lazy"
                    decoding="async"
                    className="h-16 w-full object-cover"
                  />
                </a>
                <button
                  type="button"
                  aria-label={t("chat.deleteProductReference")}
                  onClick={() => onDeleteReference(asset.id)}
                  disabled={deleting}
                  className="absolute right-1 top-1 inline-flex h-6 w-6 items-center justify-center rounded-md bg-atelier-paper/90 text-atelier-smoke opacity-100 shadow-paper-sm ring-1 ring-atelier-smoke/30 transition-colors hover:text-atelier-vermilion-dark disabled:opacity-60 dark:bg-[#241B14]/90 dark:text-atelier-cream/40 dark:ring-atelier-cream/15 dark:hover:text-atelier-vermilion md:opacity-0 md:group-hover:opacity-100"
                >
                  {deleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                </button>
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="mt-4 border-t border-atelier-smoke/30 pt-3 dark:border-atelier-cream/15">
        {selectedRound ? (
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
            {t("chat.selectedCandidate", { size: formatImageSizeValue(selectedRound.size) })}
          </div>
        ) : (
          <div className="mb-2 border border-dashed border-atelier-smoke/30 bg-atelier-paper px-3 py-2 text-center text-sm text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#1A1410] dark:text-atelier-cream/40">
            {t("chat.selectHistoryFirst")}
          </div>
        )}
        <div className="grid gap-2">
          <button
            type="button"
            onClick={() => onAttach("reference")}
            disabled={saveDisabled}
            className="inline-flex items-center justify-center border border-atelier-smoke/30 bg-atelier-paper px-3 py-2 text-sm text-atelier-sepia transition-colors hover:border-atelier-smoke/50 hover:text-atelier-ink disabled:opacity-60 dark:border-atelier-cream/15 dark:bg-[#1A1410] dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-cream"
          >
            {attachBusy ? <Loader2 size={14} className="mr-2 animate-spin" /> : <Check size={14} className="mr-2" />}
            {isProductMode ? t("chat.addReference") : t("chat.saveAsReference")}
          </button>
          {isProductMode ? (
            <button
              type="button"
              onClick={() => onAttach("main_source")}
              disabled={saveDisabled}
              className="inline-flex items-center justify-center bg-atelier-ink px-3 py-2 font-display text-sm italic text-atelier-cream transition-colors hover:bg-atelier-vermilion disabled:opacity-60 dark:bg-atelier-vermilion/20 dark:text-atelier-cream dark:ring-1 dark:ring-atelier-vermilion/40 dark:hover:bg-atelier-vermilion/30"
            >
              {attachBusy ? <Loader2 size={14} className="mr-2 animate-spin" /> : <ImageIcon size={14} className="mr-2" />}
              {t("chat.setMainSource")}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ProductThumbnail({ sourceImage, alt }: { sourceImage: SourceAsset | null; alt: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-atelier-smoke/30 bg-atelier-paper dark:border-atelier-cream/15 dark:bg-[#1A1410]">
      {sourceImage ? (
        <img src={api.toApiUrl(sourceImage.thumbnail_url)} alt={alt} decoding="async" className="h-24 w-full object-cover" />
      ) : (
        <div className="flex h-24 items-center justify-center text-atelier-smoke dark:text-atelier-cream/40">
          <ImageIcon size={20} />
        </div>
      )}
    </div>
  );
}
