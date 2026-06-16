import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { MiniHero } from "../components/MiniHero";
import { SelectField } from "../components/SelectField";
import { TopNav } from "../components/TopNav";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { TranslationKey } from "../lib/i18n";
import { useI18n } from "../lib/preferences";
import type { TranslateFunction } from "../lib/preferences";
import type { AuditEvent, AuditEventStatus } from "../lib/types";

const PAGE_SIZE = 20;
const RECORDS_STALE_TIME_MS = 30_000;

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

export function RecordsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [eventType, setEventType] = useState("model_call");

  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: api.getSessionState,
    staleTime: RECORDS_STALE_TIME_MS,
  });
  const summaryQuery = useQuery({
    queryKey: ["usage-summary"],
    queryFn: api.getUsageSummary,
    staleTime: RECORDS_STALE_TIME_MS,
  });
  const eventsQuery = useQuery({
    queryKey: ["usage-events", page, PAGE_SIZE, status, eventType],
    queryFn: () =>
      api.listUsageEvents({
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        event_type: eventType || undefined,
      }),
    placeholderData: keepPreviousData,
    staleTime: RECORDS_STALE_TIME_MS,
  });

  const total = eventsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [status, eventType]);

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

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["usage-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["usage-events"] }),
    ]);
  };

  return (
    <div className="flex min-h-screen flex-col bg-atelier-cream dark:bg-[#1A1410]">
      <TopNav
        onHome={() => navigate("/products")}
        onLogout={() => logoutMutation.mutate()}
        session={sessionQuery.data}
      />
      <MiniHero title={t("records.title")} meta={t("records.meta")} ornament="§" />
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10 lg:py-12">
        <div className="w-full space-y-8">
          <section className="grid gap-4 md:grid-cols-3">
            <Metric label={t("records.summary.totalEvents")} value={summaryQuery.data?.total_events ?? 0} />
            <Metric label={t("records.summary.totalQuota")} value={formatQuota(summaryQuery.data?.total_quota)} />
            <Metric label={t("records.summary.failedEvents")} value={summaryQuery.data?.failed_events ?? 0} />
          </section>

          <section className="border border-atelier-smoke/30 bg-atelier-paper dark:border-atelier-cream/15 dark:bg-[#221A14]">
            <div className="flex flex-col gap-4 border-b border-atelier-smoke/30 p-4 dark:border-atelier-cream/15 md:flex-row md:items-end md:justify-between">
              <div className="grid gap-3 md:grid-cols-2">
                <LabeledSelect label={t("records.filter.eventType")}>
                  <SelectField
                    value={eventType}
                    options={translateOptions(t, EVENT_TYPE_OPTIONS)}
                    onChange={setEventType}
                    visualSize="sm"
                  />
                </LabeledSelect>
                <LabeledSelect label={t("records.filter.status")}>
                  <SelectField
                    value={status}
                    options={translateOptions(t, STATUS_OPTIONS)}
                    onChange={setStatus}
                    visualSize="sm"
                  />
                </LabeledSelect>
              </div>
              <button
                type="button"
                onClick={() => void refresh()}
                className="inline-flex h-9 items-center gap-2 border border-atelier-smoke/30 px-3 font-mono text-[11px] uppercase tracking-wider text-atelier-sepia transition-colors hover:border-atelier-vermilion/40 hover:text-atelier-vermilion dark:border-atelier-cream/15 dark:text-atelier-cream/60 dark:hover:text-atelier-cream"
              >
                <RefreshCw size={13} />
                {t("records.refresh")}
              </button>
            </div>

            {eventsQuery.isLoading ? (
              <LoadingRows />
            ) : eventsQuery.isError ? (
              <PanelMessage tone="error" text={t("records.loadFailed")} />
            ) : eventsQuery.data?.items.length ? (
              <>
                <RecordsTable events={eventsQuery.data.items} t={t} />
                <Pagination page={page} totalPages={totalPages} disabled={eventsQuery.isFetching} onPageChange={setPage} />
              </>
            ) : (
              <PanelMessage tone="empty" text={t("records.empty")} />
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function RecordsTable({ events, t }: { events: AuditEvent[]; t: TranslateFunction }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-atelier-smoke/20 text-sm dark:divide-atelier-cream/10">
        <thead className="bg-atelier-cream/50 text-left font-mono text-[10px] uppercase tracking-wider text-atelier-smoke dark:bg-atelier-cream/5">
          <tr>
            <th className="px-4 py-3 font-semibold">{t("records.table.time")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.status")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.modelGroup")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.usage")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.resource")}</th>
            <th className="px-4 py-3 font-semibold">{t("records.table.requestId")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-atelier-smoke/15 dark:divide-atelier-cream/10">
          {events.map((event) => (
            <tr key={event.id} className="align-top hover:bg-atelier-cream/40 dark:hover:bg-atelier-cream/5">
              <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                {formatDateTime(event.created_at)}
              </td>
              <td className="px-4 py-3">
                <EventStatusPill status={event.status} t={t} />
                {event.error_message ? (
                  <p className="mt-2 max-w-xs text-xs leading-relaxed text-atelier-vermilion-dark dark:text-atelier-vermilion">
                    {event.error_message}
                  </p>
                ) : null}
              </td>
              <td className="px-4 py-3">
                <div className="font-medium text-atelier-ink dark:text-atelier-cream">
                  {event.model_name ?? "--"}
                </div>
                <div className="mt-1 font-mono text-[11px] text-atelier-smoke">
                  {event.new_api_token_group ?? event.provider_name ?? "--"}
                </div>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                <div>{formatQuota(event.quota)}</div>
                <div className="mt-1 text-atelier-smoke">
                  {event.prompt_tokens ?? 0}p / {event.completion_tokens ?? 0}c
                </div>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-atelier-sepia dark:text-atelier-cream/60">
                <div>{event.resource_type ?? "--"}</div>
                <div className="mt-1 max-w-[12rem] truncate text-atelier-smoke" title={event.resource_id ?? ""}>
                  {event.resource_id ?? "--"}
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="border border-atelier-smoke/30 bg-atelier-paper p-5 dark:border-atelier-cream/15 dark:bg-[#221A14]">
      <div className="font-display text-3xl italic tabular-nums text-atelier-ink dark:text-atelier-cream">{value}</div>
      <div className="mt-2 font-mono text-[10px] uppercase tracking-widest text-atelier-smoke">{label}</div>
    </div>
  );
}

function LabeledSelect({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block min-w-[11rem]">
      <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-atelier-smoke">{label}</span>
      {children}
    </label>
  );
}

function EventStatusPill({ status, t }: { status: string; t: TranslateFunction }) {
  const classes = statusClass(status as AuditEventStatus);
  return (
    <span className={`inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${classes}`}>
      {statusLabel(status, t)}
    </span>
  );
}

function statusClass(status: AuditEventStatus | string): string {
  if (status === "succeeded") {
    return "border-emerald-200/60 bg-emerald-50/40 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200";
  }
  if (status === "failed") {
    return "border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion";
  }
  if (status === "running") {
    return "border-blue-200/60 bg-blue-50/40 text-blue-800 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200";
  }
  return "border-atelier-smoke/30 bg-atelier-cream text-atelier-smoke dark:border-atelier-cream/15 dark:bg-atelier-cream/5 dark:text-atelier-cream/50";
}

function statusLabel(status: string, t: TranslateFunction): string {
  const labels: Record<string, TranslationKey> = {
    running: "records.status.running",
    succeeded: "records.status.succeeded",
    failed: "records.status.failed",
    cancelled: "records.status.cancelled",
  };
  const key = labels[status];
  return key ? t(key) : status;
}

function formatQuota(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "0";
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
      {[0, 1, 2, 3, 4].map((item) => (
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
