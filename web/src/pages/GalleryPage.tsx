import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Flag,
  Image as ImageIcon,
  Import,
  Layers3,
  Loader2,
  Trash2,
  X,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { GalleryImagePreviewDialog } from "../components/GalleryImagePreviewDialog";
import { TopNav } from "../components/TopNav";
import { api, ApiError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { type TranslationKey } from "../lib/i18n";
import { useI18n } from "../lib/preferences";
import type { CanvasTemplateSummary, GalleryEntry } from "../lib/types";
import { TemplateGraphPreview } from "./product-detail/TemplateGroupsPanel";
import { localizedWorkflowNodeTypeLabel } from "./product-detail/nodeDisplay";
import {
  galleryEntryAuthorLabelForLocale,
  galleryEntrySizeLabel,
  galleryTemplateAuthorLabelForLocale,
  galleryTileLayout,
  selectGalleryEntry,
  selectGalleryTemplate,
} from "./gallery/helpers";

type GalleryTab = "images" | "templates";
type TFunction = ReturnType<typeof useI18n>["t"];

const GALLERY_TAB_STORAGE_KEY = "productflow.gallery.tab";
const REPORT_REASON_OPTIONS = ["inappropriate", "copyright", "other"] as const;

function normalizeGalleryTab(value: string | null | undefined): GalleryTab {
  return value === "templates" ? "templates" : "images";
}

function templatePublicId(template: CanvasTemplateSummary): string {
  return template.user_template_id ?? template.key;
}

function metadataRows(
  entry: GalleryEntry,
  locale: ReturnType<typeof useI18n>["locale"],
  t: TFunction,
) {
  const rows: Array<[label: TranslationKey, value: string]> = [
    ["gallery.sharedBy", galleryEntryAuthorLabelForLocale(entry, locale)],
    ["gallery.meta.savedAt", formatDateTime(entry.created_at)],
    ["gallery.meta.size", galleryEntrySizeLabel(entry, locale)],
    ["gallery.meta.model", [entry.provider_name, entry.model_name].filter(Boolean).join(" / ") || t("common.unknown")],
    ["gallery.meta.session", entry.image_session_title],
    ["gallery.meta.product", entry.product_name ?? t("gallery.global")],
    [
      "gallery.meta.candidate",
      entry.candidate_index != null && entry.candidate_count != null
        ? `${entry.candidate_index}/${entry.candidate_count}`
        : t("common.unknown"),
    ],
  ];

  if (entry.forked_from_entry_id) {
    rows.push(["gallery.remix", t("gallery.remixFromCommunity")]);
  }

  return rows;
}

function templateMetadataRows(template: CanvasTemplateSummary, locale: ReturnType<typeof useI18n>["locale"], t: TFunction) {
  const rows: Array<[label: TranslationKey, value: string]> = [
    ["gallery.sharedBy", galleryTemplateAuthorLabelForLocale(template, locale)],
    ["gallery.meta.templateNodes", t("gallery.templateNodeCount", { count: template.preview_nodes.length })],
    ["gallery.meta.templateEdges", t("gallery.templateEdgeCount", { count: template.preview_edges.length })],
  ];
  if (template.shared_at) {
    rows.push(["gallery.meta.savedAt", formatDateTime(template.shared_at)]);
  }
  if (template.forked_from_template_id) {
    rows.push(["gallery.remix", t("gallery.templateRemixFromCommunity")]);
  }
  return rows;
}

function configText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function templateNodePrimaryText(node: CanvasTemplateSummary["preview_nodes"][number]): string | null {
  return (
    configText(node.config_json?.instruction) ??
    configText(node.config_json?.prompt) ??
    node.instruction_seed ??
    node.prompt_seed ??
    null
  );
}

function mutationErrorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.detail : fallback;
}

function GalleryTemplatePreviewDialog({
  template,
  actionError,
  actionMessage,
  importBusy,
  canImport,
  onImport,
  onClose,
}: {
  template: CanvasTemplateSummary;
  actionError: string;
  actionMessage: string;
  importBusy: boolean;
  canImport: boolean;
  onImport: (template: CanvasTemplateSummary) => void;
  onClose: () => void;
}) {
  const { locale, t } = useI18n();
  const [copiedNodeKey, setCopiedNodeKey] = useState<string | null>(null);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const copyNodeText = async (nodeKey: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedNodeKey(nodeKey);
    window.setTimeout(() => setCopiedNodeKey(null), 1200);
  };

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-atelier-ink/86 p-2 backdrop-blur-sm sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("gallery.templatePreviewLabel")}
      onClick={onClose}
    >
      <div
        className="grid h-[calc(100svh-1rem)] max-h-[calc(100svh-1rem)] w-full max-w-[calc(100vw-1rem)] min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,44svh)] overflow-hidden rounded-paper-lg bg-atelier-paper shadow-paper-lg dark:bg-[#1F1812] sm:h-[calc(100svh-2rem)] sm:max-h-[calc(100svh-2rem)] sm:max-w-[calc(100vw-2rem)] lg:grid-cols-[minmax(0,1fr)_minmax(340px,420px)] lg:grid-rows-1 xl:max-w-[94rem]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="min-h-0 overflow-auto bg-atelier-cream dark:bg-[#1A1410]">
          <TemplateGraphPreview template={template} variant="dialog" />
        </div>
        <aside className="flex min-h-0 flex-col border-t border-atelier-smoke/30 dark:border-atelier-cream/15 lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between border-b border-atelier-smoke/30 px-4 py-3 dark:border-atelier-cream/15">
            <div className="min-w-0">
              <div className="truncate font-display text-base italic text-atelier-ink dark:text-atelier-cream">{template.title}</div>
              <div className="mt-0.5 truncate font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                {galleryTemplateAuthorLabelForLocale(template, locale)}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center text-atelier-smoke transition-colors hover:bg-atelier-cream hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream"
              aria-label={t("gallery.closePreview")}
            >
              <X size={18} />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div className="whitespace-pre-wrap break-words text-sm leading-6 text-atelier-sepia dark:text-atelier-cream/80">
              {template.description || t("gallery.templateNoDescription")}
            </div>
            <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
              {templateMetadataRows(template, locale, t).map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">{t(label)}</div>
                  <div className="mt-1 truncate font-medium text-atelier-sepia dark:text-atelier-cream/80">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 border-t border-atelier-smoke/30 pt-4 dark:border-atelier-cream/15">
              <div className="font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">{t("gallery.templateNodes")}</div>
              <div className="mt-3 space-y-2">
                {template.preview_nodes.map((node) => {
                  const primaryText = templateNodePrimaryText(node);
                  return (
                    <div key={node.key} className="border border-atelier-smoke/30 bg-atelier-cream p-3 dark:border-atelier-cream/15 dark:bg-atelier-cream/5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-xs font-semibold text-atelier-ink dark:text-atelier-cream">{node.title}</div>
                          <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                            {localizedWorkflowNodeTypeLabel(node.node_type, t)}
                            {node.size ? ` · ${node.size}` : ""}
                          </div>
                        </div>
                        {primaryText ? (
                          <button
                            type="button"
                            onClick={() => void copyNodeText(node.key, primaryText)}
                            className="shrink-0 border border-atelier-smoke/30 bg-atelier-paper px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-atelier-sepia transition-colors hover:border-atelier-vermilion/30 hover:text-atelier-vermilion dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/80 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-vermilion"
                          >
                            {copiedNodeKey === node.key ? t("gallery.copied") : t("gallery.copy")}
                          </button>
                        ) : null}
                      </div>
                      {primaryText ? (
                        <div className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-atelier-sepia dark:text-atelier-cream/60">
                          {primaryText}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="space-y-2 border-t border-atelier-smoke/30 p-4 dark:border-atelier-cream/15">
            {actionError ? <div className="text-xs font-medium text-atelier-vermilion-dark dark:text-atelier-vermilion">{actionError}</div> : null}
            {actionMessage ? <div className="text-xs font-medium text-atelier-sepia dark:text-atelier-cream/80">{actionMessage}</div> : null}
            {canImport ? (
              <button
                type="button"
                onClick={() => onImport(template)}
                disabled={importBusy}
                className="inline-flex w-full items-center justify-center bg-atelier-ink px-3 py-2.5 font-display text-base italic text-atelier-cream transition-colors hover:bg-atelier-vermilion disabled:opacity-60 dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
              >
                {importBusy ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Import size={16} className="mr-2" />}
                {t("gallery.importTemplate")}
              </button>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  );
}

export function GalleryPage() {
  const { locale, t } = useI18n();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [gridContentWidth, setGridContentWidth] = useState<number | null>(null);
  const [isDesktopGrid, setIsDesktopGrid] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [reportingEntryId, setReportingEntryId] = useState<string | null>(null);
  const [reportReasonCode, setReportReasonCode] = useState<(typeof REPORT_REASON_OPTIONS)[number]>("inappropriate");
  const [reportReasonText, setReportReasonText] = useState("");
  const gridRef = useRef<HTMLDivElement | null>(null);

  const tabFromUrl = normalizeGalleryTab(searchParams.get("tab"));
  const [activeTab, setActiveTabState] = useState<GalleryTab>(() => {
    if (searchParams.get("tab")) {
      return tabFromUrl;
    }
    return normalizeGalleryTab(
      typeof window === "undefined" ? null : window.localStorage.getItem(GALLERY_TAB_STORAGE_KEY),
    );
  });

  const galleryQuery = useQuery({
    queryKey: ["gallery"],
    queryFn: api.listGalleryEntries,
  });
  const templatesQuery = useQuery({
    queryKey: ["gallery", "templates"],
    queryFn: api.listGalleryTemplates,
  });
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: api.getSessionState,
  });
  const entries = galleryQuery.data?.items ?? [];
  const templates = templatesQuery.data?.items ?? [];
  const selectedEntryId = searchParams.get("entry");
  const selectedTemplateId = searchParams.get("template");
  const previewEntry = selectedEntryId ? selectGalleryEntry(entries, selectedEntryId) : null;
  const previewTemplate = selectedTemplateId ? selectGalleryTemplate(templates, selectedTemplateId) : null;
  const currentUserId = sessionQuery.data?.new_api_user_id ?? null;
  const isAdmin = sessionQuery.data?.principal_kind === "admin";
  const canImportTemplate = sessionQuery.data?.authenticated === true && !isAdmin;

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      const nextTab = normalizeGalleryTab(tabParam);
      if (nextTab !== activeTab) {
        setActiveTabState(nextTab);
      }
    }
  }, [activeTab, searchParams]);

  useEffect(() => {
    window.localStorage.setItem(GALLERY_TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

  useEffect(() => {
    const updateGridMetrics = () => {
      setIsDesktopGrid(window.matchMedia("(min-width: 1024px)").matches);
      if (gridRef.current) {
        setGridContentWidth(gridRef.current.clientWidth);
      }
    };

    updateGridMetrics();
    window.addEventListener("resize", updateGridMetrics);

    const gridElement = gridRef.current;
    const resizeObserver =
      typeof ResizeObserver === "undefined" || !gridElement ? null : new ResizeObserver(updateGridMetrics);
    if (gridElement) {
      resizeObserver?.observe(gridElement);
    }

    return () => {
      window.removeEventListener("resize", updateGridMetrics);
      resizeObserver?.disconnect();
    };
  }, []);

  const logoutMutation = useMutation({
    mutationFn: api.destroySession,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      navigate("/login", { replace: true });
    },
  });

  const importEntryMutation = useMutation({
    mutationFn: (entryId: string) => api.importGalleryEntry(entryId),
    onSuccess: async (imageSession) => {
      queryClient.setQueryData(["image-session", imageSession.id], imageSession);
      await queryClient.invalidateQueries({ queryKey: ["image-sessions", "standalone"] });
      navigate("/image-chat");
    },
    onError: (error) => {
      setActionError(mutationErrorText(error, t("gallery.importFailed")));
      setActionMessage("");
    },
  });

  const deleteEntryMutation = useMutation({
    mutationFn: (entryId: string) => api.deleteGalleryEntry(entryId),
    onSuccess: async () => {
      closePreview();
      setActionError("");
      setActionMessage(t("gallery.deleted"));
      await queryClient.invalidateQueries({ queryKey: ["gallery"] });
    },
    onError: (error) => {
      setActionError(mutationErrorText(error, t("gallery.deleteFailed")));
      setActionMessage("");
    },
  });

  const reportEntryMutation = useMutation({
    mutationFn: (payload: { entryId: string; reason_code: string; reason_text?: string | null }) =>
      api.reportGalleryEntry(payload.entryId, {
        reason_code: payload.reason_code,
        reason_text: payload.reason_text,
      }),
    onSuccess: () => {
      setReportingEntryId(null);
      setReportReasonCode("inappropriate");
      setReportReasonText("");
      setActionError("");
      setActionMessage(t("gallery.reported"));
    },
    onError: (error) => {
      setActionError(mutationErrorText(error, t("gallery.reportFailed")));
      setActionMessage("");
    },
  });

  const importTemplateMutation = useMutation({
    mutationFn: (template: CanvasTemplateSummary) => api.importGalleryTemplate(templatePublicId(template)),
    onSuccess: async () => {
      setActionError("");
      setActionMessage(t("gallery.templateImported"));
      await queryClient.invalidateQueries({ queryKey: ["canvas-templates"] });
    },
    onError: (error) => {
      setActionError(mutationErrorText(error, t("gallery.importTemplateFailed")));
      setActionMessage("");
    },
  });

  const setActiveTab = (tab: GalleryTab) => {
    setActiveTabState(tab);
    setActionError("");
    setActionMessage("");
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("tab", tab);
      if (tab === "images") {
        next.delete("template");
      } else {
        next.delete("entry");
      }
      return next;
    });
  };

  const openEntry = (entryId: string) => {
    setActionError("");
    setActionMessage("");
    setActiveTabState("images");
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("tab", "images");
      next.set("entry", entryId);
      next.delete("template");
      return next;
    });
  };

  const openTemplate = (template: CanvasTemplateSummary) => {
    setActionError("");
    setActionMessage("");
    setActiveTabState("templates");
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("tab", "templates");
      next.set("template", templatePublicId(template));
      next.delete("entry");
      return next;
    });
  };

  const closePreview = () => {
    setReportingEntryId(null);
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("entry");
      next.delete("template");
      return next;
    });
  };

  const canDeleteEntry = (entry: GalleryEntry): boolean =>
    isAdmin || Boolean(currentUserId && entry.shared_by_user_id === currentUserId);
  const canReportEntry = (entry: GalleryEntry): boolean =>
    Boolean(currentUserId && !isAdmin && entry.shared_by_user_id !== currentUserId);

  const imageActions = useMemo(() => {
    if (!previewEntry) {
      return null;
    }
    return (
      <>
        {actionError ? <div className="text-xs font-medium text-atelier-vermilion-dark dark:text-atelier-vermilion">{actionError}</div> : null}
        {actionMessage ? <div className="text-xs font-medium text-atelier-sepia dark:text-atelier-cream/80">{actionMessage}</div> : null}
        <button
          type="button"
          onClick={() => importEntryMutation.mutate(previewEntry.id)}
          disabled={importEntryMutation.isPending}
          className="inline-flex w-full items-center justify-center border border-atelier-vermilion/30 bg-atelier-vermilion/5 px-3 py-2.5 font-display text-base italic text-atelier-vermilion transition-colors hover:bg-atelier-vermilion/10 disabled:opacity-60 dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/12 dark:text-atelier-vermilion dark:hover:bg-atelier-vermilion/20"
        >
          {importEntryMutation.isPending ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Import size={16} className="mr-2" />}
          {t("gallery.importImage")}
        </button>
        {canDeleteEntry(previewEntry) ? (
          <button
            type="button"
            onClick={() => {
              if (window.confirm(t("gallery.deleteConfirm"))) {
                deleteEntryMutation.mutate(previewEntry.id);
              }
            }}
            disabled={deleteEntryMutation.isPending}
            className="inline-flex w-full items-center justify-center border border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 px-3 py-2.5 font-display text-base italic text-atelier-vermilion-dark transition-colors hover:bg-atelier-vermilion-dark/10 disabled:opacity-60 dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion dark:hover:bg-atelier-vermilion-dark/20"
          >
            {deleteEntryMutation.isPending ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Trash2 size={16} className="mr-2" />}
            {t("gallery.delete")}
          </button>
        ) : null}
        {canReportEntry(previewEntry) ? (
          reportingEntryId === previewEntry.id ? (
            <form
              className="space-y-2 border border-atelier-smoke/30 bg-atelier-cream p-3 dark:border-atelier-cream/15 dark:bg-atelier-cream/5"
              onSubmit={(event) => {
                event.preventDefault();
                reportEntryMutation.mutate({
                  entryId: previewEntry.id,
                  reason_code: reportReasonCode,
                  reason_text: reportReasonText.trim() || null,
                });
              }}
            >
              <label className="block font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                <span className="sr-only">{t("gallery.reportReason")}</span>
                <select
                  value={reportReasonCode}
                  onChange={(event) => setReportReasonCode(event.target.value as (typeof REPORT_REASON_OPTIONS)[number])}
                  className="h-9 w-full border border-atelier-smoke/30 bg-atelier-paper px-2 text-xs font-medium text-atelier-sepia outline-none focus:border-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-cream"
                >
                  {REPORT_REASON_OPTIONS.map((reason) => (
                    <option key={reason} value={reason}>
                      {t(`gallery.reportReason.${reason}` as TranslationKey)}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                value={reportReasonText}
                onChange={(event) => setReportReasonText(event.target.value)}
                placeholder={t("gallery.reportPlaceholder")}
                maxLength={500}
                className="min-h-20 w-full border border-atelier-smoke/30 bg-atelier-paper px-2 py-2 text-xs text-atelier-sepia outline-none focus:border-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-cream"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setReportingEntryId(null)}
                  className="px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke hover:bg-atelier-paper hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:bg-atelier-cream/10 dark:hover:text-atelier-cream"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={reportEntryMutation.isPending}
                  className="inline-flex bg-atelier-ink px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-atelier-cream transition-colors hover:bg-atelier-vermilion disabled:opacity-60 dark:bg-atelier-cream dark:text-atelier-ink dark:hover:bg-atelier-vermilion dark:hover:text-atelier-cream"
                >
                  {reportEntryMutation.isPending ? <Loader2 size={13} className="mr-1.5 animate-spin" /> : null}
                  {t("gallery.reportSubmit")}
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => {
                setActionError("");
                setActionMessage("");
                setReportingEntryId(previewEntry.id);
              }}
              className="inline-flex w-full items-center justify-center border border-atelier-smoke/30 bg-atelier-paper px-3 py-2.5 font-mono text-[10px] uppercase tracking-wider text-atelier-sepia transition-colors hover:border-atelier-vermilion/40 hover:text-atelier-vermilion dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/80 dark:hover:border-atelier-vermilion/40 dark:hover:text-atelier-vermilion"
            >
              <Flag size={16} className="mr-2" />
              {t("gallery.report")}
            </button>
          )
        ) : null}
      </>
    );
  }, [
    actionError,
    actionMessage,
    currentUserId,
    deleteEntryMutation,
    importEntryMutation,
    isAdmin,
    previewEntry,
    reportEntryMutation,
    reportReasonCode,
    reportReasonText,
    reportingEntryId,
    t,
  ]);

  const activeQueryLoading = activeTab === "images" ? galleryQuery.isLoading : templatesQuery.isLoading;
  const activeQueryError = activeTab === "images" ? galleryQuery.isError : templatesQuery.isError;
  const activeCount = activeTab === "images" ? entries.length : templates.length;

  return (
    <div className="min-h-screen bg-atelier-cream text-atelier-ink dark:bg-[#1A1410] dark:text-atelier-cream">
      <TopNav
        breadcrumbs={t("gallery.title")}
        onHome={() => navigate("/products")}
        onLogout={() => logoutMutation.mutate()}
        session={sessionQuery.data}
      />

      <main className="w-full">
        <section className="relative isolate min-h-[420px] overflow-hidden bg-atelier-kraft sm:min-h-[480px] lg:min-h-[460px] dark:bg-[#241B14]">
          <img
            src="/hero.png"
            alt=""
            decoding="async"
            className="absolute inset-y-0 right-0 h-full w-full object-cover object-center opacity-35 sm:opacity-50 lg:w-[62%] lg:opacity-100"
          />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,#E8DDC4_0%,rgba(232,221,196,0.99)_36%,rgba(232,221,196,0.72)_52%,rgba(232,221,196,0.08)_76%,rgba(232,221,196,0)_100%)] dark:bg-[linear-gradient(90deg,#241B14_0%,rgba(36,27,20,0.99)_36%,rgba(36,27,20,0.72)_52%,rgba(36,27,20,0.08)_76%,rgba(36,27,20,0)_100%)]" />
          <div className="absolute inset-x-0 bottom-0 h-px bg-atelier-smoke/30" />
          <div className="relative z-10 mx-auto grid min-h-[420px] max-w-7xl grid-cols-1 px-6 py-14 sm:min-h-[480px] sm:px-10 lg:min-h-[460px] lg:grid-cols-[minmax(0,0.43fr)_minmax(360px,0.57fr)] lg:items-center lg:px-14">
            <div className="max-w-xl">
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-atelier-smoke">
                {t("gallery.feed")}
              </p>
              <h1 className="mt-6 font-display text-7xl italic leading-none text-atelier-ink sm:text-8xl lg:text-[7rem] dark:text-atelier-cream">
                {t("gallery.title")}
              </h1>
              <p className="mt-6 max-w-md text-base leading-relaxed text-atelier-sepia dark:text-atelier-cream/70">
                {t("gallery.description")}
              </p>
              <span
                aria-hidden="true"
                className="mt-8 inline-block font-display text-3xl text-atelier-ink/30 dark:text-atelier-cream/30"
              >
                ❦
              </span>
            </div>
            <div className="hidden lg:block" />
          </div>
        </section>

        <section className="bg-atelier-cream px-4 py-12 sm:px-6 lg:px-10 dark:bg-[#1A1410]">
          <div className="mx-auto mb-8 flex max-w-7xl flex-col gap-4 border-b border-atelier-smoke/30 pb-6 dark:border-atelier-cream/15 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-atelier-vermilion">
                {t("gallery.feed")}
              </p>
              <h2 className="mt-2 font-display text-3xl italic text-atelier-ink dark:text-atelier-cream">
                {activeTab === "images" ? t("gallery.works") : t("gallery.templates")}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex border border-atelier-smoke/30 p-1 dark:border-atelier-cream/15">
                <button
                  type="button"
                  onClick={() => setActiveTab("images")}
                  className={`inline-flex h-9 items-center px-3 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                    activeTab === "images"
                      ? "bg-atelier-ink text-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink"
                      : "text-atelier-sepia hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
                  }`}
                >
                  <ImageIcon size={14} className="mr-1.5" />
                  {t("gallery.imagesTab")}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("templates")}
                  className={`inline-flex h-9 items-center px-3 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                    activeTab === "templates"
                      ? "bg-atelier-ink text-atelier-cream dark:bg-atelier-cream dark:text-atelier-ink"
                      : "text-atelier-sepia hover:text-atelier-ink dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
                  }`}
                >
                  <Layers3 size={14} className="mr-1.5" />
                  {t("gallery.templatesTab")}
                </button>
              </div>
              <div className="font-mono text-xs text-atelier-smoke">
                {activeTab === "images"
                  ? t("gallery.count", { count: activeCount })
                  : t("gallery.templateCount", { count: activeCount })}
              </div>
            </div>
          </div>

          {activeQueryLoading ? (
            <div className="flex min-h-[320px] items-center justify-center text-atelier-smoke">
              <Loader2 size={28} className="animate-spin" />
            </div>
          ) : activeQueryError ? (
            <div className="flex min-h-[320px] items-center justify-center px-6 text-sm font-medium text-atelier-vermilion-dark dark:text-atelier-vermilion">
              {activeTab === "images" ? t("gallery.loadFailed") : t("gallery.templateLoadFailed")}
            </div>
          ) : activeTab === "images" ? (
            entries.length ? (
              <div
                ref={gridRef}
                className="mx-auto grid max-w-7xl grid-flow-dense grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12 lg:auto-rows-[8px]"
              >
                {entries.map((entry, index) => {
                  const tileLayout = galleryTileLayout(entry, index, gridContentWidth ?? undefined);
                  const tileStyle: CSSProperties = {
                    aspectRatio: tileLayout.aspectRatio,
                    ...(isDesktopGrid ? { gridRowEnd: `span ${tileLayout.rowSpan}` } : {}),
                  };
                  const authorLabel = galleryEntryAuthorLabelForLocale(entry, locale);
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => openEntry(entry.id)}
                      aria-label={`${t("gallery.openDetail")}: ${authorLabel}`}
                      className={`group relative min-w-0 overflow-hidden bg-atelier-ink text-left shadow-paper-sm transition duration-300 hover:-translate-y-1 hover:shadow-paper-lg ${tileLayout.className}`}
                      style={tileStyle}
                    >
                      <div className="relative h-full overflow-hidden bg-atelier-ink">
                        <img
                          src={api.toApiUrl(entry.image.thumbnail_url)}
                          alt={entry.prompt ?? entry.image.original_filename}
                          loading="lazy"
                          decoding="async"
                          className="h-full w-full object-contain transition duration-300"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-atelier-ink/82 via-atelier-ink/10 to-transparent opacity-80 transition-opacity group-hover:opacity-95" />
                        {entry.forked_from_entry_id ? (
                          <div className="absolute left-3 top-3 rounded-full bg-atelier-cream/88 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-atelier-ink shadow-paper-sm">
                            {t("gallery.remix")}
                          </div>
                        ) : null}
                        <div className="absolute inset-x-0 bottom-0 p-4 text-atelier-cream">
                          <div className="line-clamp-2 font-display text-base italic leading-5">
                            {entry.prompt ?? entry.image.original_filename}
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[10px] uppercase tracking-wider text-atelier-cream/75">
                            <span>{authorLabel}</span>
                            <span>{galleryEntrySizeLabel(entry, locale)}</span>
                            <span>{formatDateTime(entry.created_at)}</span>
                          </div>
                          <div className="mt-1 truncate text-[11px] text-atelier-cream/60">{entry.image_session_title}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="flex min-h-[320px] flex-col items-center justify-center border border-dashed border-atelier-smoke/40 bg-atelier-paper px-8 py-16 text-center dark:border-atelier-cream/15 dark:bg-[#221A14]">
                <span
                  aria-hidden="true"
                  className="mb-6 font-display text-6xl italic leading-none text-atelier-smoke"
                >
                  ❦
                </span>
                <p className="font-display text-xl italic text-atelier-ink dark:text-atelier-cream">
                  {t("gallery.empty")}
                </p>
              </div>
            )
          ) : templates.length ? (
            <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {templates.map((template) => (
                <button
                  key={templatePublicId(template)}
                  type="button"
                  onClick={() => openTemplate(template)}
                  className="group overflow-hidden border border-atelier-smoke/30 bg-atelier-paper text-left shadow-paper-sm transition duration-300 hover:-translate-y-1 hover:border-atelier-vermilion/40 hover:shadow-paper-lg dark:border-atelier-cream/15 dark:bg-atelier-cream/5"
                >
                  <TemplateGraphPreview template={template} />
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="line-clamp-2 font-display text-base italic leading-5 text-atelier-ink dark:text-atelier-cream">{template.title}</h3>
                        <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                          {galleryTemplateAuthorLabelForLocale(template, locale)}
                        </div>
                      </div>
                      {template.forked_from_template_id ? (
                        <span className="shrink-0 rounded-full border border-atelier-vermilion/30 bg-atelier-vermilion/5 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-atelier-vermilion dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/12 dark:text-atelier-vermilion">
                          {t("gallery.remix")}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-3 line-clamp-2 text-xs leading-5 text-atelier-sepia dark:text-atelier-cream/60">
                      {template.description || t("gallery.templateNoDescription")}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:text-atelier-cream/40">
                      <span className="rounded-full bg-atelier-cream px-2 py-1 dark:bg-atelier-cream/10">
                        {t("gallery.templateNodeCount", { count: template.preview_nodes.length })}
                      </span>
                      <span className="rounded-full bg-atelier-cream px-2 py-1 dark:bg-atelier-cream/10">
                        {t("gallery.templateEdgeCount", { count: template.preview_edges.length })}
                      </span>
                      {template.shared_at ? (
                        <span className="rounded-full bg-atelier-cream px-2 py-1 dark:bg-atelier-cream/10">{formatDateTime(template.shared_at)}</span>
                      ) : null}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex min-h-[320px] flex-col items-center justify-center border border-dashed border-atelier-smoke/40 bg-atelier-paper px-8 py-16 text-center dark:border-atelier-cream/15 dark:bg-[#221A14]">
              <span
                aria-hidden="true"
                className="mb-6 font-display text-6xl italic leading-none text-atelier-smoke"
              >
                ※
              </span>
              <p className="font-display text-xl italic text-atelier-ink dark:text-atelier-cream">
                {t("gallery.templateEmpty")}
              </p>
            </div>
          )}
        </section>
      </main>

      {previewEntry ? (
        <GalleryImagePreviewDialog
          ariaLabel={t("gallery.previewLabel")}
          imageUrl={api.toApiUrl(previewEntry.image.preview_url)}
          imageAlt={previewEntry.prompt ?? previewEntry.image.original_filename}
          title={t("gallery.prompt")}
          subtitle={`${galleryEntryAuthorLabelForLocale(previewEntry, locale)} / ${previewEntry.image.original_filename}`}
          body={previewEntry.prompt ?? t("gallery.noPrompt")}
          metadataRows={metadataRows(previewEntry, locale, t).map(([label, value]) => ({ label: t(label), value }))}
          providerNotes={previewEntry.provider_notes}
          providerNotesTitle={t("gallery.providerNotes")}
          downloadUrl={previewEntry.image.download_url}
          downloadLabel={t("gallery.download")}
          actions={imageActions}
          closeLabel={t("gallery.closePreview")}
          onClose={closePreview}
        />
      ) : null}
      {previewTemplate ? (
        <GalleryTemplatePreviewDialog
          template={previewTemplate}
          actionError={actionError}
          actionMessage={actionMessage}
          importBusy={importTemplateMutation.isPending}
          canImport={canImportTemplate}
          onImport={(template) => importTemplateMutation.mutate(template)}
          onClose={closePreview}
        />
      ) : null}
    </div>
  );
}
