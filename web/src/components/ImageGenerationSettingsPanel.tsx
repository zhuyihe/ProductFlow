import { ImageToolControls } from "./ImageToolControls";
import { ImageSizePicker } from "./ImageSizePicker";
import { SelectField } from "./SelectField";
import type { ImageSizeOption } from "../lib/imageSizes";
import { formatImageSizeValue } from "../lib/imageSizes";
import { useI18n } from "../lib/preferences";
import type { ImageToolOptionKey, ImageToolOptions } from "../lib/types";

interface ImageGenerationSettingsPanelProps {
  size: string;
  sizeOptions: ImageSizeOption[];
  maxDimension: number;
  toolOptions: ImageToolOptions;
  allowedToolFields: readonly ImageToolOptionKey[];
  modelOptions?: readonly string[];
  lockModelToOptions?: boolean;
  onSizeChange: (size: string) => void;
  onToolOptionsChange: (toolOptions: ImageToolOptions) => void;
  surface?: "card" | "plain";
  generationCount?: number;
  generationCountOptions?: readonly number[];
  generationCountLabel?: string;
  generationCountDescription?: string;
  onGenerationCountChange?: (count: number) => void;
  showToolOptions?: boolean;
}

export function ImageGenerationSettingsPanel({
  size,
  sizeOptions,
  maxDimension,
  toolOptions,
  allowedToolFields,
  modelOptions = [],
  lockModelToOptions = false,
  onSizeChange,
  onToolOptionsChange,
  surface = "card",
  generationCount,
  generationCountOptions,
  generationCountLabel,
  generationCountDescription,
  onGenerationCountChange,
  showToolOptions = true,
}: ImageGenerationSettingsPanelProps) {
  const { t } = useI18n();
  const showCount = generationCount !== undefined && generationCountOptions?.length && onGenerationCountChange;
  const showModelSelect = allowedToolFields.includes("model") && (modelOptions.length > 0 || lockModelToOptions);
  const modelSelectOptions = modelOptions.length
    ? modelOptions.map((model) => ({ value: model, label: model }))
    : [{ value: "", label: t("imageTool.noModels") }];
  const toolControlAllowedFields = showModelSelect
    ? allowedToolFields.filter((field) => field !== "model")
    : allowedToolFields;
  const containerClassName = surface === "card" ? "rounded-2xl border border-slate-200 bg-white p-4" : "space-y-3";

  return (
    <div className={containerClassName}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-slate-950">{t("imageSettings.title")}</div>
        <span className="text-[11px] font-medium text-slate-400">{formatImageSizeValue(size)}</span>
      </div>
      {showModelSelect ? (
        <label className="mb-3 block" htmlFor="image-generation-model">
          <span className="mb-1.5 block text-xs font-semibold text-slate-700">{t("imageTool.model")}</span>
          <SelectField
            id="image-generation-model"
            value={toolOptions.model ?? modelOptions[0] ?? ""}
            options={modelSelectOptions}
            disabled={modelOptions.length <= 1}
            onChange={(nextValue) => onToolOptionsChange({ ...toolOptions, model: nextValue || null })}
          />
        </label>
      ) : null}
      <ImageSizePicker value={size} presets={sizeOptions} maxDimension={maxDimension} onChange={onSizeChange} />
      {showCount ? (
        <label className="mt-3 block" htmlFor="image-generation-count">
          <span className="mb-1.5 block text-xs font-semibold text-slate-700">
            {generationCountLabel ?? t("imageSettings.count")}
          </span>
          {generationCountDescription ? (
            <span className="mb-1.5 block text-[11px] leading-5 text-slate-500">{generationCountDescription}</span>
          ) : null}
          <SelectField
            id="image-generation-count"
            value={String(generationCount)}
            options={generationCountOptions.map((count) => ({
              value: String(count),
              label: t("imageSettings.candidateCount", { count }),
            }))}
            onChange={(nextValue) => onGenerationCountChange(Number(nextValue))}
          />
        </label>
      ) : null}
      {showToolOptions ? (
        <div className="mt-3">
          <ImageToolControls
            surface="plain"
            value={toolOptions}
            allowedFields={toolControlAllowedFields}
            modelOptions={modelOptions}
            lockModelToOptions={lockModelToOptions}
            onChange={onToolOptionsChange}
          />
        </div>
      ) : null}
    </div>
  );
}
