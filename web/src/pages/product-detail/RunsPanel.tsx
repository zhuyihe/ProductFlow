import { useState } from "react";
import { FileText, Loader2, RotateCcw, Layers3 } from "lucide-react";

import { PromptPreviewDialog, type PromptPreview } from "../../components/PromptPreviewDialog";
import { SelectField } from "../../components/SelectField";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/preferences";
import type { ProductWorkflow, WorkflowNode, WorkflowRun, WorkflowRunStatus } from "../../lib/types";
import { workflowNodeDisplayLabel, workflowNodeDisplayTitle } from "./nodeDisplay";
import {
  outputText,
  statusClass,
  workflowNodeRunDurationText,
  workflowNodeRunProviderSummary,
  workflowNodeRunStatusLabel,
  workflowRunQueueText,
} from "./utils";

const RUN_STATUS_CLASS_NAMES: Record<WorkflowRunStatus, string> = {
  running: "border-atelier-vermilion/30 bg-atelier-vermilion/5 text-atelier-vermilion dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion/15 dark:text-atelier-vermilion",
  succeeded:
    "border-atelier-smoke/40 bg-atelier-cream text-atelier-sepia dark:border-atelier-cream/15 dark:bg-atelier-cream/12 dark:text-atelier-cream/70",
  failed: "border-atelier-vermilion-dark/30 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/12 dark:text-atelier-vermilion",
  cancelled: "border-atelier-smoke/30 bg-atelier-paper text-atelier-sepia dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke",
};

const RUN_STATUS_DOT_CLASS_NAMES: Record<WorkflowRunStatus, string> = {
  running: "bg-atelier-vermilion shadow-paper-md",
  succeeded: "bg-atelier-smoke shadow-paper-md",
  failed: "bg-atelier-vermilion-dark shadow-paper-md",
  cancelled: "bg-atelier-smoke shadow-paper-md",
};

interface RunsPanelProps {
  workflow: ProductWorkflow | null;
  latestRun: ProductWorkflow["runs"][number] | null;
  busyRunId: string | null;
  onRetryRun: (run: WorkflowRun) => void;
  imageModel: string;
  imageModelOptions: readonly string[];
  onImageModelChange: (model: string) => void;
  textModel: string;
  textModelOptions: readonly string[];
  onTextModelChange: (model: string) => void;
}

function imagePromptItems(
  workflow: ProductWorkflow,
  run: WorkflowRun,
): Array<{ nodeId: string; title: string; instruction: string }> {
  return run.node_runs.flatMap((nodeRun) => {
    const node = workflow.nodes.find((item) => item.id === nodeRun.node_id);
    if (node?.node_type !== "image_generation" || !nodeRun.output_json) {
      return [];
    }
    const instruction = outputText(nodeRun.output_json, "instruction");
    if (!instruction) {
      return [];
    }
    return [
      {
        nodeId: node.id,
        title: node.title,
        instruction,
      },
    ];
  });
}

function findWorkflowNode(workflow: ProductWorkflow, nodeId: string): WorkflowNode | null {
  return workflow.nodes.find((node) => node.id === nodeId) ?? null;
}

export function RunsPanel({
  workflow,
  latestRun,
  busyRunId,
  onRetryRun,
  imageModel,
  imageModelOptions,
  onImageModelChange,
  textModel,
  textModelOptions,
  onTextModelChange,
}: RunsPanelProps) {
  const { t } = useI18n();
  const [promptPreview, setPromptPreview] = useState<PromptPreview | null>(null);
  const showRunSettings = imageModelOptions.length > 0 || textModelOptions.length > 0;

  if (!workflow) {
    return (
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-4 w-24 animate-shimmer" />
          <div className="h-5 w-28 rounded-full animate-shimmer" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="config-bubble space-y-3 rounded-xl p-3"
            >
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full animate-shimmer" />
                <div className="h-4 w-28 animate-shimmer" />
                <div className="ml-auto h-4 w-12 rounded animate-shimmer" />
              </div>
              <div className="space-y-1.5 pl-4.5">
                <div className="h-3 w-3/4 animate-shimmer" />
                <div className="h-3 w-1/2 animate-shimmer" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section>
      {showRunSettings ? (
        <div className="config-bubble mb-3 rounded-xl p-3 text-xs shadow-sm">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-atelier-smoke dark:text-atelier-smoke">
            {t("detail.runSettingsTitle")}
          </div>
          <div className="mb-3 text-[11px] leading-5 text-atelier-smoke dark:text-atelier-smoke">
            {t("detail.runSettingsHint")}
          </div>
          <div className="space-y-3">
            {textModelOptions.length > 0 ? (
              <label className="block">
                <span className="mb-1.5 block text-[11px] font-semibold text-atelier-sepia dark:text-atelier-cream">
                  {t("detail.runSettingsTextModel")}
                </span>
                <SelectField
                  value={textModel}
                  options={textModelOptions.map((model) => ({ value: model, label: model }))}
                  disabled={textModelOptions.length <= 1}
                  onChange={onTextModelChange}
                  radius="lg"
                  visualSize="sm"
                />
              </label>
            ) : null}
            {imageModelOptions.length > 0 ? (
              <label className="block">
                <span className="mb-1.5 block text-[11px] font-semibold text-atelier-sepia dark:text-atelier-cream">
                  {t("detail.runSettingsImageModel")}
                </span>
                <SelectField
                  value={imageModel}
                  options={imageModelOptions.map((model) => ({ value: model, label: model }))}
                  disabled={imageModelOptions.length <= 1}
                  onChange={onImageModelChange}
                  radius="lg"
                  visualSize="sm"
                />
              </label>
            ) : null}
          </div>
        </div>
      ) : null}
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs text-atelier-smoke dark:text-atelier-smoke">
          {workflow?.runs.length ? t("detail.runsCount", { count: workflow.runs.length }) : t("detail.noRunHistory")}
        </div>
        {latestRun ? (
          <div className="rounded-full border border-atelier-smoke/30 bg-atelier-paper px-2.5 py-1 text-[11px] text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke">
            {t("detail.latest", { time: formatDateTime(latestRun.started_at) })}
          </div>
        ) : null}
      </div>
      {workflow?.runs.length ? (
        <div className="space-y-2">
          {workflow.runs.map((run) => {
            const promptItems = imagePromptItems(workflow, run);
            const queueText = workflowRunQueueText(run, t);
            const runBusy = busyRunId === run.id;
            const runModels = [
              run.new_api_text_model
                ? `${t("detail.runSettingsTextModel")} · ${run.new_api_text_model}`
                : null,
              run.new_api_image_model
                ? `${t("detail.runSettingsImageModel")} · ${run.new_api_image_model}`
                : null,
            ].filter(Boolean) as string[];
            return (
              <div
                key={run.id}
                className="config-bubble rounded-xl p-3 text-xs shadow-sm"
              >
                <div className="space-y-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full shadow-md ${RUN_STATUS_DOT_CLASS_NAMES[run.status]}`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${RUN_STATUS_CLASS_NAMES[run.status]}`}
                        >
                          {t(`detail.runStatus.${run.status}`)}
                        </span>
                        <span className="inline-flex items-center text-[11px] text-atelier-smoke dark:text-atelier-smoke">
                          <Layers3 size={12} className="mr-1 text-atelier-smoke dark:text-atelier-smoke" />
                          {t("detail.nodeRunCount", { count: run.node_runs.length })}
                        </span>
                        {run.is_cancelable ? (
                          <span className="rounded-full border border-atelier-smoke/40 bg-atelier-kraft px-2 py-0.5 text-[10px] font-medium text-atelier-sepia dark:border-atelier-cream/15 dark:bg-atelier-kraft/12 dark:text-atelier-cream/70">
                            {t("detail.runCancelable")}
                          </span>
                        ) : null}
                        <span className="text-[11px] text-atelier-smoke dark:text-atelier-smoke">
                          {formatDateTime(run.started_at)}
                        </span>
                        {run.finished_at ? (
                          <span className="text-[11px] text-atelier-smoke dark:text-atelier-smoke">
                            {t("detail.finished", { time: formatDateTime(run.finished_at) })}
                          </span>
                        ) : null}
                      </div>
                      {queueText ? <div className="mt-2 text-[11px] leading-5 text-atelier-smoke dark:text-atelier-smoke">{queueText}</div> : null}
                      {runModels.length ? (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {runModels.map((model) => (
                            <span
                              key={model}
                              className="rounded-full border border-atelier-smoke/30 bg-atelier-paper px-2 py-0.5 text-[10px] font-medium text-atelier-sepia dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-cream/70"
                            >
                              {model}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    {run.is_retryable ? (
                      <button
                        type="button"
                        onClick={() => onRetryRun(run)}
                        disabled={runBusy}
                        className="inline-flex shrink-0 items-center rounded-lg border border-atelier-smoke/30 bg-atelier-paper px-2 py-1 text-[11px] font-medium text-atelier-sepia transition-colors hover:border-atelier-vermilion-dark/30 hover:bg-atelier-vermilion-dark/5 hover:text-atelier-vermilion-dark disabled:opacity-60 dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke dark:hover:border-atelier-vermilion/40 dark:hover:bg-atelier-vermilion-dark/15 dark:hover:text-atelier-vermilion"
                      >
                        {runBusy ? (
                          <Loader2 size={12} className="mr-1 animate-spin" />
                        ) : (
                          <RotateCcw size={12} className="mr-1" />
                        )}
                        {t("detail.retry")}
                      </button>
                    ) : null}
                  </div>
                  <div className="rounded-xl border border-atelier-smoke/20 bg-atelier-paper/70 p-2 dark:border-atelier-cream/15 dark:bg-[#1F1812]/70">
                    <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-atelier-smoke dark:text-atelier-smoke">
                      {t("detail.nodeRunDetails")}
                    </div>
                    <div className="divide-y divide-atelier-smoke/20 overflow-hidden rounded-lg border border-atelier-smoke/30 bg-atelier-paper dark:divide-atelier-cream/15 dark:border-atelier-cream/15 dark:bg-[#1F1812]">
                      {run.node_runs.map((nodeRun) => {
                        const node = findWorkflowNode(workflow, nodeRun.node_id);
                        const promptItem = promptItems.find((item) => item.nodeId === nodeRun.node_id);
                        const durationText = workflowNodeRunDurationText(nodeRun, t);
                        const providerSummary = workflowNodeRunProviderSummary(nodeRun, t);
                        return (
                          <div key={nodeRun.id} className="px-2.5 py-2">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-1.5">
                                  <span className="max-w-[170px] truncate text-[11px] font-semibold text-atelier-ink dark:text-atelier-cream">
                                    {node ? workflowNodeDisplayTitle(node, t) : t("detail.nodeRunUnknown")}
                                  </span>
                                  {node ? (
                                    <span className="text-[10px] text-atelier-smoke dark:text-atelier-smoke">
                                      {workflowNodeDisplayLabel(node, t)}
                                    </span>
                                  ) : null}
                                  {durationText ? (
                                    <span className="text-[10px] text-atelier-smoke dark:text-atelier-smoke">{durationText}</span>
                                  ) : null}
                                </div>
                                {providerSummary ? (
                                  <div className="mt-1 line-clamp-2 text-[10px] leading-4 text-atelier-smoke dark:text-atelier-smoke">
                                    {providerSummary}
                                  </div>
                                ) : null}
                              </div>
                              <span
                                className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${statusClass(nodeRun.status)}`}
                              >
                                {workflowNodeRunStatusLabel(nodeRun.status, t)}
                              </span>
                            </div>
                            {nodeRun.failure_reason ? (
                              <div
                                className={`mt-2 line-clamp-2 rounded-lg border px-2 py-1 text-[11px] leading-5 ${
                                  nodeRun.status === "cancelled"
                                    ? "border-atelier-smoke/20 bg-atelier-paper text-atelier-sepia dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke"
                                    : "border-atelier-vermilion-dark/20 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion"
                                }`}
                              >
                                {nodeRun.failure_reason}
                              </div>
                            ) : null}
                            {promptItem ? (
                              <button
                                type="button"
                                onClick={() =>
                                  setPromptPreview({
                                    title: `${promptItem.title} Prompt`,
                                    text: promptItem.instruction,
                                    meta: formatDateTime(run.started_at),
                                  })
                                }
                                className="mt-2 inline-flex max-w-full items-center rounded-lg border border-atelier-smoke/30 bg-atelier-paper px-2 py-1 text-[11px] font-medium text-atelier-sepia transition-colors hover:border-atelier-vermilion/30 hover:bg-atelier-vermilion/5 hover:text-atelier-vermilion dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke dark:hover:border-atelier-vermilion/40 dark:hover:bg-atelier-vermilion/10 dark:hover:text-atelier-cream"
                              >
                                <FileText size={12} className="mr-1 shrink-0" />
                                <span className="truncate">{t("detail.nodeRunPrompt")}</span>
                              </button>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  {run.failure_reason ? (
                    <div
                      className={`line-clamp-2 rounded-lg border px-2.5 py-1.5 ${
                        run.status === "cancelled"
                          ? "border-atelier-smoke/20 bg-atelier-paper text-atelier-sepia dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke"
                          : "border-atelier-vermilion-dark/20 bg-atelier-vermilion-dark/5 text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-atelier-vermilion-dark/15 dark:text-atelier-vermilion"
                      }`}
                    >
                      {run.failure_reason}
                    </div>
                  ) : null}
                  {run.status === "failed" && !run.is_retryable ? (
                    <div className="inline-flex rounded-lg border border-atelier-vermilion-dark/20 bg-atelier-paper px-2.5 py-1 text-[11px] font-medium text-atelier-vermilion-dark dark:border-atelier-vermilion/40 dark:bg-[#1F1812] dark:text-atelier-vermilion">
                      {t("detail.notRetryable")}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex min-h-[160px] items-center justify-center rounded-xl border border-dashed border-atelier-smoke/30 bg-atelier-paper/60 px-4 py-6 text-center text-xs text-atelier-smoke dark:border-atelier-cream/15 dark:bg-[#1F1812] dark:text-atelier-smoke">
          {t("detail.noRuns")}
        </div>
      )}
      {promptPreview ? (
        <PromptPreviewDialog preview={promptPreview} onClose={() => setPromptPreview(null)} />
      ) : null}
    </section>
  );
}
