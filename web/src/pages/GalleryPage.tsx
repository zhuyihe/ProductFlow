import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Flag,
  Image as ImageIcon,
  Import,
  Layers3,
  Loader2,
  Sparkles,
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
      className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/86 p-2 backdrop-blur-sm sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("gallery.templatePreviewLabel")}
      onClick={onClose}
    >
      <div
        className="grid h-[calc(100svh-1rem)] max-h-[calc(100svh-1rem)] w-full max-w-[calc(100vw-1rem)] min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,44svh)] overflow-hidden rounded-lg bg-white shadow-2xl sm:h-[calc(100svh-2rem)] sm:max-h-[calc(100svh-2rem)] sm:max-w-[calc(100vw-2rem)] lg:grid-cols-[minmax(0,1fr)_minmax(340px,420px)] lg:grid-rows-1 xl:max-w-[94rem]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="min-h-0 overflow-auto bg-zinc-50 dark:bg-[#0b1220]">
          <TemplateGraphPreview template={template} variant="dialog" />
        </div>
        <aside className="flex min-h-0 flex-col border-t border-slate-200 lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-bold text-slate-950">{template.title}</div>
              <div className="mt-0.5 truncate text-xs text-slate-500">
                {galleryTemplateAuthorLabelForLocale(template, locale)}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-950"
              aria-label={t("gallery.closePreview")}
            >
              <X size={18} />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">
              {template.description || t("gallery.templateNoDescription")}
            </div>
            <div className="mt-6 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
              {templateMetadataRows(template, locale, t).map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <div className="font-semibold text-slate-400">{t(label)}</div>
                  <div className="mt-1 truncate font-medium text-slate-800">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 border-t border-slate-200 pt-4">
              <div className="text-xs font-bold uppercase text-slate-400">{t("gallery.templateNodes")}</div>
              <div className="mt-3 space-y-2">
                {template.preview_nodes.map((node) => {
                  const primaryText = templateNodePrimaryText(node);
                  return (
                    <div key={node.key} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-xs font-bold text-slate-900">{node.title}</div>
                          <div className="mt-1 text-[11px] font-medium text-slate-500">
                            {localizedWorkflowNodeTypeLabel(node.node_type, t)}
                            {node.size ? ` · ${node.size}` : ""}
                          </div>
                        </div>
                        {primaryText ? (
                          <button
                            type="button"
                            onClick={() => void copyNodeText(node.key, primaryText)}
                            className="shrink-0 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-600 transition-colors hover:border-indigo-200 hover:text-indigo-700"
                          >
                            {copiedNodeKey === node.key ? t("gallery.copied") : t("gallery.copy")}
                          </button>
                        ) : null}
                      </div>
                      {primaryText ? (
                        <div className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">
                          {primaryText}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="space-y-2 border-t border-slate-200 p-4">
            {actionError ? <div className="text-xs font-medium text-red-600">{actionError}</div> : null}
            {actionMessage ? <div className="text-xs font-medium text-emerald-700">{actionMessage}</div> : null}
            {canImport ? (
              <button
                type="button"
                onClick={() => onImport(template)}
                disabled={importBusy}
                className="inline-flex w-full items-center justify-center rounded-lg bg-slate-950 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-60"
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
        {actionError ? <div className="text-xs font-medium text-red-600">{actionError}</div> : null}
        {actionMessage ? <div className="text-xs font-medium text-emerald-700">{actionMessage}</div> : null}
        <button
          type="button"
          onClick={() => importEntryMutation.mutate(previewEntry.id)}
          disabled={importEntryMutation.isPending}
          className="inline-flex w-full items-center justify-center rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2.5 text-sm font-semibold text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-60"
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
            className="inline-flex w-full items-center justify-center rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:opacity-60"
          >
            {deleteEntryMutation.isPending ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Trash2 size={16} className="mr-2" />}
            {t("gallery.delete")}
          </button>
        ) : null}
        {canReportEntry(previewEntry) ? (
          reportingEntryId === previewEntry.id ? (
            <form
              className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3"
              onSubmit={(event) => {
                event.preventDefault();
                reportEntryMutation.mutate({
                  entryId: previewEntry.id,
                  reason_code: reportReasonCode,
                  reason_text: reportReasonText.trim() || null,
                });
              }}
            >
              <label className="block text-xs font-semibold text-slate-500">
                <span className="sr-only">{t("gallery.reportReason")}</span>
                <select
                  value={reportReasonCode}
                  onChange={(event) => setReportReasonCode(event.target.value as (typeof REPORT_REASON_OPTIONS)[number])}
                  className="h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-xs font-medium text-slate-800 outline-none"
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
                className="min-h-20 w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-xs text-slate-800 outline-none"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setReportingEntryId(null)}
                  className="rounded-md px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-white"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={reportEntryMutation.isPending}
                  className="inline-flex rounded-md bg-slate-950 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"
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
              className="inline-flex w-full items-center justify-center rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-amber-200 hover:text-amber-700"
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
    <div className="min-h-screen bg-[#07111d] text-slate-950">
      <TopNav
        breadcrumbs={t("gallery.title")}
        onHome={() => navigate("/products")}
        onLogout={() => logoutMutation.mutate()}
        session={sessionQuery.data}
      />

      <main className="w-full">
        <section className="relative isolate min-h-[420px] overflow-hidden bg-[#f4eddf] sm:min-h-[480px] lg:min-h-[460px]">
          <img
            src="/hero.png"
            alt=""
            decoding="async"
            className="absolute inset-y-0 right-0 h-full w-full object-cover object-center opacity-35 sm:opacity-50 lg:w-[62%] lg:opacity-100"
          />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,#f4eddf_0%,rgba(244,237,223,0.99)_36%,rgba(244,237,223,0.72)_52%,rgba(244,237,223,0.08)_76%,rgba(244,237,223,0)_100%)]" />
          <div className="absolute inset-x-0 bottom-0 h-px bg-[#020617]/10" />
          <div className="relative z-10 mx-auto grid min-h-[420px] max-w-7xl grid-cols-1 px-6 py-14 sm:min-h-[480px] sm:px-10 lg:min-h-[460px] lg:grid-cols-[minmax(0,0.43fr)_minmax(360px,0.57fr)] lg:items-center lg:px-14">
            <div className="max-w-xl">
              <div className="mb-7 h-px w-44 bg-[#020617]/22" />
              <h1 className="text-6xl font-black leading-none text-[#020617] sm:text-7xl lg:text-8xl">
                {t("gallery.title")}
              </h1>
              <p className="mt-6 max-w-md text-base leading-7 text-[#1f2937]">{t("gallery.description")}</p>
              <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-[#020617]/12 bg-white/70 px-3 py-1.5 text-xs font-semibold text-[#1f2937] shadow-sm">
                <Sparkles size={14} className="text-indigo-600" />
                <span>{t("gallery.feed")}</span>
              </div>
            </div>
            <div className="hidden lg:block" />
          </div>
        </section>

        <section className="bg-[#07111d] px-4 py-8 sm:px-6 lg:px-10">
          <div className="mx-auto mb-6 flex max-w-7xl flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-xs font-bold uppercase text-indigo-300">{t("gallery.feed")}</div>
              <h2 className="mt-2 text-2xl font-black text-white">
                {activeTab === "images" ? t("gallery.works") : t("gallery.templates")}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded-xl border border-white/10 bg-white/5 p-1">
                <button
                  type="button"
                  onClick={() => setActiveTab("images")}
                  className={`inline-flex h-9 items-center rounded-lg px-3 text-xs font-bold transition-colors ${
                    activeTab === "images" ? "bg-white text-slate-950" : "text-white/65 hover:text-white"
                  }`}
                >
                  <ImageIcon size={14} className="mr-1.5" />
                  {t("gallery.imagesTab")}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("templates")}
                  className={`inline-flex h-9 items-center rounded-lg px-3 text-xs font-bold transition-colors ${
                    activeTab === "templates" ? "bg-white text-slate-950" : "text-white/65 hover:text-white"
                  }`}
                >
                  <Layers3 size={14} className="mr-1.5" />
                  {t("gallery.templatesTab")}
                </button>
              </div>
              <div className="text-sm font-medium text-white/55">
                {activeTab === "images"
                  ? t("gallery.count", { count: activeCount })
                  : t("gallery.templateCount", { count: activeCount })}
              </div>
            </div>
          </div>

          {activeQueryLoading ? (
            <div className="flex min-h-[320px] items-center justify-center text-white/60">
              <Loader2 size={28} className="animate-spin" />
            </div>
          ) : activeQueryError ? (
            <div className="flex min-h-[320px] items-center justify-center px-6 text-sm font-medium text-red-200">
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
                      className={`group relative min-w-0 overflow-hidden rounded-md bg-slate-900 text-left shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-[#0b4eea]/20 ${tileLayout.className}`}
                      style={tileStyle}
                    >
                      <div className="relative h-full overflow-hidden bg-slate-900">
                        <img
                          src={api.toApiUrl(entry.image.thumbnail_url)}
                          alt={entry.prompt ?? entry.image.original_filename}
                          loading="lazy"
                          decoding="async"
                          className="h-full w-full object-contain transition duration-300"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/82 via-slate-950/10 to-transparent opacity-80 transition-opacity group-hover:opacity-95" />
                        {entry.forked_from_entry_id ? (
                          <div className="absolute left-3 top-3 rounded-full bg-white/88 px-2.5 py-1 text-[11px] font-semibold text-slate-900 shadow-sm">
                            {t("gallery.remix")}
                          </div>
                        ) : null}
                        <div className="absolute inset-x-0 bottom-0 p-4 text-white">
                          <div className="line-clamp-2 text-sm font-semibold leading-5">
                            {entry.prompt ?? entry.image.original_filename}
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-semibold text-white/75">
                            <span>{authorLabel}</span>
                            <span>{galleryEntrySizeLabel(entry, locale)}</span>
                            <span>{formatDateTime(entry.created_at)}</span>
                          </div>
                          <div className="mt-1 truncate text-[11px] text-white/58">{entry.image_session_title}</div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="flex min-h-[320px] flex-col items-center justify-center px-6 text-sm text-white/60">
                <ImageIcon size={30} className="mb-4 text-indigo-300" />
                <div>{t("gallery.empty")}</div>
              </div>
            )
          ) : templates.length ? (
            <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {templates.map((template) => (
                <button
                  key={templatePublicId(template)}
                  type="button"
                  onClick={() => openTemplate(template)}
                  className="group overflow-hidden rounded-md border border-white/10 bg-white text-left shadow-sm transition duration-300 hover:-translate-y-1 hover:border-indigo-300 hover:shadow-2xl hover:shadow-[#0b4eea]/20"
                >
                  <TemplateGraphPreview template={template} />
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="line-clamp-2 text-sm font-bold leading-5 text-slate-950">{template.title}</h3>
                        <div className="mt-1 text-xs font-medium text-slate-500">
                          {galleryTemplateAuthorLabelForLocale(template, locale)}
                        </div>
                      </div>
                      {template.forked_from_template_id ? (
                        <span className="shrink-0 rounded-full border border-indigo-100 bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-700">
                          {t("gallery.remix")}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-3 line-clamp-2 text-xs leading-5 text-slate-500">
                      {template.description || t("gallery.templateNoDescription")}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-500">
                      <span className="rounded-full bg-slate-100 px-2 py-1">
                        {t("gallery.templateNodeCount", { count: template.preview_nodes.length })}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2 py-1">
                        {t("gallery.templateEdgeCount", { count: template.preview_edges.length })}
                      </span>
                      {template.shared_at ? (
                        <span className="rounded-full bg-slate-100 px-2 py-1">{formatDateTime(template.shared_at)}</span>
                      ) : null}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex min-h-[320px] flex-col items-center justify-center px-6 text-sm text-white/60">
              <Layers3 size={30} className="mb-4 text-indigo-300" />
              <div>{t("gallery.templateEmpty")}</div>
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
