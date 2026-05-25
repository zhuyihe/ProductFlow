import { useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ChevronRight, Eye, ImagePlus, LayoutTemplate, Loader2, Tag, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Drawer } from "vaul";

import { ImageDropZone } from "../components/ImageDropZone";
import { api, ApiError } from "../lib/api";
import { localizeCanvasTemplateSummary } from "../lib/canvasTemplateLocalization";
import { useI18n } from "../lib/preferences";
import type { TranslationKey } from "../lib/i18n";
import type { CanvasTemplateSummary, WorkflowNodeType } from "../lib/types";

interface PreviewNode {
  id: string;
  title: string;
  subtitle: string;
  x: number;
  y: number;
  width?: number;
  tone?: "input" | "copy" | "image" | "output" | "blank";
}

interface PreviewPortUsage {
  inputs: Set<string>;
  outputs: Set<string>;
}

interface PreviewEdge {
  from: string;
  to: string;
}

interface CanvasPlanOption {
  key: string;
  label: string;
  shortLabel: string;
  description: string;
  badge: string;
  stage: string;
  outputCount: number;
  referenceCount: number;
  previewNodes: PreviewNode[];
  previewEdges: PreviewEdge[];
}

const PREVIEW_MIN_WIDTH = 920;
const PREVIEW_NODE_WIDTH = 248;
const NODE_HEIGHT = 92;
const PRODUCT_CREATE_FORM_ID = "product-create-form";

const NODE_TYPE_LABEL_KEYS: Record<WorkflowNodeType, TranslationKey> = {
  product_context: "create.productContext",
  reference_image: "create.referenceImage",
  copy_generation: "create.copy",
  image_generation: "create.imageGeneration",
};

const stageLabelKeys: Record<string, TranslationKey> = {
  blank: "create.stage.blank",
  listing: "create.stage.listing",
  detail: "create.stage.detail",
  content: "create.stage.content",
  gallery: "create.stage.gallery",
  campaign: "create.stage.campaign",
};

const stageOrder = ["blank", "listing", "detail", "gallery", "content", "campaign"];

// NODE_COLORS: 节点身份语义编码 (G1 决策 + Section 4 PRESERVE)
// sky/violet/emerald/amber 对应 input/copy/image/output 四种节点类型，禁止迁移到 atelier 色板
const toneClasses: Record<NonNullable<PreviewNode["tone"]>, string> = {
  input: "border-sky-100 bg-sky-50/90 text-sky-900 dark:border-sky-400/35 dark:bg-sky-500/12 dark:text-sky-100",
  copy: "border-violet-100 bg-violet-50/90 text-violet-900 dark:border-violet-400/40 dark:bg-violet-500/16 dark:text-violet-100",
  image: "border-emerald-100 bg-emerald-50/90 text-emerald-900 dark:border-emerald-400/35 dark:bg-emerald-500/12 dark:text-emerald-100",
  output: "border-amber-100 bg-amber-50/90 text-amber-900 dark:border-amber-400/35 dark:bg-amber-500/12 dark:text-amber-100",
  blank: "border-dashed border-atelier-smoke/50 bg-atelier-paper/80 text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#241B14]/80 dark:text-atelier-cream/40",
};

function nodeTone(nodeType: WorkflowNodeType, outputNodeKeys: Set<string>, nodeKey: string): PreviewNode["tone"] {
  if (nodeType === "product_context") {
    return "input";
  }
  if (nodeType === "copy_generation") {
    return "copy";
  }
  if (nodeType === "image_generation") {
    return "image";
  }
  return outputNodeKeys.has(nodeKey) ? "output" : "input";
}

function nodeSubtitle(
  node: CanvasTemplateSummary["preview_nodes"][number],
  outputNodeKeys: Set<string>,
  t: ReturnType<typeof useI18n>["t"],
): string {
  if (outputNodeKeys.has(node.key)) {
    return t("create.outputSlot");
  }
  if (node.node_type === "image_generation" && node.size) {
    return node.size.replace("x", " x ");
  }
  return t(NODE_TYPE_LABEL_KEYS[node.node_type]);
}

function canvasTemplateToPlan(template: CanvasTemplateSummary, t: ReturnType<typeof useI18n>["t"]): CanvasPlanOption {
  const outputNodeKeys = new Set(template.output_slots.map((slot) => slot.node_key));
  return {
    key: template.key,
    label: template.title,
    shortLabel: template.output_slots.map((slot) => slot.label).join(" / ") || template.scenario.title,
    description: template.description,
    badge: template.scenario.title || t("create.template"),
    stage: template.scenario.ecommerce_stage,
    outputCount: template.output_slots.length,
    referenceCount: template.reference_input_hints.length,
    previewNodes: template.preview_nodes.map((node) => ({
      id: node.key,
      title: node.title,
      subtitle: nodeSubtitle(node, outputNodeKeys, t),
      x: node.position_x,
      y: node.position_y,
      tone: nodeTone(node.node_type, outputNodeKeys, node.key),
    })),
    previewEdges: template.preview_edges.map((edge) => ({
      from: edge.source_node_key,
      to: edge.target_node_key,
    })),
  };
}

function sortPlans(plans: CanvasPlanOption[]): CanvasPlanOption[] {
  return [...plans].sort((left, right) => {
    const leftIndex = stageOrder.indexOf(left.stage);
    const rightIndex = stageOrder.indexOf(right.stage);
    const normalizedLeft = leftIndex === -1 ? stageOrder.length : leftIndex;
    const normalizedRight = rightIndex === -1 ? stageOrder.length : rightIndex;
    return normalizedLeft - normalizedRight || left.label.localeCompare(right.label, "zh-Hans-CN");
  });
}

function previewWidth(plan: CanvasPlanOption): number {
  if (!plan.previewNodes.length) {
    return PREVIEW_MIN_WIDTH;
  }
  return Math.max(
    PREVIEW_MIN_WIDTH,
    Math.max(...plan.previewNodes.map((node) => node.x + (node.width ?? PREVIEW_NODE_WIDTH))) + 96,
  );
}

function groupedPlans(plans: CanvasPlanOption[], t: ReturnType<typeof useI18n>["t"]) {
  const groups = new Map<string, CanvasPlanOption[]>();
  for (const plan of plans) {
    const items = groups.get(plan.stage) ?? [];
    items.push(plan);
    groups.set(plan.stage, items);
  }
  return stageOrder
    .filter((stage) => groups.has(stage))
    .map((stage) => ({ stage, label: stageLabelKeys[stage] ? t(stageLabelKeys[stage]) : stage, plans: groups.get(stage) ?? [] }));
}

export function ProductCreatePage() {
  const { locale, t } = useI18n();
  const navigate = useNavigate();
  const mobileTemplateButtonRef = useRef<HTMLButtonElement | null>(null);
  const mobilePreviewButtonRef = useRef<HTMLButtonElement | null>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [canvasTemplateKey, setCanvasTemplateKey] = useState<string>("");
  const [error, setError] = useState("");
  const [mobileTemplateSheetOpen, setMobileTemplateSheetOpen] = useState(false);
  const [mobilePreviewSheetOpen, setMobilePreviewSheetOpen] = useState(false);

  const templatesQuery = useQuery({
    queryKey: ["canvas-templates"],
    queryFn: () => api.listCanvasTemplates(),
  });

  const canvasPlanOptions = useMemo(() => {
    const blankCanvasPlan: CanvasPlanOption = {
      key: "",
      label: t("create.blankCanvas"),
      shortLabel: t("create.freeLayout"),
      description: t("create.blankDescription"),
      badge: t("create.basic"),
      stage: "blank",
      outputCount: 0,
      referenceCount: 0,
      previewNodes: [
        { id: "product", title: t("create.productContext"), subtitle: t("create.productInfoNode"), x: 48, y: 112, tone: "input" },
        { id: "blank", title: t("create.freeLayout"), subtitle: t("create.addNode"), x: 368, y: 112, tone: "blank" },
      ],
      previewEdges: [{ from: "product", to: "blank" }],
    };
    const fullCanvasTemplates =
      templatesQuery.data?.items
        .filter((template) => template.kind === "full_canvas")
        .map((template) => localizeCanvasTemplateSummary(template, locale))
        .map((template) => canvasTemplateToPlan(template, t)) ?? [];
    return [blankCanvasPlan, ...sortPlans(fullCanvasTemplates)];
  }, [locale, t, templatesQuery.data]);

  const selectedPlan =
    canvasPlanOptions.find((option) => option.key === canvasTemplateKey) ?? canvasPlanOptions[0];

  const planGroups = useMemo(() => groupedPlans(canvasPlanOptions, t), [canvasPlanOptions, t]);

  const previewLabel = useMemo(() => {
    if (!file) {
      return t("create.uploadIdle");
    }
    return file.name;
  }, [file, t]);

  const createProductMutation = useMutation({
    mutationFn: () => {
      if (!file) {
        throw new Error(t("create.requiredImage"));
      }
      return api.createProduct({
        name,
        file,
        canvas_template_key: selectedPlan.key,
      });
    },
    onSuccess: (product) => {
      navigate(`/products/${product.id}`);
    },
    onError: (mutationError) => {
      if (mutationError instanceof ApiError) {
        setError(mutationError.detail);
        return;
      }
      setError(mutationError instanceof Error ? mutationError.message : t("create.failed"));
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    createProductMutation.mutate();
  };

  const handleImageFiles = (files: File[]) => {
    setFile(files[0] ?? null);
    setError("");
  };

  const templatePanelContent = (
    <>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl italic text-atelier-ink dark:text-atelier-cream">{t("create.templateTitle")}</h2>
          <p className="mt-1 text-sm text-atelier-sepia dark:text-atelier-cream/60">{t("create.templateDescription")}</p>
        </div>
        {templatesQuery.isLoading ? <Loader2 size={16} className="animate-spin text-atelier-smoke" /> : null}
      </div>

      {templatesQuery.isError ? (
        <div className="mt-4 border border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 px-3 py-2 text-sm text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion">
          {t("create.templateLoadFailed")}
        </div>
      ) : null}

      <div className="mt-4 space-y-5 pr-1 lg:max-h-[610px] lg:overflow-y-auto">
        {planGroups.map((group) => (
          <div key={group.stage}>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">{group.label}</h3>
              <span className="font-mono text-[10px] text-atelier-smoke dark:text-atelier-cream/40">{group.plans.length}</span>
            </div>
            <div className="space-y-2">
              {group.plans.map((option) => {
                const selected = selectedPlan.key === option.key;
                return (
                  <button
                    key={option.key || "blank"}
                    type="button"
                    onClick={() => {
                      setCanvasTemplateKey(option.key);
                      setMobileTemplateSheetOpen(false);
                    }}
                    className={`w-full border-l-2 p-3 text-left transition-colors ${
                      selected
                        ? "border-atelier-vermilion bg-atelier-vermilion/5 dark:bg-atelier-vermilion/10"
                        : "border-transparent bg-atelier-paper hover:border-atelier-smoke/50 hover:bg-atelier-cream dark:bg-[#1F1812] dark:hover:border-atelier-cream/30 dark:hover:bg-[#241B14]"
                    }`}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <span className="block truncate font-display text-base italic text-atelier-ink dark:text-atelier-cream">
                          {option.label}
                        </span>
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-atelier-sepia dark:text-atelier-cream/60">
                          {option.description}
                        </p>
                      </div>
                      {selected ? <Check size={14} className="mt-0.5 shrink-0 text-atelier-vermilion dark:text-atelier-vermilion" /> : null}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <TemplateChip>{option.shortLabel}</TemplateChip>
                      {option.outputCount ? <TemplateChip>{t("create.outputCount", { count: option.outputCount })}</TemplateChip> : null}
                      {option.referenceCount ? <TemplateChip>{t("create.referenceCount", { count: option.referenceCount })}</TemplateChip> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </>
  );

  const previewPanelContent = (
    <>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-display text-2xl italic text-atelier-ink dark:text-atelier-cream">{selectedPlan.label}</h2>
            <span className="rounded-full border border-atelier-smoke/30 bg-atelier-cream px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/40">
              {selectedPlan.badge}
            </span>
          </div>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-atelier-sepia dark:text-atelier-cream/60">{selectedPlan.description}</p>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
          <span className="border border-atelier-smoke/30 bg-atelier-cream px-2 py-1 dark:border-atelier-cream/15 dark:bg-[#241B14]">
            {t("create.nodeCount", { count: selectedPlan.previewNodes.length })}
          </span>
          <span className="border border-atelier-smoke/30 bg-atelier-cream px-2 py-1 dark:border-atelier-cream/15 dark:bg-[#241B14]">
            {t("create.edgeCount", { count: selectedPlan.previewEdges.length })}
          </span>
        </div>
      </div>
      <WorkflowPreview plan={selectedPlan} />
    </>
  );

  return (
    <div className="min-h-screen bg-atelier-paper px-4 pb-[calc(6.25rem+env(safe-area-inset-bottom))] pt-4 font-body text-atelier-ink dark:bg-[#1A1410] dark:text-atelier-cream sm:px-6 lg:px-8 lg:pb-8">
      <main className="mx-auto max-w-[1480px]">
        <div className="mb-5 flex items-start justify-between gap-4 border-b border-atelier-smoke/30 pb-4 dark:border-atelier-cream/15">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center bg-atelier-vermilion/10 text-atelier-vermilion dark:border dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/15 dark:text-atelier-vermilion">
              <Tag size={21} />
            </div>
            <div>
              <h1 className="font-display text-3xl italic text-atelier-ink dark:text-atelier-cream">{t("create.title")}</h1>
              <p className="mt-1 text-sm text-atelier-sepia dark:text-atelier-cream/60">{t("create.description")}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate("/products")}
            aria-label={t("create.close")}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-atelier-cream text-atelier-smoke transition-colors hover:bg-atelier-kraft hover:text-atelier-ink dark:border dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/40 dark:hover:bg-[#241B14] dark:hover:text-atelier-cream"
          >
            <X size={18} />
          </button>
        </div>

        <form id={PRODUCT_CREATE_FORM_ID} onSubmit={handleSubmit} className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
          <section className="border border-atelier-smoke/30 bg-atelier-paper p-5 shadow-paper-sm dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-paper-md">
            <h2 className="font-display text-xl italic text-atelier-ink dark:text-atelier-cream">{t("create.productInfo")}</h2>

            <div className="mt-5">
              <label className="mb-2 block font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
                {t("create.mainImage")} <span className="text-atelier-vermilion-dark">*</span>
              </label>
              <ImageDropZone
                ariaLabel={t("create.uploadAria")}
                className="flex aspect-[1.55] cursor-pointer flex-col items-center justify-center border border-dashed border-atelier-smoke/50 bg-atelier-cream/40 p-7 text-atelier-smoke transition-colors hover:border-atelier-vermilion/30 hover:bg-atelier-vermilion/5 dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/40 dark:hover:border-atelier-vermilion/40 dark:hover:bg-atelier-vermilion/10"
                onFiles={handleImageFiles}
              >
                {({ isDragging }) => (
                  <>
                    <ImagePlus size={34} className="mb-3 text-atelier-smoke dark:text-atelier-cream/40" />
                    <p className="text-sm font-medium text-atelier-sepia dark:text-atelier-cream/60">{isDragging ? t("create.uploadDrop") : previewLabel}</p>
                    <p className="mt-2 text-xs text-atelier-smoke dark:text-atelier-cream/40">{t("create.uploadHint")}</p>
                  </>
                )}
              </ImageDropZone>
            </div>

            <div className="mt-6">
              <label className="mb-2 block font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">
                {t("create.productName")} <span className="text-atelier-vermilion-dark">*</span>
              </label>
              <input
                required
                type="text"
                maxLength={60}
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full border border-atelier-smoke/30 bg-atelier-paper px-3 py-2.5 text-sm transition-shadow placeholder:text-atelier-smoke focus:border-atelier-vermilion focus:outline-none focus:ring-1 focus:ring-atelier-vermilion/30 dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream dark:placeholder:text-atelier-cream/40 dark:focus:border-atelier-vermilion dark:focus:ring-atelier-vermilion/30"
                placeholder={t("create.namePlaceholder")}
              />
              <div className="mt-1 text-right font-mono text-[10px] text-atelier-smoke dark:text-atelier-cream/40">{name.length} / 60</div>
            </div>

            <div className="mt-6 border border-atelier-smoke/30 bg-atelier-cream/70 p-3 dark:border-atelier-cream/15 dark:bg-[#241B14] lg:hidden">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:text-atelier-cream/40">{t("create.templateTitle")}</div>
                  <div className="mt-1 truncate font-display text-base italic text-atelier-ink dark:text-atelier-cream">{selectedPlan.label}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <TemplateChip>{selectedPlan.shortLabel}</TemplateChip>
                    <TemplateChip>{t("create.nodeCount", { count: selectedPlan.previewNodes.length })}</TemplateChip>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileTemplateSheetOpen(true)}
                  className="inline-flex min-h-11 shrink-0 items-center border border-atelier-smoke/30 bg-atelier-paper px-3 font-mono text-[10px] uppercase tracking-widest text-atelier-sepia shadow-paper-sm transition-colors hover:border-atelier-vermilion/30 hover:text-atelier-vermilion focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-vermilion dark:focus-visible:ring-atelier-vermilion"
                >
                  {t("create.changeTemplate")}
                </button>
              </div>
            </div>

            {error ? <div className="mt-4 text-sm text-atelier-vermilion-dark dark:text-atelier-vermilion">{error}</div> : null}

            <div className="mt-6 hidden gap-3 lg:flex">
              <button
                type="button"
                onClick={() => navigate("/products")}
                className="flex-1 border border-atelier-smoke/30 px-4 py-2.5 text-sm font-medium text-atelier-sepia transition-colors hover:border-atelier-smoke/50 hover:bg-atelier-cream dark:border-atelier-cream/15 dark:text-atelier-cream/60 dark:hover:border-atelier-cream/30 dark:hover:bg-atelier-vermilion/5 dark:hover:text-atelier-cream"
              >
                {t("create.cancel")}
              </button>
              <button
                type="submit"
                disabled={createProductMutation.isPending}
                className="flex flex-1 items-center justify-center bg-atelier-ink px-4 py-2.5 text-sm font-medium text-atelier-cream transition-colors hover:bg-atelier-vermilion disabled:opacity-50 dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
              >
                {createProductMutation.isPending ? <Loader2 size={15} className="mr-2 animate-spin" /> : null}
                {t("create.submit")}
              </button>
            </div>
          </section>

          <section className="hidden min-h-[720px] gap-5 lg:grid xl:grid-cols-[320px_minmax(0,1fr)]">
            <div className="border border-atelier-smoke/30 bg-atelier-paper p-4 shadow-paper-sm dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-paper-md">
              {templatePanelContent}
            </div>

            <div className="border border-atelier-smoke/30 bg-atelier-paper p-4 shadow-paper-sm dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:shadow-paper-md">
              {previewPanelContent}
            </div>
          </section>
        </form>
      </main>

      <div className="fixed inset-x-0 z-40 px-3 lg:hidden" style={{ bottom: "calc(0.75rem + env(safe-area-inset-bottom))" }}>
        <div className="mx-auto flex max-w-2xl items-center gap-2 border border-atelier-smoke/30 bg-atelier-paper p-2 shadow-paper-md dark:border-atelier-cream/15 dark:bg-[#1F1812]">
          <button
            ref={mobileTemplateButtonRef}
            type="button"
            onClick={() => setMobileTemplateSheetOpen(true)}
            className="inline-flex min-h-11 min-w-0 flex-1 items-center border border-atelier-smoke/30 bg-atelier-paper px-3 text-left font-mono text-[10px] uppercase tracking-widest text-atelier-sepia shadow-paper-sm transition-colors active:scale-[0.98] hover:border-atelier-vermilion/30 hover:text-atelier-vermilion focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-vermilion dark:focus-visible:ring-atelier-vermilion"
            aria-label={t("create.openTemplateSheet")}
          >
            <LayoutTemplate size={16} className="mr-2 shrink-0 text-atelier-vermilion dark:text-atelier-vermilion" />
            <span className="min-w-0 flex-1 truncate">{selectedPlan.shortLabel}</span>
            <ChevronRight size={16} className="ml-2 shrink-0 text-atelier-smoke" />
          </button>
          <button
            ref={mobilePreviewButtonRef}
            type="button"
            onClick={() => setMobilePreviewSheetOpen(true)}
            className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center border border-atelier-smoke/30 bg-atelier-paper px-3 text-atelier-sepia shadow-paper-sm transition-colors active:scale-[0.98] hover:border-atelier-vermilion/30 hover:text-atelier-vermilion focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/60 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-vermilion dark:focus-visible:ring-atelier-vermilion"
            aria-label={t("create.openPreviewSheet")}
            title={t("create.openPreviewSheet")}
          >
            <Eye size={17} />
          </button>
          <button
            type="submit"
            form={PRODUCT_CREATE_FORM_ID}
            disabled={createProductMutation.isPending}
            className="inline-flex min-h-11 shrink-0 items-center justify-center bg-atelier-ink px-3 text-sm font-semibold text-atelier-cream shadow-paper-md transition-colors active:scale-[0.98] hover:bg-atelier-vermilion focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion disabled:opacity-60 dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
          >
            {createProductMutation.isPending ? <Loader2 size={15} className="mr-1.5 animate-spin" /> : null}
            {t("create.submitShort")}
          </button>
        </div>
      </div>

      <Drawer.Root
        direction="bottom"
        handleOnly
        open={mobileTemplateSheetOpen}
        onOpenChange={(open) => {
          setMobileTemplateSheetOpen(open);
          if (!open) {
            mobileTemplateButtonRef.current?.focus();
          }
        }}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-[70] bg-atelier-ink/55 lg:hidden" />
          <Drawer.Content className="fixed inset-x-0 bottom-0 z-[71] flex max-h-[80dvh] flex-col overflow-hidden border-t border-atelier-smoke/30 bg-atelier-paper shadow-paper-lg outline-none dark:border-atelier-cream/15 dark:bg-[#1F1812] lg:hidden">
            <Drawer.Title className="sr-only">{t("create.mobileTemplateSheet")}</Drawer.Title>
            <Drawer.Description className="sr-only">{t("create.templateDescription")}</Drawer.Description>
            <Drawer.Handle className="mx-auto mt-2 flex h-7 w-24 items-center justify-center rounded-full text-atelier-smoke focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:text-atelier-cream/40 dark:focus-visible:ring-atelier-vermilion">
              <span className="h-1.5 w-12 rounded-full bg-atelier-smoke/50 dark:bg-atelier-cream/15" />
            </Drawer.Handle>
            <div data-vaul-no-drag className="min-h-0 flex-1 touch-pan-y overflow-y-auto overscroll-contain px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] pt-2 [-webkit-overflow-scrolling:touch]">
              {templatePanelContent}
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>

      <Drawer.Root
        direction="bottom"
        handleOnly
        open={mobilePreviewSheetOpen}
        onOpenChange={(open) => {
          setMobilePreviewSheetOpen(open);
          if (!open) {
            mobilePreviewButtonRef.current?.focus();
          }
        }}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-[70] bg-atelier-ink/55 lg:hidden" />
          <Drawer.Content className="fixed inset-x-0 bottom-0 z-[71] flex max-h-[80dvh] flex-col overflow-hidden border-t border-atelier-smoke/30 bg-atelier-paper shadow-paper-lg outline-none dark:border-atelier-cream/15 dark:bg-[#1F1812] lg:hidden">
            <Drawer.Title className="sr-only">{t("create.mobilePreviewSheet")}</Drawer.Title>
            <Drawer.Description className="sr-only">{selectedPlan.description}</Drawer.Description>
            <Drawer.Handle className="mx-auto mt-2 flex h-7 w-24 items-center justify-center rounded-full text-atelier-smoke focus:outline-none focus-visible:ring-1 focus-visible:ring-atelier-vermilion dark:text-atelier-cream/40 dark:focus-visible:ring-atelier-vermilion">
              <span className="h-1.5 w-12 rounded-full bg-atelier-smoke/50 dark:bg-atelier-cream/15" />
            </Drawer.Handle>
            <div data-vaul-no-drag className="min-h-0 flex-1 touch-pan-y overflow-y-auto overscroll-contain px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] pt-2 [-webkit-overflow-scrolling:touch]">
              {previewPanelContent}
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </div>
  );
}

function TemplateChip({ children }: { children: ReactNode }) {
  return (
    <span className="border border-atelier-smoke/30 bg-atelier-cream px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#241B14] dark:text-atelier-cream/40">
      {children}
    </span>
  );
}

function WorkflowPreview({ plan }: { plan: CanvasPlanOption }) {
  const nodeById = new Map(plan.previewNodes.map((node) => [node.id, node]));
  const width = previewWidth(plan);
  const portUsage = plan.previewEdges.reduce<PreviewPortUsage>(
    (usage, edge) => {
      usage.outputs.add(edge.from);
      usage.inputs.add(edge.to);
      return usage;
    },
    { inputs: new Set<string>(), outputs: new Set<string>() },
  );
  return (
    <div className="relative h-[560px] overflow-x-auto overflow-y-hidden border border-atelier-smoke/30 bg-atelier-cream dark:border-atelier-cream/15 dark:bg-[#241B14]">
      <div
        className="relative h-full bg-[radial-gradient(circle_at_1px_1px,rgba(156,148,137,0.35)_1px,transparent_0)] bg-[length:16px_16px] dark:bg-[radial-gradient(circle_at_1px_1px,rgba(245,241,232,0.15)_1px,transparent_0)]"
        style={{ width }}
      >
        <svg className="pointer-events-none absolute inset-0 z-0 h-full w-full" viewBox={`0 0 ${width} 560`} aria-hidden="true">
          {plan.previewEdges.map((edge) => {
            const from = nodeById.get(edge.from);
            const to = nodeById.get(edge.to);
            if (!from || !to) {
              return null;
            }
            const fromWidth = from.width ?? PREVIEW_NODE_WIDTH;
            const startX = from.x + fromWidth;
            const startY = from.y + NODE_HEIGHT / 2;
            const endX = to.x;
            const endY = to.y + NODE_HEIGHT / 2;
            const midX = startX + Math.max((endX - startX) / 2, 36);
            return (
              <path
                key={`${edge.from}-${edge.to}`}
                d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
                fill="none"
                className="stroke-atelier-vermilion dark:stroke-atelier-vermilion"
                strokeLinecap="round"
                strokeOpacity="0.75"
                strokeWidth="1.8"
              />
            );
          })}
        </svg>
        {plan.previewNodes.map((node) => (
          <PreviewNodeCard key={node.id} node={node} portUsage={portUsage} />
        ))}
      </div>
    </div>
  );
}

function PreviewNodeCard({ node, portUsage }: { node: PreviewNode; portUsage: PreviewPortUsage }) {
  const { t } = useI18n();
  const width = node.width ?? PREVIEW_NODE_WIDTH;
  const status = node.tone === "copy" || node.tone === "image" ? t("create.pending") : t("create.available");
  const showInputPort = portUsage.inputs.has(node.id);
  const showOutputPort = portUsage.outputs.has(node.id);
  return (
    <div
      className={`absolute z-10 border px-3 py-3 shadow-paper-sm backdrop-blur ${toneClasses[node.tone ?? "input"]}`}
      style={{ left: node.x, top: node.y, width, height: NODE_HEIGHT }}
    >
      {showInputPort ? (
        <span
          aria-hidden="true"
          className="absolute left-[-5px] top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border border-atelier-smoke/50 bg-atelier-paper shadow-paper-sm dark:border-atelier-cream/30 dark:bg-[#241B14]"
        />
      ) : null}
      {showOutputPort ? (
        <span
          aria-hidden="true"
          className="absolute right-[-6px] top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-atelier-vermilion bg-atelier-paper shadow-paper-sm dark:border-atelier-vermilion dark:bg-[#241B14]"
        />
      ) : null}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{node.title}</div>
          <div className="mt-1 truncate text-xs opacity-70">{node.subtitle}</div>
        </div>
        <span className="shrink-0 rounded-full bg-atelier-paper/70 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke dark:bg-[#241B14]/80 dark:text-atelier-cream/40">{status}</span>
      </div>
      <div className="mt-3 flex gap-1.5">
        <span className="h-1.5 w-7 rounded-full bg-current opacity-20" />
        <span className="h-1.5 w-4 rounded-full bg-current opacity-20" />
      </div>
    </div>
  );
}
