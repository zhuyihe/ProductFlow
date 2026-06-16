import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Eye, Loader2, RefreshCw, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { MiniHero } from "../components/MiniHero";
import { SelectField } from "../components/SelectField";
import { TopNav } from "../components/TopNav";
import { api, ApiError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { TranslationKey } from "../lib/i18n";
import { useI18n } from "../lib/preferences";
import type { TranslateFunction } from "../lib/preferences";
import type { AuditEvent } from "../lib/types";

const PAGE_SIZE = 30;
const AUDIT_STALE_TIME_MS = 20_000;

interface OptionSpec {
  value: string;
  labelKey: TranslationKey;
}

const STATUS_OPTIONS: OptionSpec[] = [
  { value: "", labelKey: "records.filter.allStatuses" },
  { value: "running", labelKey: "records.status.running" },
  { value: "succeeded", labelKey: "records.status.succeeded" },
  { value: "failed", labelKey: "records.status.failed" },
  { value: "cancelled", labelKey: "records.status.cancelled" },
];

const EVENT_TYPE_OPTIONS: OptionSpec[] = [
  { value: "", labelKey: "records.filter.allEventTypes" },
  { value: "model_call", labelKey: "records.event.modelCall" },
  { value: "admin_content_view", labelKey: "records.event.adminContentView" },
  { value: "session", labelKey: "records.event.session" },
  { value: "settings_change", labelKey: "records.event.settingsChange" },
  { value: "export", labelKey: "records.event.export" },
];

export function AdminAuditPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [eventType, setEventType] = useState("");
  const [subjectUserId, setSubjectUserId] = useState("");
  const [requestId, setRequestId] = useState("");
  const [historicalUnowned, setHistoricalUnowned] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [contentViewMessage, setContentViewMessage] = useState("");

  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: api.getSessionState,
    staleTime: AUDIT_STALE_TIME_MS,
  });
  const eventsQuery = useQuery({
    queryKey: [
      "admin-audit-events",
      page,
      PAGE_SIZE,
      status,
      eventType,
      subjectUserId,
      requestId,
      historicalUnowned,
    ],
    queryFn: () =>
      api.listAdminAuditEvents({
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        event_type: eventType || undefined,
        subject_user_id: historicalUnowned ? undefined : subjectUserId.trim() || undefined,
        request_id: requestId.trim() || undefined,
        historical_unowned: historicalUnowned,
      }),
    placeholderData: keepPreviousData,
    staleTime: AUDIT_STALE_TIME_MS,
  });

  const selectedEvent = useMemo(
    () => eventsQuery.data?.items.find((event) => event.id === selectedEventId) ?? null,
    [eventsQuery.data?.items, selectedEventId],
  );
  const total = eventsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
    setSelectedEventId(null);
  }, [status, eventType, subjectUserId, requestId, historicalUnowned]);

  useEffect(() => {
    if (eventsQuery.data && page > totalPages) {
      setPage(totalPages);
    }
  }, [eventsQuery.data, page, totalPages]);

  const logoutMutation = useMutation({
    mutationFn: api.destroySession,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      navigate("/login", { replace: true });
    },
  });

  const contentViewMutation = useMutation({
    mutationFn: (event: AuditEvent) =>
      api.createAdminContentViewEvent({
        event_id: event.id,
        resource_type: event.resource_type ?? "audit_event",
        resource_id: event.resource_id ?? event.id,
      }),
    onSuccess: () => {
      setContentViewMessage(t("audit.contentViewSuccess"));
      void queryClient.invalidateQueries({ queryKey: ["admin-audit-events"] });
    },
    onError: (error) => {
      setContentViewMessage(error instanceof ApiError ? error.detail : t("audit.contentViewFailed"));
    },
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-audit-events"] });
  };

  return (
    <div className="flex min-h-screen flex-col bg-atelier-cream dark:bg-[#1A1410]">
      <TopNav
        onHome={() => navigate("/products")}
        onLogout={() => logoutMutation.mutate()}
        session={sessionQuery.data}
      />
      <MiniHero title={t("audit.title")} meta={t("audit.meta")} ornament="※" />
      <main className="mx-auto flex w-full max-w-7xl flex-1 gap-6 px-6 py-10 lg:py-12">
        <section className="min-w-0 flex-1 border border-atelier-smoke/30 bg-atelier-paper dark:border-atelier-cream/15 dark:bg-[#221A14]">
          <div className="grid gap-4 border-b border-atelier-smoke/30 p-4 dark:border-atelier-cream/15 xl:grid-cols-[repeat(4,minmax(0,1fr))_auto] xl:items-end">
            <LabeledControl label={t("records.filter.eventType")}>
              <SelectField
                value={eventType}
                options={translateOptions(t, EVENT_TYPE_OPTIONS)}
                onChange={setEventType}
                visualSize="sm"
              />
            </LabeledControl>
            <LabeledControl label={t("records.filter.status")}>
              <SelectField
                value={status}
                options={translateOptions(t, STATUS_OPTIONS)}
                onChange={setStatus}
                visualSize="sm"
              />
            </LabeledControl>
            <LabeledControl label={t("audit.filter.subjectUserId")}>
              <input
                value={subjectUserId}
                disabled={historicalUnowned}
                onChange={(event) => setSubjectUserId(event.target.value)}
                className="h-9 w-full border border-atelier-smoke/50 bg-atelier-paper px-3 text-sm text-atelier-ink outline-none transition-colors focus:border-atelier-vermilion disabled:bg-atelier-cream disabled:text-atelier-smoke dark:border-atelier-cream/20 dark:bg-[#1F1812] dark:text-atelier-cream dark:disabled:bg-atelier-cream/5"
                placeholder="new-api user id"
              />
            </LabeledControl>
            <LabeledControl label={t("audit.filter.requestId")}>
              <input
                value={requestId}
                onChange={(event) => setRequestId(event.target.value)}
                className="h-9 w-full border border-atelier-smoke/50 bg-atelier-paper px-3 text-sm text-atelier-ink outline-none transition-colors focus:border-atelier-vermilion dark:border-atelier-cream/20 dark:bg-[#1F1812] dark:text-atelier-cream"
                placeholder="atr_ / new-api request"
              />
            </LabeledControl>
            <div className="flex items-center justify-between gap-3">
              <label className="flex h-9 items-center gap-2 whitespace-nowrap font-mono text-[11px] uppercase tracking-wider text-atelier-smoke">
                <input
                  type="checkbox"
                  checked={historicalUnowned}
                  onChange={(event) => setHistoricalUnowned(event.target.checked)}
                  className="h-4 w-4 accent-atelier-vermilion"
                />
                {t("audit.filter.historicalUnowned")}
              </label>
              <button
                type="button"
                onClick={() => void refresh()}
                className="inline-flex h-9 items-center gap-2 border border-atelier-smoke/30 px-3 font-mono text-[11px] uppercase tracking-wider text-atelier-sepia transition-colors hover:border-atelier-vermilion/40 hover:text-atelier-vermilion dark:border-atelier-cream/15 dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
              >
                <RefreshCw size={13} />
                {t("audit.refresh")}
              </button>
            </div>
          </div>

          {eventsQuery.isLoading ? (
            <LoadingRows />
          ) : eventsQuery.isError ? (
            <PanelMessage text={t("audit.loadFailed")} tone="error" />
          ) : eventsQuery.data?.items.length ? (
            <>
              <AuditTable
                events={eventsQuery.data.items}
                selectedEventId={selectedEventId}
                onSelect={setSelectedEventId}
                t={t}
              />
              <Pagination page={page} totalPages={totalPages} disabled={eventsQuery.isFetching} onPageChange={setPage} />
            </>
          ) : (
            <PanelMessage text={t("audit.empty")} tone="empty" />
          )}
        </section>

        <AuditDetailPanel
          event={selectedEvent}
          message={contentViewMessage}
          busy={contentViewMutation.isPending}
          onClose={() => {
            setSelectedEventId(null);
            setContentViewMessage("");
          }}
          onContentView={(event) => contentViewMutation.mutate(event)}
          t={t}
        />
      </main>
    </div>
  );
}

function AuditTable({
  events,
  selectedEventId,
  onSelect,
  t,
}: {
  events: AuditEvent[];
  selectedEventId: string | null;
  onSelect: (id: string) => void;
  t: TranslateFunction;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-atelier-smoke/20 text-sm dark:divide-atelier-cream/10">
        <thead className="bg-atelier-cream/50 text-left font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:bg-atelier-cream/5">
          <tr>
            <th className="px-4 py-3 font-semibold">{t("records.table.time")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.filter.eventType")}</th>
            <th className="px-4 py-3 font-semibold">{t("audit.detail.user")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.modelGroup")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.requestId")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.resource")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-atelier-smoke/15 dark:divide-atelier-cream/10">
          {events.map((event) => {
            const active = event.id === selectedEventId;
            return (
              <tr
                key={event.id}
                className={`cursor-pointer align-top transition-colors ${
                  active
                    ? "bg-atelier-vermilion/5 dark:bg-atelier-vermilion/10"
                    : "hover:bg-atelier-cream/40 dark:hover:bg-atelier-cream/5"
                }`}
                onClick={() => onSelect(event.id)}
              >
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                  {formatDateTime(event.created_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-atelier-ink dark:text-atelier-cream">
                    {eventLabel(event.event_type, t)}
                  </div>
                  <div className="mt-1">
                    <StatusBadge status={event.status} t={t} />
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                  <div>{event.subject_username ?? "--"}</div>
                  <div className="mt-1 max-w-[10rem] truncate text-atelier-smoke" title={event.subject_user_id ?? ""}>
                    {event.subject_user_id ?? t("audit.historicalUnowned")}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-atelier-ink dark:text-atelier-cream">{event.model_name ?? "--"}</div>
                  <div className="mt-1 font-mono text-[11px] text-atelier-smoke">
                    {event.new_api_token_group ?? event.provider_name ?? "--"}
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-[11px] text-atelier-sepia dark:text-atelier-cream/60">
                  <div className="max-w-[13rem] truncate" title={event.atelier_request_id ?? ""}>
                    {event.atelier_request_id ?? "--"}
                  </div>
                  {event.new_api_request_id ? (
                    <div className="mt-1 max-w-[13rem] truncate text-atelier-smoke" title={event.new_api_request_id}>
                      {event.new_api_request_id}
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                  <div>{event.resource_type ?? "--"}</div>
                  <div className="mt-1 max-w-[11rem] truncate text-atelier-smoke" title={event.resource_id ?? ""}>
                    {event.resource_id ?? "--"}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AuditDetailPanel({
  event,
  message,
  busy,
  onClose,
  onContentView,
  t,
}: {
  event: AuditEvent | null;
  message: string;
  busy: boolean;
  onClose: () => void;
  onContentView: (event: AuditEvent) => void;
  t: TranslateFunction;
}) {
  if (!event) {
    return (
      <aside className="hidden w-80 shrink-0 border border-dashed border-atelier-smoke/40 bg-atelier-paper/50 p-5 text-sm text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#221A14]/50 dark:text-atelier-cream/40 xl:block">
        {t("audit.detail.empty")}
      </aside>
    );
  }

  const canRecordContentView = Boolean(event.resource_type && event.resource_id);

  return (
    <aside className="fixed inset-y-0 right-0 z-[70] w-full max-w-md overflow-y-auto border-l border-atelier-smoke/30 bg-atelier-paper p-5 shadow-paper-lg dark:border-atelier-cream/15 dark:bg-[#1F1812] xl:static xl:z-auto xl:w-96 xl:shadow-none">
      <div className="flex items-start justify-between gap-3 border-b border-atelier-smoke/20 pb-4 dark:border-atelier-cream/10">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-atelier-smoke">
            {t("audit.detail.title")}
          </div>
          <h2 className="mt-1 font-display text-2xl italic text-atelier-ink dark:text-atelier-cream">
            {eventLabel(event.event_type, t)}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-9 w-9 items-center justify-center border border-atelier-smoke/30 text-atelier-smoke transition-colors hover:border-atelier-vermilion/40 hover:text-atelier-vermilion dark:border-atelier-cream/15"
        >
          <X size={15} />
        </button>
      </div>

      <div className="mt-5 space-y-4">
        <DetailRow label={t("audit.detail.status")} value={statusLabel(event.status, t)} />
        <DetailRow label={t("audit.detail.user")} value={`${event.subject_username ?? "--"} / ${event.subject_user_id ?? "--"}`} />
        <DetailRow label={t("audit.detail.actor")} value={`${event.actor_username ?? "--"} / ${event.actor_principal_kind ?? "--"}`} />
        <DetailRow label={t("audit.detail.model")} value={event.model_name ?? "--"} />
        <DetailRow label={t("audit.detail.group")} value={event.new_api_token_group ?? "--"} />
        <DetailRow label={t("audit.detail.quota")} value={formatValue(event.quota)} />
        <DetailRow label={t("audit.detail.atelierRequestId")} value={event.atelier_request_id ?? "--"} />
        <DetailRow label={t("audit.detail.newApiRequestId")} value={event.new_api_request_id ?? "--"} />
        <DetailRow label={t("audit.detail.resource")} value={`${event.resource_type ?? "--"} / ${event.resource_id ?? "--"}`} />
        {event.error_message ? <DetailRow label={t("audit.detail.error")} value={event.error_message} tone="error" /> : null}
      </div>

      {event.metadata_json ? (
        <pre className="mt-5 max-h-64 overflow-auto border border-atelier-smoke/20 bg-atelier-cream/50 p-3 text-xs leading-relaxed text-atelier-sepia dark:border-atelier-cream/10 dark:bg-atelier-cream/5 dark:text-atelier-cream/70">
          {JSON.stringify(event.metadata_json, null, 2)}
        </pre>
      ) : null}

      <button
        type="button"
        disabled={!canRecordContentView || busy}
        onClick={() => onContentView(event)}
        className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 bg-atelier-ink px-4 text-sm font-semibold text-atelier-cream transition-colors hover:bg-atelier-vermilion disabled:bg-atelier-smoke/40 dark:bg-atelier-vermilion dark:hover:bg-atelier-vermilion-dark"
      >
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Eye size={15} />}
        {t("audit.contentView")}
      </button>
      {message ? (
        <p className="mt-3 text-sm text-atelier-sepia dark:text-atelier-cream/60">{message}</p>
      ) : null}
    </aside>
  );
}

function LabeledControl({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-atelier-smoke">{label}</span>
      {children}
    </label>
  );
}

function DetailRow({ label, value, tone }: { label: string; value: string; tone?: "error" }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-atelier-smoke">{label}</div>
      <div
        className={`mt-1 break-words text-sm ${
          tone === "error"
            ? "text-atelier-vermilion-dark dark:text-atelier-vermilion"
            : "text-atelier-ink dark:text-atelier-cream"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function StatusBadge({ status, t }: { status: string; t: TranslateFunction }) {
  const className =
    status === "succeeded"
      ? "border-emerald-200/60 bg-emerald-50/40 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200"
      : status === "failed"
        ? "border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion"
        : status === "running"
          ? "border-blue-200/60 bg-blue-50/40 text-blue-800 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200"
          : "border-atelier-smoke/30 bg-atelier-cream text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/50";
  return (
    <span className={`inline-flex border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${className}`}>
      {statusLabel(status, t)}
    </span>
  );
}

function eventLabel(value: string, t: TranslateFunction): string {
  const labels: Record<string, TranslationKey> = {
    model_call: "records.event.modelCall",
    admin_content_view: "records.event.adminContentView",
    session: "records.event.session",
    settings_change: "records.event.settingsChange",
    export: "records.event.export",
  };
  const key = labels[value];
  return key ? t(key) : value;
}

function statusLabel(value: string, t: TranslateFunction): string {
  const labels: Record<string, TranslationKey> = {
    running: "records.status.running",
    succeeded: "records.status.succeeded",
    failed: "records.status.failed",
    cancelled: "records.status.cancelled",
  };
  const key = labels[value];
  return key ? t(key) : value;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return numeric.toLocaleString("zh-CN", { maximumFractionDigits: 6 });
}

function LoadingRows() {
  return (
    <div className="space-y-2 p-4">
      {[0, 1, 2, 3, 4, 5].map((item) => (
        <div key={item} className="h-12 animate-shimmer" />
      ))}
    </div>
  );
}

function PanelMessage({ text, tone }: { text: string; tone: "empty" | "error" }) {
  const className =
    tone === "error"
      ? "text-atelier-vermilion-dark dark:text-atelier-vermilion"
      : "text-atelier-smoke dark:text-atelier-cream/50";
  return <div className={`px-6 py-16 text-center text-sm ${className}`}>{text}</div>;
}

function Pagination({
  page,
  totalPages,
  disabled,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  disabled: boolean;
  onPageChange: (page: number) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-end gap-3 border-t border-atelier-smoke/20 px-4 py-3 dark:border-atelier-cream/10">
      <button
        type="button"
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(Math.max(1, page - 1))}
        className="inline-flex h-8 items-center gap-1 px-2 font-mono text-[11px] uppercase tracking-wider text-atelier-sepia transition-colors hover:text-atelier-vermilion disabled:opacity-40 dark:text-atelier-cream/60"
      >
        <ArrowLeft size={12} />
        {t("pagination.previous")}
      </button>
      <span className="font-mono text-xs tabular-nums text-atelier-smoke">
        {page} / {totalPages}
      </span>
      <button
        type="button"
        disabled={disabled || page >= totalPages}
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        className="inline-flex h-8 items-center gap-1 px-2 font-mono text-[11px] uppercase tracking-wider text-atelier-sepia transition-colors hover:text-atelier-vermilion disabled:opacity-40 dark:text-atelier-cream/60"
      >
        {t("pagination.next")}
        <ArrowRight size={12} />
      </button>
    </div>
  );
}

function translateOptions(t: TranslateFunction, options: OptionSpec[]) {
  return options.map((option) => ({
    value: option.value,
    label: t(option.labelKey),
  }));
}
